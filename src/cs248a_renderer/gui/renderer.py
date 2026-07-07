from typing import Tuple, Unpack
from imgui_bundle import ImVec2, imgui, imgui_ctx, imgui_tex_inspect
from reactivex import Observable
from reactivex.subject import BehaviorSubject, Subject
import slangpy as spy
from slangpy_imgui_bundle.render_targets.window import Window, WindowArgs


class RendererWindowArgs(WindowArgs):
    render_texture: Observable[Tuple[spy.Texture, int]]
    render_request: Subject[None]
    abort_render: Subject[None]
    render_progress: Observable[Tuple[int, int]]


class RendererWindow(Window):
    _render_texture: spy.Texture
    _render_texture_id: int

    _render_request: Subject[None]
    _abort_render: Subject[None]
    _render_progress: Tuple[int, int] = (0, 0)
    _real_time_rendering: bool = False

    def __init__(self, **kwargs: Unpack[RendererWindowArgs]) -> None:
        super().__init__(**kwargs)

        def update_texture(texture: Tuple[spy.Texture, int]):
            self._render_texture, self._render_texture_id = texture

        def update_progress(progress: Tuple[int, int]):
            self._render_progress = progress

        kwargs["render_texture"].subscribe(update_texture)
        kwargs["render_progress"].subscribe(update_progress)

        self._render_request = kwargs["render_request"]
        self._abort_render = kwargs["abort_render"]

    def render_window(self, time: float, delta_time: float, open: bool | None) -> bool:
        window_flags = imgui.WindowFlags_.menu_bar.value
        with imgui_ctx.begin("Renderer", p_open=open, flags=window_flags) as window:
            # Menu bar.
            if imgui.begin_menu_bar():
                if imgui.menu_item_simple("Render"):
                    self._render_request.on_next(None)
                rendering = self._render_progress[1] > 0
                if imgui.menu_item_simple("Abort", enabled=rendering):
                    self._abort_render.on_next(None)
                imgui.end_menu_bar()

            # Progress bar
            rendering = self._render_progress[1] > 0
            if rendering:
                current, total = self._render_progress
                imgui.progress_bar(
                    fraction=float(current) / float(total) if total > 0 else 0.0,
                    size_arg=(-1, 0),
                    overlay=f"Rendering: {current}/{total} samples",
                )
                if imgui.button("Abort Rendering", size=(-1, 0)):
                    self._abort_render.on_next(None)

            # Get the available content space.
            content_region_avail = imgui.get_content_region_avail()
            imgui_tex_inspect.begin_inspector_panel(
                "Render Result Inspector",
                self._render_texture_id,
                ImVec2(self._render_texture.width, self._render_texture.height),
                flags=imgui_tex_inspect.InspectorFlags_.flip_y.value,
                size=imgui_tex_inspect.SizeIncludingBorder(content_region_avail),
            )
            imgui_tex_inspect.end_inspector_panel()

            return window.opened


class RendererConfigWindowArgs(WindowArgs):
    canvas_size: BehaviorSubject[Tuple[int, int]]
    render_depth: BehaviorSubject[bool]
    render_normal: BehaviorSubject[bool]
    visualize_barycentric_coords: BehaviorSubject[bool]
    visualize_tex_uv: BehaviorSubject[bool]
    visualize_level_of_detail: BehaviorSubject[bool]
    visualize_albedo: BehaviorSubject[bool]
    smooth_shading: BehaviorSubject[bool]
    num_rectangular_light_samples: BehaviorSubject[int]
    path_trace_depth: BehaviorSubject[int]
    spp: BehaviorSubject[int]
    max_bvh_nodes: BehaviorSubject[int]
    min_prim_per_node: BehaviorSubject[int]


