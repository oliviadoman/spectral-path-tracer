"""
Volumetric renderer application.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Tuple
import platform
from PIL import Image
import numpy as np
from imgui_bundle import imgui_tex_inspect, portable_file_dialogs as pfd
from reactivex.subject import BehaviorSubject, Subject
from slangpy_imgui_bundle.app import App
import slangpy as spy
from slangpy_nn.utils import slang_include_paths
from slangpy_imgui_bundle.utils.file_dialog import (
    async_open_file_dialog,
    async_save_file_dialog,
)
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from cs248a_renderer import SHADER_PATH
from cs248a_renderer.gui.dockspace import VolumetricDockspace
from cs248a_renderer.gui.preview import PreviewWindow
from cs248a_renderer.gui.renderer import RendererWindow, RendererConfigWindow
from cs248a_renderer.gui.scene_editor import SceneEditorWindow
from cs248a_renderer.gui.scene_wizard import SceneWizard
from cs248a_renderer.model.scene_object import SceneObject
from cs248a_renderer.model.mesh import Triangle
from cs248a_renderer.model.bvh import BVH
from cs248a_renderer.view_model.scene_manager import SceneManager

# from cs248a_renderer.renderer.volume_renderer import VolumeRenderer
# from cs248a_renderer.renderer.nerf_renderer import NeRFRenderer
from cs248a_renderer.renderer.core_renderer import Renderer


logger = logging.getLogger(__name__)


FONT_PATH = Path(__file__).parent / "fonts" / "JetBrainsMonoNerdFontMono-Regular.ttf"
_system = platform.system()
if _system == "Darwin":
    DEVICE_TYPE = spy.DeviceType.metal
elif _system in ("Windows", "Linux"):
    DEVICE_TYPE = spy.DeviceType.vulkan
else:
    # Default to vulkan for unknown/other platforms
    DEVICE_TYPE = spy.DeviceType.vulkan


@dataclass
class BVHBuildProgress:
    current: int
    total: int


@dataclass
class BVHBuildResult:
    triangles: list[Triangle]
    bvh: BVH


def bvh_worker(conn: Connection) -> None:
    """
    Worker process for BVH construction.
    """
    triangles, max_nodes, min_prim_per_node = conn.recv()

    def on_progress(current: int, total: int) -> None:
        conn.send(BVHBuildProgress(current=current, total=total))

    bvh = BVH(
        primitives=triangles,
        max_nodes=max_nodes,
        min_prim_per_node=min_prim_per_node,
        on_progress=on_progress,
    )
    conn.send(BVHBuildResult(triangles=triangles, bvh=bvh))


class InteractiveRendererApp(App):
    window_title = "CS 248A Interactive Renderer"
    fb_scale = 1.0
    font_size = 16
    device_type = DEVICE_TYPE

    scene_manager: SceneManager = SceneManager()
    core_renderer: Renderer
    target_spp: int = 0
    # volume_renderer: VolumeRenderer
    # nerf_renderer: NeRFRenderer
    render_texture: BehaviorSubject[Tuple[spy.Texture, int]]
    canvas_size: BehaviorSubject[Tuple[int, int]] = BehaviorSubject((800, 600))
    render_request: Subject[None] = Subject()
    abort_render: Subject[None] = Subject()
    render_progress: BehaviorSubject[Tuple[int, int]] = BehaviorSubject((0, 0))
    editing_object: BehaviorSubject[SceneObject | None] = BehaviorSubject(None)

    # Renderer config parameters
    render_depth: BehaviorSubject[bool] = BehaviorSubject(False)
    render_normal: BehaviorSubject[bool] = BehaviorSubject(False)
    visualize_barycentric_coords: BehaviorSubject[bool] = BehaviorSubject(False)
    visualize_tex_uv: BehaviorSubject[bool] = BehaviorSubject(False)
    visualize_level_of_detail: BehaviorSubject[bool] = BehaviorSubject(False)
    visualize_albedo: BehaviorSubject[bool] = BehaviorSubject(False)
    smooth_shading: BehaviorSubject[bool] = BehaviorSubject(False)
    num_rectangular_light_samples: BehaviorSubject[int] = BehaviorSubject(1)
    path_trace_depth: BehaviorSubject[int] = BehaviorSubject(1)
    spp: BehaviorSubject[int] = BehaviorSubject(16)
    max_bvh_nodes: BehaviorSubject[int] = BehaviorSubject(1024)
    min_prim_per_node: BehaviorSubject[int] = BehaviorSubject(32)
    always_build_bvh: BehaviorSubject[bool] = BehaviorSubject(True)

    _scene_wizard_open: Subject[None] = Subject()
    _preview_open: BehaviorSubject[bool] = BehaviorSubject(True)
    _renderer_open: BehaviorSubject[bool] = BehaviorSubject(True)
    _renderer_config_open: BehaviorSubject[bool] = BehaviorSubject(False)
    _scene_editor_open: BehaviorSubject[bool] = BehaviorSubject(True)

    _on_load_mesh: Subject[None] = Subject()
    _on_load_volume: Subject[None] = Subject()
    _on_save_scene: Subject[None] = Subject()
    _on_load_scene: Subject[None] = Subject()
    _on_save_render_result: Subject[None] = Subject()

    _mesh_outdated: BehaviorSubject[bool] = BehaviorSubject(True)
    _build_bvh_request: Subject[None] = Subject()
    _bvh_process: Process | None = None
    _bvh_conn: Connection | None = None
    _bvh_progress: BehaviorSubject[Tuple[int, int]] = BehaviorSubject((0, 0))

    def __init__(self) -> None:
        shader_paths = [SHADER_PATH]
        shader_paths.extend(slang_include_paths())
        super().__init__(user_shader_paths=shader_paths)

        imgui_tex_inspect.init()
        imgui_tex_inspect.create_context()

        self._reload_font(self.font_size)

        self._on_load_mesh.subscribe(lambda _: asyncio.create_task(self._load_mesh()))
        self._on_load_volume.subscribe(
            lambda _: asyncio.create_task(self._load_volume())
        )
        self._on_save_scene.subscribe(lambda _: asyncio.create_task(self._save_scene()))
        self._on_load_scene.subscribe(lambda _: asyncio.create_task(self._load_scene()))
        self._on_save_render_result.subscribe(
            lambda _: asyncio.create_task(self._save_render_result())
        )
        self._build_bvh_request.subscribe(
            lambda _: asyncio.create_task(
                self.build_bvh(self.max_bvh_nodes.value, self.min_prim_per_node.value)
            )
        )
        self.always_build_bvh.subscribe(
            lambda always_build: self._mesh_outdated.on_next(True)
        )

        # --------------------- Volume Renderer  --------------------- #

        texture = self._create_render_texture(
            self.canvas_size.value[0], self.canvas_size.value[1]
        )
        texture_id = self.adapter.register_texture(texture)
        self.render_texture = BehaviorSubject((texture, texture_id))
        self.core_renderer = Renderer(
            device=self.device, render_texture_sbj=self.render_texture
        )

        self.canvas_size.subscribe(self._on_canvas_resize)
        self.render_request.subscribe(self._on_render_request)
        self.abort_render.subscribe(self._on_abort_render)

        # --------------------------- GUI  --------------------------- #

        self._dockspace = VolumetricDockspace(
            device=self.device,
            adapter=self.adapter,
            window_size=self._curr_window_size,
            window_open_subjects={
                "preview_open": self._preview_open,
                "scene_wizard_open": self._scene_wizard_open,
                "renderer_open": self._renderer_open,
                "renderer_config_open": self._renderer_config_open,
                "scene_editor_open": self._scene_editor_open,
            },
            file_subjects={
                "on_load_mesh": self._on_load_mesh,
                "on_load_volume": self._on_load_volume,
                "on_save_scene": self._on_save_scene,
                "on_load_scene": self._on_load_scene,
                "on_save_render_result": self._on_save_render_result,
            },
            renderer_state={
                "render_request": self.render_request,
                "abort_render": self.abort_render,
                "always_build_bvh": self.always_build_bvh,
                "mesh_outdated": self._mesh_outdated,
                "build_bvh": self._build_bvh_request,
                "bvh_progress": self._bvh_progress,
            },
        )

        self._render_targets = [
            SceneWizard(
                device=self.device,
                adapter=self.adapter,
                open=self._scene_wizard_open,
                scene_manager=self.scene_manager,
            ),
            PreviewWindow(
                device=self.device,
                adapter=self.adapter,
                open=self._preview_open,
                on_close=lambda: self._preview_open.on_next(False),
                scene_manager=self.scene_manager,
                canvas_size=self.canvas_size,
                editing_object=self.editing_object,
                mesh_outdated=self._mesh_outdated,
            ),
            RendererConfigWindow(
                device=self.device,
                adapter=self.adapter,
                open=self._renderer_config_open,
                on_close=lambda: self._renderer_config_open.on_next(False),
                canvas_size=self.canvas_size,
                render_depth=self.render_depth,
                render_normal=self.render_normal,
                visualize_barycentric_coords=self.visualize_barycentric_coords,
                visualize_tex_uv=self.visualize_tex_uv,
                visualize_level_of_detail=self.visualize_level_of_detail,
                visualize_albedo=self.visualize_albedo,
                smooth_shading=self.smooth_shading,
                num_rectangular_light_samples=self.num_rectangular_light_samples,
                path_trace_depth=self.path_trace_depth,
                spp=self.spp,
                max_bvh_nodes=self.max_bvh_nodes,
                min_prim_per_node=self.min_prim_per_node,
            ),
            RendererWindow(
                device=self.device,
                adapter=self.adapter,
                open=self._renderer_open,
                on_close=lambda: self._renderer_open.on_next(False),
                render_texture=self.render_texture,
                render_request=self.render_request,
                abort_render=self.abort_render,
                render_progress=self.render_progress,
            ),
            SceneEditorWindow(
                device=self.device,
                adapter=self.adapter,
                open=self._scene_editor_open,
                on_close=lambda: self._scene_editor_open.on_next(False),
                scene_manager=self.scene_manager,
                editing_object=self.editing_object,
                mesh_outdated=self._mesh_outdated,
            ),
        ]

    def update(self):
        if self.core_renderer.num_samples < self.target_spp:
            self.core_renderer.render_step(
                view_mat=self.scene_manager.scene.camera.view_matrix(),
                fov=self.scene_manager.scene.camera.fov,
                render_depth=self.render_depth.value,
                render_normal=self.render_normal.value,
                visualize_barycentric_coords=self.visualize_barycentric_coords.value,
                visualize_tex_uv=self.visualize_tex_uv.value,
                visualize_level_of_detail=self.visualize_level_of_detail.value,
                visualize_albedo=self.visualize_albedo.value,
                smooth_shading=self.smooth_shading.value,
                num_rectangular_light_samples=self.num_rectangular_light_samples.value,
                path_trace_depth=self.path_trace_depth.value,
            )
            self.render_progress.on_next(
                (self.core_renderer.num_samples, self.target_spp)
            )
        elif self.core_renderer.num_samples == self.target_spp and self.target_spp > 0:
            logger.info(
                f"Render completed with {self.core_renderer.num_samples} samples."
            )
            self.target_spp = 0
            self.render_progress.on_next((0, 0))

    def _on_canvas_resize(self, size: tuple[int, int]) -> None:
        width, height = size
        curr_id = self.render_texture.value[1]
        self.adapter.unregister_texture(curr_id)
        texture = self._create_render_texture(width, height)
        texture_id = self.adapter.register_texture(texture)
        self.render_texture.on_next((texture, texture_id))

    def _on_render_request(self, _) -> None:
        mesh_was_outdated = self._mesh_outdated.value

        if mesh_was_outdated:
            self.core_renderer.load_triangles(self.scene_manager.scene)
            self._mesh_outdated.on_next(False)
            if self.always_build_bvh.value and self._bvh_process is None:
                asyncio.create_task(
                    self.build_bvh_and_render(
                        self.max_bvh_nodes.value, self.min_prim_per_node.value
                    )
                )
        if self.scene_manager.scene.single_volume is not None:
            self.core_renderer.load_volume(self.scene_manager.scene.single_volume)
        self.core_renderer.load_lights(self.scene_manager.scene)
        self.core_renderer.clear_render_target()

        if not self.always_build_bvh.value or not mesh_was_outdated:
            self.target_spp = self.spp.value
            self.render_progress.on_next((0, self.target_spp))

    def _on_abort_render(self, _) -> None:
        if self.target_spp > 0:
            logger.info(
                f"Rendering aborted at {self.core_renderer.num_samples}/{self.target_spp} samples."
            )
            self.target_spp = 0
            self.render_progress.on_next((0, 0))

    def _reload_font(self, size: int) -> None:
        self.io.fonts.clear()
        self.io.fonts.add_font_from_file_ttf(
            str(FONT_PATH),
            size * self.fb_scale,
        )
        self.adapter.refresh_font_texture()
        self.io.font_global_scale = 1.0 / self.fb_scale

    def _create_render_texture(self, width: int, height: int) -> spy.Texture:
        return self.device.create_texture(
            type=spy.TextureType.texture_2d,
            width=width,
            height=height,
            format=spy.Format.rgba32_float,
            usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
        )

    async def _load_mesh(self) -> None:
        mesh_path = await self._choose_file(filters=["Obj Files", "*.obj"])
        if mesh_path is not None:
            self.scene_manager.load_mesh(mesh_path=mesh_path)
            self._mesh_outdated.on_next(True)

    async def _load_volume(self) -> None:
        volume_path = await self._choose_file(filters=["Numpy Files", "*.npy"])
        if volume_path is not None:
            self.scene_manager.load_volume(volume_path=volume_path)

    async def _save_scene(self) -> None:
        """Save the current scene to a ZIP file."""
        try:
            save_path = await self._choose_save_file(
                filters=["Scene ZIP Files", "*.zip"], default_filename="scene.zip"
            )
            if save_path is not None:
                self.scene_manager.serialize_scene(zip_path=save_path)
                logger.info(f"Scene saved to {save_path}")
        except Exception as e:
            logger.error(f"Error saving scene: {e}")

    async def _load_scene(self) -> None:
        """Load a scene from a ZIP file."""
        try:
            scene_path = await self._choose_file(filters=["Scene ZIP Files", "*.zip"])
            if scene_path is not None:
                self.scene_manager.deserialize_scene(zip_path=scene_path)
                self._mesh_outdated.on_next(True)
                logger.info(f"Scene loaded from {scene_path}")
        except Exception as e:
            logger.error(f"Error loading scene: {e}")

    async def _save_render_result(self) -> None:
        """Save the current render target to a PNG image."""
        try:
            save_path = await self._choose_save_file(
                filters=["PNG Files", "*.png"], default_filename="render.png"
            )
            if save_path is None:
                return

            texture = self.render_texture.value[0]
            width, height = texture.width, texture.height
            img_np = np.flipud(texture.to_numpy().reshape((height, width, 4)))
            img_np[:, :, :3] = np.pow(img_np[:, :, :3], 1 / 2.2)
            img_np = np.clip(img_np * 255, 0, 255).astype(np.uint8)
            image = Image.fromarray(img_np, mode="RGBA")
            image.save(save_path)
            logger.info("Render result saved to %s", save_path)
        except Exception as e:
            logger.error(f"Error saving render result: {e}")

    async def _choose_file(self, filters: list[str] = []) -> Path | None:
        files = await async_open_file_dialog(
            title="Open File",
            default_path=str(Path.cwd()),
            filters=filters,
            options=pfd.opt.none,
        )
        if files:
            file_path = Path(files[0])
            logger.info("Selected file: %s", file_path)
            return file_path
        return None

    async def _choose_save_file(
        self, filters: list[str] = [], default_filename: str = "file"
    ) -> Path | None:
        """Open a file save dialog."""
        file_path = await async_save_file_dialog(
            title="Save File",
            default_path=str(Path.cwd() / default_filename),
            filters=filters,
            options=pfd.opt.none,
        )
        if file_path:
            save_path = (
                Path(file_path[0]) if isinstance(file_path, list) else Path(file_path)
            )
            logger.info("Save file to: %s", save_path)
            return save_path
        return None

    async def build_bvh_and_render(self, max_nodes: int, min_prim_per_node: int):
        await self.build_bvh(max_nodes, min_prim_per_node)
        if self.target_spp == 0:
            self.target_spp = self.spp.value
            self.render_progress.on_next((0, self.target_spp))

    async def build_bvh(self, max_nodes: int, min_prim_per_node: int):
        if self._bvh_process is not None:
            logger.warning("BVH build already in progress.")
            return

        triangles, materials = (
            self.scene_manager.scene.extract_triangles_with_material()
        )
        if len(triangles) == 0:
            logger.warning("No triangles to build BVH.")
            return

        parent_conn, child_conn = Pipe()
        self._bvh_conn = parent_conn
        self._bvh_process = Process(
            target=bvh_worker,
            args=(child_conn,),
        )
        self._bvh_process.start()

        # Send data to worker
        self._bvh_conn.send((triangles, max_nodes, min_prim_per_node))

        # Monitor progress
        while True:
            if self._bvh_conn.poll():
                msg = self._bvh_conn.recv()
                if isinstance(msg, BVHBuildProgress):
                    current, total = msg.current, msg.total
                    self._bvh_progress.on_next((current, total))
                else:
                    break
            await asyncio.sleep(0.0)

        self._bvh_process.join()
        self._bvh_process = None
        self._bvh_conn = None
        self._bvh_progress.on_next((0, 0))

        # Retrieve BVH result
        result = msg
        logger.info("BVH build completed with %d nodes.", len(result.bvh.nodes))
        self.core_renderer.load_bvh(result.triangles, result.bvh)
        self.core_renderer.load_materials(materials)
        self._mesh_outdated.on_next(False)
