from pyglm import glm
import slangpy as spy
import pytest
import numpy as np
from slangpy_nn.utils import slang_include_paths

from cs248a_renderer import SHADER_PATH
from cs248a_renderer.model.cameras import PerspectiveCamera
from cs248a_renderer.model.ray_marcher_config import RayMarcherConfig
from cs248a_renderer.model.scene import SingleVolumeScene
from cs248a_renderer.model.transforms import Transform3D
from cs248a_renderer.model.volumes import DenseVolume
from cs248a_renderer.renderer.volume_renderer import VolumeRenderer


shader_paths = [SHADER_PATH]
shader_paths.extend(slang_include_paths())
device = spy.create_device(include_paths=shader_paths)


BASE_RENDER_SIZE = 512
BASE_VOLUME_SIZE = 128
BASE_CAMERA_DISTANCE = 2.0
BASE_STEP_SIZE = 0.01


def _random_volume_data(volume_size):
    return np.random.rand(volume_size, volume_size, volume_size, 4).astype(np.float32)


def _benchmark_forward_render(
    benchmark,
    *,
    render_size,
    volume_size,
    cam_dist,
    step_size,
):
    """Execute the renderer benchmark with the provided parameters."""
    w = h = render_size
    render_texture = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=w,
        height=h,
        usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
    )
    renderer = VolumeRenderer(
        device=device,
        render_texture=render_texture,
    )
    volume = DenseVolume(
        data=_random_volume_data(volume_size),
    )
    camera = PerspectiveCamera(transform=Transform3D(glm.vec3(0.0, 0.0, cam_dist)))
    config = RayMarcherConfig(
        max_steps=1024,
        step_size=step_size,
        density_scale=10.0,
    )
    scene = SingleVolumeScene(
        volume=volume,
        camera=camera,
        ray_marcher_config=config,
    )
    benchmark(
        renderer.render,
        scene=scene,
        view_mat=camera.view_matrix(),
        fov=camera.fov,
    )


def _prepare_forward_dispatch(render_size, volume_size, cam_dist, step_size):
    w = h = render_size
    render_texture = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=w,
        height=h,
        usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
    )
    renderer = VolumeRenderer(device=device, render_texture=render_texture)

    volume_data = _random_volume_data(volume_size)
    volume = DenseVolume(data=volume_data)
    camera = PerspectiveCamera(transform=Transform3D(glm.vec3(0.0, 0.0, cam_dist)))
    config = RayMarcherConfig(
        max_steps=1024,
        step_size=step_size,
        density_scale=10.0,
    )
    scene = SingleVolumeScene(
        volume=volume,
        camera=camera,
        ray_marcher_config=config,
    )

    data_arr = np.ascontiguousarray(volume_data)
    data_buffer = device.create_buffer(
        format=spy.Format.rgba32_float,
        usage=spy.BufferUsage.shader_resource,
        data=data_arr,
    )

    min_bound, max_bound = volume.bounding_box
    dim = volume.shape
    model_mat = volume.transform.get_matrix()
    view_mat = camera.view_matrix()
    focal_length = (0.5 * float(render_texture.height)) / np.tan(
        np.radians(camera.fov) / 2.0
    )

    uniforms = {
        "canvasSize": (render_texture.width, render_texture.height),
        "invModelMatrix": np.array(glm.inverse(model_mat)),
        "invViewMatrix": np.array(glm.inverse(view_mat)),
        "focalLength": focal_length,
        "ambientColor": scene.ambient_color,
        "rayMarcherConfig": {
            "maxSteps": scene.ray_marcher_config.max_steps,
            "stepSize": scene.ray_marcher_config.step_size,
            "densityScale": scene.ray_marcher_config.density_scale,
        },
        "volume": {
            "minBound": (min_bound.x, min_bound.y, min_bound.z),
            "maxBound": (max_bound.x, max_bound.y, max_bound.z),
            "dimensions": (dim[2], dim[1], dim[0]),
            "data": {
                "tex": data_buffer,
                "size": (dim[2], dim[1], dim[0]),
            },
            "useAlbedoVolume": True,
            "albedo": scene.volume.properties["albedo"],
        },
        "outputTexture": render_texture,
    }

    thread_count = (render_texture.width, render_texture.height, 1)
    return renderer, renderer._forward_kernel, thread_count, uniforms