class RendererConfigWindow(Window):
    _canvas_size: BehaviorSubject[Tuple[int, int]]
    _render_depth: BehaviorSubject[bool]
    _render_normal: BehaviorSubject[bool]
    _visualize_barycentric_coords: BehaviorSubject[bool]
    _visualize_tex_uv: BehaviorSubject[bool]
    _visualize_level_of_detail: BehaviorSubject[bool]
    _visualize_albedo: BehaviorSubject[bool]
    _smooth_shading: BehaviorSubject[bool]
    _num_rectangular_light_samples: BehaviorSubject[int]
    _path_trace_depth: BehaviorSubject[int]
    _spp: BehaviorSubject[int]
    _max_bvh_nodes: BehaviorSubject[int]
    _min_prim_per_node: BehaviorSubject[int]

    def __init__(self, **kwargs: Unpack[RendererConfigWindowArgs]) -> None:
        super().__init__(**kwargs)
        self._canvas_size = kwargs["canvas_size"]
        self._render_depth = kwargs["render_depth"]
        self._render_normal = kwargs["render_normal"]
        self._visualize_barycentric_coords = kwargs["visualize_barycentric_coords"]
        self._visualize_tex_uv = kwargs["visualize_tex_uv"]
        self._visualize_level_of_detail = kwargs["visualize_level_of_detail"]
        self._visualize_albedo = kwargs["visualize_albedo"]
        self._smooth_shading = kwargs["smooth_shading"]
        self._num_rectangular_light_samples = kwargs["num_rectangular_light_samples"]
        self._path_trace_depth = kwargs["path_trace_depth"]
        self._spp = kwargs["spp"]
        self._max_bvh_nodes = kwargs["max_bvh_nodes"]
        self._min_prim_per_node = kwargs["min_prim_per_node"]

    def render_window(self, time: float, delta_time: float, open: bool | None) -> bool:
        with imgui_ctx.begin("Renderer Config", p_open=open) as window:
            imgui.separator_text("Canvas Settings")

            width, height = self._canvas_size.value
            changed_width, new_width = imgui.input_int("Width##canvas", width)
            changed_height, new_height = imgui.input_int("Height##canvas", height)

            if changed_width or changed_height:
                new_width = max(1, new_width)
                new_height = max(1, new_height)
                self._canvas_size.on_next((new_width, new_height))

            imgui.text(f"Current canvas size: {width}x{height}")

            imgui.separator_text("Render Settings")

            changed, value = imgui.checkbox("Render Depth", self._render_depth.value)
            if changed:
                self._render_depth.on_next(value)

            changed, value = imgui.checkbox("Render Normal", self._render_normal.value)
            if changed:
                self._render_normal.on_next(value)

            changed, value = imgui.checkbox(
                "Visualize Barycentric Coords", self._visualize_barycentric_coords.value
            )
            if changed:
                self._visualize_barycentric_coords.on_next(value)

            changed, value = imgui.checkbox(
                "Visualize Texture UV", self._visualize_tex_uv.value
            )
            if changed:
                self._visualize_tex_uv.on_next(value)

            changed, value = imgui.checkbox(
                "Visualize Level of Detail", self._visualize_level_of_detail.value
            )
            if changed:
                self._visualize_level_of_detail.on_next(value)

            changed, value = imgui.checkbox(
                "Visualize Albedo", self._visualize_albedo.value
            )
            if changed:
                self._visualize_albedo.on_next(value)

            changed, value = imgui.checkbox(
                "Smooth Shading", self._smooth_shading.value
            )
            if changed:
                self._smooth_shading.on_next(value)

            changed, value = imgui.input_int(
                "Rectangular Light Samples##lights",
                self._num_rectangular_light_samples.value,
            )
            if changed:
                value = max(1, value)
                self._num_rectangular_light_samples.on_next(value)

            changed, value = imgui.input_int(
                "Path Trace Depth##ptdepth",
                self._path_trace_depth.value,
            )
            if changed:
                value = max(1, value)
                self._path_trace_depth.on_next(value)

            changed, value = imgui.input_int(
                "Samples Per Pixel (SPP)##spp",
                self._spp.value,
            )
            if changed:
                value = max(1, value)
                self._spp.on_next(value)

            imgui.separator_text("BVH Settings")

            changed, value = imgui.input_int(
                "Max BVH Nodes##maxbvhnodes",
                self._max_bvh_nodes.value,
            )
            if changed:
                value = max(1, value)
                self._max_bvh_nodes.on_next(value)

            changed, value = imgui.input_int(
                "Min Primitives Per Node##minprimpernode",
                self._min_prim_per_node.value,
            )
            if changed:
                value = max(1, value)
                self._min_prim_per_node.on_next(value)

            return window.opened
