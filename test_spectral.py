"""
Quick visual test for the spectral path tracer (Tasks 1-3).
Renders a glass sphere with a point light and saves the output.
If spectral dispersion is working, you should see faint color fringing
at the sphere edges (chromatic aberration).
"""
import sys
sys.path.insert(0, "src")

import open3d as o3d
import numpy as np
from pyglm import glm
from PIL import Image
import slangpy as spy

from cs248a_renderer import setup_device, RendererModules
from cs248a_renderer.model.scene import Scene
from cs248a_renderer.model.mesh import Mesh
from cs248a_renderer.model.material import PhysicsBasedMaterial, MaterialField, BRDFType
from cs248a_renderer.model.lights import PointLight
from cs248a_renderer.model.cameras import PerspectiveCamera
from cs248a_renderer.model.transforms import Transform3D
from cs248a_renderer.renderer.core_renderer import Renderer
from cs248a_renderer.model.bvh import BVH

def tone_mapping(image_np, gamma=2.2, exposure=1.0):
    rgb = np.power(np.clip(image_np[:, :, :3] * exposure, 0, None), 1.0 / gamma)
    return np.clip(rgb, 0.0, 1.0)

def main():
    # --- Device & renderer setup ---
    device = setup_device([])
    IMG_SIZE = (512, 512)
    output_image = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        usage=spy.TextureUsage.unordered_access,
        width=IMG_SIZE[0], height=IMG_SIZE[1],
    )
    renderer_modules = RendererModules(device)
    renderer = Renderer(device=device, render_texture=output_image, render_modules=renderer_modules)

    # --- Scene ---
    scene = Scene()

    # Camera
    eye = glm.vec3(0.0, 2.0, 6.0)
    target = glm.vec3(0.0, 1.0, 0.0)
    scene.camera = PerspectiveCamera(
        fov=45.0,
        transform=Transform3D(
            position=eye,
            rotation=glm.quatLookAt(glm.normalize(target - eye), glm.vec3(0, 1, 0)),
        ),
    )

    # Glass sphere
    o3d_mesh = o3d.io.read_triangle_mesh("resources/uv_sphere_smooth.obj")
    sphere = Mesh(o3d_mesh, name="glass_sphere")
    sphere.transform.position = glm.vec3(0.0, 1.5, 0.0)
    sphere.transform.scale = glm.vec3(1.5, 1.5, 1.5)
    sphere.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(1.0, 1.0, 1.0)),
        brdf_type=BRDFType.GLASS,
    )
    sphere.material.ior = 1.5  # will be overridden by Cauchy per-wavelength
    scene.add_object(sphere)

    # Ground plane
    o3d_plane = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(o3d_plane, name="ground")
    ground.transform.position = glm.vec3(0.0, 0.0, 0.0)
    ground.transform.scale = glm.vec3(10.0, 1.0, 10.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.8, 0.8, 0.8)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    # Point light above and to the side
    light = PointLight(
        name="key_light",
        position=glm.vec3(3.0, 6.0, 4.0),
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=200.0,
    )
    scene.add_object(light)

    # --- Build BVH & load ---
    triangles, materials = scene.extract_triangles_with_material()
    bvh = BVH(primitives=triangles, max_nodes=8192, min_prim_per_node=4)
    renderer.load_bvh(triangles, bvh)
    renderer.load_materials(materials)
    renderer.load_lights(scene=scene)

    # --- Render ---
    SPP = 512
    print(f"Rendering {SPP} spp...")
    renderer.clear_render_target()
    for i in range(SPP):
        renderer.render_step(
            view_mat=scene.camera.view_matrix(),
            fov=scene.camera.fov,
            smooth_shading=True,
            path_trace_depth=4,
            fresnel_effect=True,
            use_cosine_weighted_sampling=True,
        )
        if (i + 1) % 32 == 0:
            print(f"  {i+1}/{SPP} samples done")

    # --- Save output ---
    image_array = output_image.to_numpy()
    tone_mapped = tone_mapping(image_array, exposure=1.0)
    tone_mapped_uint8 = (np.flipud(tone_mapped) * 255).astype(np.uint8)
    pil_image = Image.fromarray(tone_mapped_uint8)
    pil_image.save("test_spectral_output.png")
    print("Saved test_spectral_output.png")

if __name__ == "__main__":
    main()