def _benchmark_backward_render(
    benchmark,
    *,
    render_size,
    volume_size,
    cam_dist,
    step_size,
):
    w = h = render_size
    render_texture = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=w,
        height=h,
        usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
    )
    renderer = VolumeRenderer(device=device, render_texture=render_texture)

    volume = DenseVolume(data=_random_volume_data(volume_size))
    camera = PerspectiveCamera(transform=Transform3D(glm.vec3(0.0, 0.0, cam_dist)))
    config = RayMarcherConfig(
        max_steps=1024,
        step_size=step_size,
        density_scale=10.0,
    )
    scene = SingleVolumeScene(
        volume=volume,
        camera=camera,
        ray_marcher_config=config,
    )

    renderer.load_volume(scene)
    d_output = np.random.rand(h, w, 4).astype(np.float32)

    def run_backward():
        renderer.reset_volume_d()
        renderer.render_backward(scene=scene, d_output=d_output)

    benchmark(run_backward)


def _prepare_backward_dispatch(render_size, volume_size, cam_dist, step_size):
    w = h = render_size
    render_texture = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=w,
        height=h,
        usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
    )
    renderer = VolumeRenderer(device=device, render_texture=render_texture)

    volume_data = _random_volume_data(volume_size)
    volume = DenseVolume(data=volume_data)
    camera = PerspectiveCamera(transform=Transform3D(glm.vec3(0.0, 0.0, cam_dist)))
    config = RayMarcherConfig(
        max_steps=1024,
        step_size=step_size,
        density_scale=10.0,
    )
    scene = SingleVolumeScene(
        volume=volume,
        camera=camera,
        ray_marcher_config=config,
    )

    renderer.load_volume(scene)
    renderer.reset_volume_d()

    d_output = np.random.rand(h, w, 4).astype(np.float32)
    d_output_tex = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=w,
        height=h,
        usage=spy.TextureUsage.shader_resource,
        data=d_output,
    )

    min_bound, max_bound = volume.bounding_box
    dim = volume.shape
    model_mat = volume.transform.get_matrix()
    view_mat = camera.view_matrix()
    focal_length = (0.5 * float(render_texture.height)) / np.tan(
        np.radians(camera.fov) / 2.0
    )

    uniforms = {
        "canvasSize": (render_texture.width, render_texture.height),
        "invModelMatrix": np.array(glm.inverse(model_mat)),
        "invViewMatrix": np.array(glm.inverse(view_mat)),
        "focalLength": focal_length,
        "ambientColor": scene.ambient_color,
        "rayMarcherConfig": {
            "maxSteps": scene.ray_marcher_config.max_steps,
            "stepSize": scene.ray_marcher_config.step_size,
            "densityScale": scene.ray_marcher_config.density_scale,
        },
        "volume": {
            "minBound": (min_bound.x, min_bound.y, min_bound.z),
            "maxBound": (max_bound.x, max_bound.y, max_bound.z),
            "dimensions": (dim[2], dim[1], dim[0]),
            "data": {
                "tex": renderer._data,
                "size": (dim[2], dim[1], dim[0]),
            },
            "dData": {
                "dTex": renderer._d_data,
            },
            "useAlbedoVolume": True,
            "albedo": scene.volume.properties["albedo"],
        },
        "dOutputTexture": d_output_tex,
    }

    thread_count = (render_texture.width, render_texture.height, 1)
    return renderer, d_output_tex, renderer._backward_kernel, thread_count, uniforms


@pytest.mark.parametrize(
    "render_size",
    [
        256,
        384,
        512,
        768,
        1024,
    ],
)
def test_forward_renderer_render_size(benchmark, render_size):
    _benchmark_forward_render(
        benchmark,
        render_size=render_size,
        volume_size=BASE_VOLUME_SIZE,
        cam_dist=BASE_CAMERA_DISTANCE,
        step_size=BASE_STEP_SIZE,
    )


@pytest.mark.parametrize(
    "volume_size",
    [
        64,
        128,
        192,
        256,
    ],
)
def test_forward_renderer_volume_size(benchmark, volume_size):
    _benchmark_forward_render(
        benchmark,
        render_size=BASE_RENDER_SIZE,
        volume_size=volume_size,
        cam_dist=BASE_CAMERA_DISTANCE,
        step_size=BASE_STEP_SIZE,
    )


