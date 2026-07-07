"""
High-quality spectral renders for Tasks 5-7.
  - prism_rainbow.png: View through a glass prism showing spectral dispersion
  - sphere_chromatic.png: Glass sphere with chromatic aberration fringing
"""
import sys, math
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
from cs248a_renderer.model.lights import PointLight, RectangularLight
from cs248a_renderer.model.cameras import PerspectiveCamera
from cs248a_renderer.model.transforms import Transform3D
from cs248a_renderer.renderer.core_renderer import Renderer
from cs248a_renderer.model.bvh import BVH


def tone_mapping(image_np, gamma=2.2, exposure=1.0):
    rgb = np.power(np.clip(image_np[:, :, :3] * exposure, 0, None), 1.0 / gamma)
    return np.clip(rgb, 0.0, 1.0)


def create_prism_o3d(apex_half_angle_deg=30.0, base_width=2.0, depth=6.0):
    half_base = base_width / 2.0
    height = half_base / math.tan(math.radians(apex_half_angle_deg))
    d = depth / 2.0
    cy = height / 3.0

    vertices = np.array([
        [-half_base, -cy,         -d],
        [ half_base, -cy,         -d],
        [       0.0, height - cy, -d],
        [-half_base, -cy,          d],
        [ half_base, -cy,          d],
        [       0.0, height - cy,  d],
    ], dtype=np.float64)

    triangles = np.array([
        [0, 2, 1], [3, 4, 5],
        [0, 1, 4], [0, 4, 3],
        [1, 2, 5], [1, 5, 4],
        [2, 0, 3], [2, 3, 5],
    ], dtype=np.int32)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.compute_vertex_normals()
    return mesh


def setup_renderer(img_size=(512, 512)):
    device = setup_device([])
    output_image = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        usage=spy.TextureUsage.unordered_access,
        width=img_size[0], height=img_size[1],
    )
    renderer_modules = RendererModules(device)
    renderer = Renderer(device=device, render_texture=output_image,
                        render_modules=renderer_modules)
    return renderer, output_image


def render_scene(renderer, output_image, scene, spp, path_depth, exposure, filename):
    triangles, materials = scene.extract_triangles_with_material()
    bvh = BVH(primitives=triangles, max_nodes=8192, min_prim_per_node=4)
    renderer.load_bvh(triangles, bvh)
    renderer.load_materials(materials)
    renderer.load_lights(scene=scene)

    print(f"Rendering {filename} at {spp} spp ...")
    renderer.clear_render_target()
    for i in range(spp):
        renderer.render_step(
            view_mat=scene.camera.view_matrix(),
            fov=scene.camera.fov,
            smooth_shading=True,
            path_trace_depth=path_depth,
            fresnel_effect=True,
            use_cosine_weighted_sampling=True,
        )
        if (i + 1) % 256 == 0:
            print(f"  {i+1}/{spp}")

    image_array = output_image.to_numpy()
    tone_mapped = tone_mapping(image_array, exposure=exposure)
    pil_image = Image.fromarray((np.flipud(tone_mapped) * 255).astype(np.uint8))
    pil_image.save(filename)
    print(f"  Saved {filename}")


def build_prism_scene():
    """Prism scene: camera looks through the prism at a bright light behind it.
    Spectral dispersion creates rainbow fringes at the refracted edges."""
    scene = Scene()
    scene.ambient_color = (0.0, 0.0, 0.0, 1.0)

    eye = glm.vec3(0.0, 1.5, 8.0)
    target = glm.vec3(0.0, 2.0, 0.0)
    scene.camera = PerspectiveCamera(
        fov=40.0,
        transform=Transform3D(
            position=eye,
            rotation=glm.quatLookAt(glm.normalize(target - eye), glm.vec3(0, 1, 0)),
        ),
    )

    # Glass prism — 40° apex (20° half), narrower to reduce TIR with high IOR
    prism_mesh = create_prism_o3d(apex_half_angle_deg=20.0, base_width=3.0, depth=5.0)
    prism = Mesh(prism_mesh, name="prism")
    prism.transform.position = glm.vec3(0.0, 1.8, 0.0)
    prism.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(1.0, 1.0, 1.0)),
        brdf_type=BRDFType.GLASS,
    )
    prism.material.ior = 1.5
    scene.add_object(prism)

    # Large bright rectangular light behind the prism
    light = RectangularLight(
        name="back_light",
        transform=Transform3D(
            position=glm.vec3(0.0, 5.0, -6.0),
            rotation=glm.angleAxis(glm.radians(-30.0), glm.vec3(1.0, 0.0, 0.0)),
        ),
        vertices=[
            glm.vec3(-5.0, 0.0, -3.0),
            glm.vec3( 5.0, 0.0, -3.0),
            glm.vec3( 5.0, 0.0,  3.0),
            glm.vec3(-5.0, 0.0,  3.0),
        ],
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=8.0,
        doubleSided=True,
    )
    scene.add_object(light)

    # Dark ground
    ground_mesh = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(ground_mesh, name="ground")
    ground.transform.scale = glm.vec3(20.0, 1.0, 20.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.15, 0.15, 0.15)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    return scene


def build_sphere_scene():
    """Glass sphere on a bright checkerboard-like ground to maximize
    chromatic aberration visibility at the silhouette edges."""
    scene = Scene()
    scene.ambient_color = (0.0, 0.0, 0.0, 1.0)

    eye = glm.vec3(0.0, 2.5, 5.0)
    target = glm.vec3(0.0, 1.5, 0.0)
    scene.camera = PerspectiveCamera(
        fov=40.0,
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
    sphere.material.ior = 1.5
    scene.add_object(sphere)

    # White ground
    ground_mesh = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(ground_mesh, name="ground")
    ground.transform.scale = glm.vec3(15.0, 1.0, 15.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.9, 0.9, 0.9)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    # Strong point light (creates bright caustic + specular)
    light = PointLight(
        name="key_light",
        position=glm.vec3(3.0, 7.0, 5.0),
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=400.0,
    )
    scene.add_object(light)

    # Rectangular light for even illumination
    rect_light = RectangularLight(
        name="rect_light",
        transform=Transform3D(
            position=glm.vec3(0.0, 10.0, 0.0),
        ),
        vertices=[
            glm.vec3(-3.0, 0.0, -3.0),
            glm.vec3( 3.0, 0.0, -3.0),
            glm.vec3( 3.0, 0.0,  3.0),
            glm.vec3(-3.0, 0.0,  3.0),
        ],
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=3.0,
        doubleSided=True,
    )
    scene.add_object(rect_light)

    return scene


def main():
    renderer, output_image = setup_renderer(img_size=(512, 512))

    # Prism: 2048 SPP for clean rainbow fringes
    render_scene(renderer, output_image, build_prism_scene(),
                 spp=2048, path_depth=6, exposure=1.5, filename="prism_rainbow.png")

    # Sphere: 1024 SPP for visible chromatic aberration
    render_scene(renderer, output_image, build_sphere_scene(),
                 spp=1024, path_depth=4, exposure=1.0, filename="sphere_chromatic.png")


if __name__ == "__main__":
    main()
