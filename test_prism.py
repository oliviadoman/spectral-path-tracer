"""
Spectral path tracer scenes:
  Scene 1 (Task 5): Triangular glass prism with caustic rainbow on ground
  Scene 2 (Task 7): Glass sphere showing chromatic aberration
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
    """Create a triangular prism mesh.

    The cross-section is an isosceles triangle in the XY plane with the apex pointing up (+y).
    The prism extends along the Z axis.

    Args:
        apex_half_angle_deg: Half the apex angle in degrees (30 = equilateral, smaller = narrower).
        base_width: Width of the base of the triangle.
        depth: Length of the prism along Z.
    """
    half_base = base_width / 2.0
    height = half_base / math.tan(math.radians(apex_half_angle_deg))
    d = depth / 2.0

    # Centroid at origin
    cy = height / 3.0  # centroid is 1/3 up from base

    vertices = np.array([
        [-half_base, -cy,         -d],  # 0: front base-left
        [ half_base, -cy,         -d],  # 1: front base-right
        [       0.0, height - cy, -d],  # 2: front apex
        [-half_base, -cy,          d],  # 3: back base-left
        [ half_base, -cy,          d],  # 4: back base-right
        [       0.0, height - cy,  d],  # 5: back apex
    ], dtype=np.float64)

    # Triangles with outward normals (verified by cross-product)
    triangles = np.array([
        [0, 2, 1],  # front cap  (-z)
        [3, 4, 5],  # back cap   (+z)
        [0, 1, 4],  # bottom     (-y)
        [0, 4, 3],  # bottom     (-y)
        [1, 2, 5],  # right face (outward right)
        [1, 5, 4],  # right face (outward right)
        [2, 0, 3],  # left face  (outward left)
        [2, 3, 5],  # left face  (outward left)
    ], dtype=np.int32)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.compute_vertex_normals()
    return mesh


def create_wall_o3d(width=10.0, height=10.0):
    """Create a flat rectangular wall mesh in the XY plane, centered at origin, facing +z."""
    hw, hh = width / 2.0, height / 2.0
    vertices = np.array([
        [-hw, -hh, 0],
        [ hw, -hh, 0],
        [ hw,  hh, 0],
        [-hw,  hh, 0],
    ], dtype=np.float64)
    triangles = np.array([
        [0, 1, 2],
        [0, 2, 3],
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


def render_scene(renderer, output_image, scene, spp=512, path_depth=6, exposure=1.0, filename="output.png"):
    triangles, materials = scene.extract_triangles_with_material()
    bvh = BVH(primitives=triangles, max_nodes=8192, min_prim_per_node=4)
    renderer.load_bvh(triangles, bvh)
    renderer.load_materials(materials)
    renderer.load_lights(scene=scene)

    print(f"Rendering {filename} at {spp} spp (depth={path_depth})...")
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
        if (i + 1) % 128 == 0:
            print(f"  {i+1}/{spp}")

    image_array = output_image.to_numpy()
    tone_mapped = tone_mapping(image_array, exposure=exposure)
    pil_image = Image.fromarray((np.flipud(tone_mapped) * 255).astype(np.uint8))
    pil_image.save(filename)
    print(f"  Saved {filename}")


# ──────────────────────────────────────────────
# Scene 1: Prism with caustic rainbow on ground
# ──────────────────────────────────────────────
def build_prism_scene():
    scene = Scene()
    scene.ambient_color = (0.0, 0.0, 0.0, 1.0)  # black background

    # Camera: looking down at the ground from front-right
    eye = glm.vec3(5.0, 6.0, 8.0)
    target = glm.vec3(1.0, 0.0, 0.0)
    scene.camera = PerspectiveCamera(
        fov=50.0,
        transform=Transform3D(
            position=eye,
            rotation=glm.quatLookAt(glm.normalize(target - eye), glm.vec3(0, 1, 0)),
        ),
    )

    # Ground plane (large white Lambertian surface to catch the caustic rainbow)
    ground_mesh = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(ground_mesh, name="ground")
    ground.transform.position = glm.vec3(0.0, 0.0, 0.0)
    ground.transform.scale = glm.vec3(20.0, 1.0, 20.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.9, 0.9, 0.9)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    # Glass prism — hovering above the ground
    # Use a 40° apex angle (narrower than equilateral) to avoid total internal reflection
    # with the high flint glass IOR (~1.7).
    prism_mesh = create_prism_o3d(apex_half_angle_deg=20.0, base_width=2.5, depth=6.0)
    prism = Mesh(prism_mesh, name="prism")
    prism.transform.position = glm.vec3(0.0, 3.5, 0.0)
    prism.transform.scale = glm.vec3(1.0, 1.0, 1.0)
    prism.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(1.0, 1.0, 1.0)),
        brdf_type=BRDFType.GLASS,
    )
    prism.material.ior = 1.5  # base IOR (overridden per-wavelength by Cauchy)
    scene.add_object(prism)

    # Rectangular light — positioned above and to the left of the prism,
    # shining down through the prism onto the ground.
    # The light acts as a bright slit source.
    light = RectangularLight(
        name="slit_light",
        transform=Transform3D(
            position=glm.vec3(-3.0, 9.0, 0.0),
            rotation=glm.angleAxis(glm.radians(60.0), glm.vec3(0.0, 0.0, 1.0)),
        ),
        vertices=[
            glm.vec3(-0.3, 0.0, -3.0),
            glm.vec3( 0.3, 0.0, -3.0),
            glm.vec3( 0.3, 0.0,  3.0),
            glm.vec3(-0.3, 0.0,  3.0),
        ],
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=15.0,
        doubleSided=True,
    )
    scene.add_object(light)

    return scene


# ──────────────────────────────────────────────
# Scene 2: Prism viewed from front (direct view through prism at a light)
# ──────────────────────────────────────────────
def build_prism_direct_scene():
    scene = Scene()
    scene.ambient_color = (0.0, 0.0, 0.0, 1.0)

    # Camera looking at the prism from the front
    eye = glm.vec3(0.0, 1.0, 8.0)
    target = glm.vec3(0.0, 1.5, 0.0)
    scene.camera = PerspectiveCamera(
        fov=40.0,
        transform=Transform3D(
            position=eye,
            rotation=glm.quatLookAt(glm.normalize(target - eye), glm.vec3(0, 1, 0)),
        ),
    )

    # Glass prism at center
    prism_mesh = create_prism_o3d(apex_half_angle_deg=20.0, base_width=3.0, depth=5.0)
    prism = Mesh(prism_mesh, name="prism")
    prism.transform.position = glm.vec3(0.0, 1.5, 0.0)
    prism.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(1.0, 1.0, 1.0)),
        brdf_type=BRDFType.GLASS,
    )
    prism.material.ior = 1.5
    scene.add_object(prism)

    # Large rectangular light behind and above the prism
    light = RectangularLight(
        name="back_light",
        transform=Transform3D(
            position=glm.vec3(0.0, 4.0, -5.0),
            rotation=glm.angleAxis(glm.radians(-30.0), glm.vec3(1.0, 0.0, 0.0)),
        ),
        vertices=[
            glm.vec3(-4.0, 0.0, -2.0),
            glm.vec3( 4.0, 0.0, -2.0),
            glm.vec3( 4.0, 0.0,  2.0),
            glm.vec3(-4.0, 0.0,  2.0),
        ],
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=8.0,
        doubleSided=True,
    )
    scene.add_object(light)

    # Ground plane (to give some context)
    ground_mesh = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(ground_mesh, name="ground")
    ground.transform.scale = glm.vec3(15.0, 1.0, 15.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.3, 0.3, 0.3)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    return scene


# ──────────────────────────────────────────────
# Scene 3: Glass sphere — chromatic aberration
# ──────────────────────────────────────────────
def build_sphere_scene():
    scene = Scene()
    scene.ambient_color = (0.0, 0.0, 0.0, 1.0)

    # Camera close to the sphere to see edge fringing
    eye = glm.vec3(0.0, 2.0, 5.0)
    target = glm.vec3(0.0, 1.2, 0.0)
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
    sphere.material.ior = 1.5
    scene.add_object(sphere)

    # White ground plane
    ground_mesh = o3d.io.read_triangle_mesh("resources/plane.obj")
    ground = Mesh(ground_mesh, name="ground")
    ground.transform.scale = glm.vec3(15.0, 1.0, 15.0)
    ground.material = PhysicsBasedMaterial(
        albedo=MaterialField(uniform_value=glm.vec3(0.9, 0.9, 0.9)),
        brdf_type=BRDFType.LAMBERTIAN,
    )
    scene.add_object(ground)

    # Bright point light above-right for strong specular highlights + caustic
    light = PointLight(
        name="key_light",
        position=glm.vec3(3.0, 6.0, 4.0),
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=300.0,
    )
    scene.add_object(light)

    # Fill rectangular light for softer illumination
    fill_light = RectangularLight(
        name="fill_light",
        transform=Transform3D(
            position=glm.vec3(-4.0, 8.0, -2.0),
            rotation=glm.angleAxis(glm.radians(45.0), glm.vec3(1.0, 0.0, 0.0)),
        ),
        vertices=[
            glm.vec3(-2.0, 0.0, -2.0),
            glm.vec3( 2.0, 0.0, -2.0),
            glm.vec3( 2.0, 0.0,  2.0),
            glm.vec3(-2.0, 0.0,  2.0),
        ],
        color=glm.vec3(1.0, 1.0, 1.0),
        intensity=5.0,
        doubleSided=True,
    )
    scene.add_object(fill_light)

    return scene


def main():
    renderer, output_image = setup_renderer(img_size=(512, 512))

    # Render all three scenes
    scenes = [
        ("prism_caustic.png",  build_prism_scene(),        1024, 6, 2.0),
        ("prism_direct.png",   build_prism_direct_scene(),  512, 6, 1.5),
        ("sphere_spectral.png", build_sphere_scene(),       512, 4, 1.0),
    ]

    for filename, scene, spp, depth, exposure in scenes:
        render_scene(renderer, output_image, scene, spp=spp,
                     path_depth=depth, exposure=exposure, filename=filename)


if __name__ == "__main__":
    main()