@pytest.mark.parametrize(
    "step_size",
    [
        0.02,
        0.01,
        0.005,
        0.0025,
        0.001,
    ],
)
def test_forward_renderer_step_size(benchmark, step_size):
    _benchmark_forward_render(
        benchmark,
        render_size=BASE_RENDER_SIZE,
        volume_size=BASE_VOLUME_SIZE,
        cam_dist=BASE_CAMERA_DISTANCE,
        step_size=step_size,
    )


@pytest.mark.parametrize(
    "volume_size",
    [
        64,
        96,
        128,
        192,
        256,
    ],
)
def test_density_buffer_creation(benchmark, volume_size):
    density_arr = np.ascontiguousarray(_random_volume_data(volume_size)[:, :, :, 0])

    def create_buffer():
        buffer = device.create_buffer(
            format=spy.Format.r32_float,
            usage=spy.BufferUsage.shader_resource,
            data=density_arr,
        )
        return buffer

    benchmark(create_buffer)


@pytest.mark.parametrize(
    "volume_size",
    [
        64,
        96,
        128,
        192,
        256,
        320,
    ],
)
def test_forward_renderer_dispatch_volume_size(benchmark, volume_size):
    renderer, forward_kernel, thread_count, uniforms = _prepare_forward_dispatch(
        BASE_RENDER_SIZE,
        volume_size,
        BASE_CAMERA_DISTANCE,
        BASE_STEP_SIZE,
    )

    def dispatch_kernel():
        _ = renderer
        forward_kernel.dispatch(
            thread_count=thread_count,
            uniforms=uniforms,
        )
        device.wait()

    benchmark(dispatch_kernel)


@pytest.mark.parametrize(
    "render_size",
    [
        256,
        384,
        512,
        768,
        1024,
    ],
)
def test_forward_renderer_dispatch_render_size(benchmark, render_size):
    renderer, forward_kernel, thread_count, uniforms = _prepare_forward_dispatch(
        render_size,
        BASE_VOLUME_SIZE,
        BASE_CAMERA_DISTANCE,
        BASE_STEP_SIZE,
    )

    def dispatch_kernel():
        _ = renderer
        forward_kernel.dispatch(
            thread_count=thread_count,
            uniforms=uniforms,
        )
        device.wait()

    benchmark(dispatch_kernel)


@pytest.mark.parametrize(
    "render_size",
    [
        256,
        384,
        512,
        768,
        1024,
    ],
)
def test_backward_renderer_render_size(benchmark, render_size):
    _benchmark_backward_render(
        benchmark,
        render_size=render_size,
        volume_size=BASE_VOLUME_SIZE,
        cam_dist=BASE_CAMERA_DISTANCE,
        step_size=BASE_STEP_SIZE,
    )


@pytest.mark.parametrize(
    "volume_size",
    [
        64,
        128,
        192,
        256,
    ],
)
def test_backward_renderer_volume_size(benchmark, volume_size):
    _benchmark_backward_render(
        benchmark,
        render_size=BASE_RENDER_SIZE,
        volume_size=volume_size,
        cam_dist=BASE_CAMERA_DISTANCE,
        step_size=BASE_STEP_SIZE,
    )


@pytest.mark.parametrize(
    "volume_size",
    [
        64,
        96,
        128,
        192,
        256,
    ],
)
def test_backward_renderer_dispatch_volume_size(benchmark, volume_size):
    (
        renderer,
        d_output_tex,
        backward_kernel,
        thread_count,
        uniforms,
    ) = _prepare_backward_dispatch(
        BASE_RENDER_SIZE,
        volume_size,
        BASE_CAMERA_DISTANCE,
        BASE_STEP_SIZE,
    )

    def dispatch_kernel():
        _ = renderer, d_output_tex
        backward_kernel.dispatch(
            thread_count=thread_count,
            uniforms=uniforms,
        )
        device.wait()

    benchmark(dispatch_kernel)


@pytest.mark.parametrize(
    "render_size",
    [
        256,
        384,
        512,
        768,
        1024,
    ],
)
def test_backward_renderer_dispatch_render_size(benchmark, render_size):
    (
        renderer,
        d_output_tex,
        backward_kernel,
        thread_count,
        uniforms,
    ) = _prepare_backward_dispatch(
        render_size,
        BASE_VOLUME_SIZE,
        BASE_CAMERA_DISTANCE,
        BASE_STEP_SIZE,
    )

    def dispatch_kernel():
        _ = renderer, d_output_tex
        backward_kernel.dispatch(
            thread_count=thread_count,
            uniforms=uniforms,
        )
        device.wait()

    benchmark(dispatch_kernel)
