"""
Scene serialization module for saving and loading scene graphs.
"""

import json
import zipfile
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pyglm import glm
import io
import open3d as o3d

from cs248a_renderer.model.scene import Scene
from cs248a_renderer.model.scene_object import SceneObject
from cs248a_renderer.model.mesh import Mesh, Triangle
from cs248a_renderer.model.volumes import DenseVolume, VolumeProperties
from cs248a_renderer.model.cameras import PerspectiveCamera
from cs248a_renderer.model.transforms import Transform3D
from cs248a_renderer.model.material import (
    PhysicsBasedMaterial,
    MaterialField,
    FilteringMethod,
    BRDFType,
)
from cs248a_renderer.model.lights import (
    PointLight,
    DirectionalLight,
    RectangularLight,
)

logger = logging.getLogger(__name__)


class SceneSerializer:
    """Handles serialization and deserialization of Scene objects to/from zip files."""

    def __init__(self):
        self.mesh_counter = 0
        self.volume_counter = 0
        self.texture_counter = 0

    def serialize_to_zip(self, scene: Scene, zip_path: Path) -> None:
        """Serialize a scene to a zip file.

        :param scene: The Scene object to serialize.
        :param zip_path: Path where the zip file will be saved.
        """
        logger.info(f"Serializing scene to {zip_path}")
        self.mesh_counter = 0
        self.volume_counter = 0
        self.texture_counter = 0

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Serialize scene metadata
            scene_metadata = {
                "version": "1.0",
                "ambient_color": list(scene.ambient_color),
            }
            zipf.writestr("metadata.json", json.dumps(scene_metadata, indent=2))

            # Serialize camera
            camera_data = self._serialize_camera(scene.camera)
            zipf.writestr("camera.json", json.dumps(camera_data, indent=2))

            # Serialize scene graph (lights excluded)
            scene_graph = self._serialize_scene_object(scene.root, zipf)
            zipf.writestr("scene_graph.json", json.dumps(scene_graph, indent=2))

            # Serialize lights separately
            lights_data = self._serialize_lights(scene, zipf)
            zipf.writestr("lights.json", json.dumps(lights_data, indent=2))

        logger.info(f"Scene successfully serialized to {zip_path}")

    def _serialize_camera(self, camera: PerspectiveCamera) -> Dict[str, Any]:
        """Serialize a PerspectiveCamera to a dictionary."""
        return {
            "type": "PerspectiveCamera",
            "name": camera.name,
            "fov": camera.fov,
            "near": camera.near,
            "far": camera.far,
            "transform": self._serialize_transform(camera.transform),
        }

    def _serialize_transform(self, transform: Transform3D) -> Dict[str, List[float]]:
        """Serialize a Transform3D to a dictionary."""
        return {
            "position": [
                transform.position.x,
                transform.position.y,
                transform.position.z,
            ],
            "rotation": [
                transform.rotation.x,
                transform.rotation.y,
                transform.rotation.z,
                transform.rotation.w,
            ],
            "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
        }

    def _serialize_scene_object(
        self, obj: SceneObject, zipf: zipfile.ZipFile
    ) -> Dict[str, Any]:
        """Serialize a SceneObject and its children recursively (lights excluded)."""
        obj_data = {
            "type": self._get_object_type(obj),
            "name": obj.name,
            "transform": self._serialize_transform(obj.transform),
            "children": [],
        }

        # Handle specific object types
        if isinstance(obj, Mesh):
            mesh_data = self._serialize_mesh(obj, zipf)
            obj_data.update(mesh_data)
        elif isinstance(obj, DenseVolume):
            volume_data = self._serialize_volume(obj, zipf)
            obj_data.update(volume_data)
        elif isinstance(obj, PerspectiveCamera):
            camera_data = self._serialize_camera(obj)
            obj_data.update(camera_data)

        # Recursively serialize children (skip lights - they're handled separately)
        for child in obj.children:
            if not isinstance(child, (PointLight, DirectionalLight, RectangularLight)):
                child_data = self._serialize_scene_object(child, zipf)
                obj_data["children"].append(child_data)

        return obj_data

    def _get_object_type(self, obj: SceneObject) -> str:
        """Get the type name of a SceneObject."""
        if isinstance(obj, PerspectiveCamera):
            return "PerspectiveCamera"
        elif isinstance(obj, Mesh):
            return "Mesh"
        elif isinstance(obj, DenseVolume):
            return "DenseVolume"
        else:
            return "SceneObject"

    def _serialize_mesh(self, mesh: Mesh, zipf: zipfile.ZipFile) -> Dict[str, Any]:
        """Serialize a Mesh object."""
        mesh_data = {
            "mesh_data_file": f"meshes/mesh_{self.mesh_counter}.npz",
            "material": self._serialize_material(mesh.material, zipf),
        }

        # Save mesh data (triangles)
        vertices_list = []
        colors_list = []
        uvs_list = []
        normals_list = []

        for triangle in mesh.triangles:
            vertices_list.append([list(v) for v in triangle.vertices])
            colors_list.append([list(c) for c in triangle.colors])
            uvs_list.append([list(u) for u in triangle.uvs])
            normals_list.append([list(n) for n in triangle.normals])

        mesh_arrays = {
            "vertices": np.array(vertices_list, dtype=np.float32),
            "colors": np.array(colors_list, dtype=np.float32),
            "uvs": np.array(uvs_list, dtype=np.float32),
            "normals": np.array(normals_list, dtype=np.float32),
        }

        # Write to zip
        with io.BytesIO() as buffer:
            np.savez_compressed(buffer, **mesh_arrays)
            buffer.seek(0)
            zipf.writestr(mesh_data["mesh_data_file"], buffer.read())

        self.mesh_counter += 1
        return mesh_data

    def _serialize_material(
        self, material: PhysicsBasedMaterial, zipf: zipfile.ZipFile
    ) -> Dict[str, Any]:
        """Serialize a PhysicsBasedMaterial."""
        material_data = {
            "albedo": self._serialize_material_field(material.albedo, zipf),
            "smoothness": material.smoothness,
            "brdf_type": material.brdf_type.value,
            "ior": material.ior,
        }
        return material_data

    def _serialize_material_field(
        self, field: MaterialField, zipf: zipfile.ZipFile
    ) -> Dict[str, Any]:
        """Serialize a MaterialField."""
        field_data = {
            "uniform_value": None,
            "use_texture": field.use_texture,
            "filtering_method": field.filtering_method.value,
            "textures": [],
        }

        if field.uniform_value is not None:
            if isinstance(field.uniform_value, glm.vec3):
                field_data["uniform_value"] = [
                    field.uniform_value.x,
                    field.uniform_value.y,
                    field.uniform_value.z,
                ]
            else:
                field_data["uniform_value"] = field.uniform_value

        # Save textures
        for i, texture in enumerate(field.textures):
            texture_file = f"textures/texture_{self.texture_counter}_{i}.npz"
            with io.BytesIO() as buffer:
                np.savez_compressed(buffer, texture=texture)
                buffer.seek(0)
                zipf.writestr(texture_file, buffer.read())
            field_data["textures"].append(texture_file)

        self.texture_counter += 1
        return field_data

    def _serialize_volume(
        self, volume: DenseVolume, zipf: zipfile.ZipFile
    ) -> Dict[str, Any]:
        """Serialize a DenseVolume object."""
        volume_data = {
            "volume_data_file": f"volumes/volume_{self.volume_counter}.npz",
            "properties": {
                "voxel_size": volume.properties["voxel_size"],
                "pivot": volume.properties["pivot"],
            },
        }

        # Save volume data
        with io.BytesIO() as buffer:
            np.savez_compressed(buffer, data=volume.data)
            buffer.seek(0)
            zipf.writestr(volume_data["volume_data_file"], buffer.read())

        self.volume_counter += 1
        return volume_data

    def _serialize_lights(self, scene: Scene, zipf: zipfile.ZipFile) -> Dict[str, Any]:
        """Serialize all lights in the scene."""
        lights_data = {
            "point_lights": [],
            "directional_lights": [],
            "rectangular_lights": [],
        }

        for light in scene.point_lights:
            light_data = {
                "type": "PointLight",
                "name": light.name,
                "transform": self._serialize_transform(light.transform),
                "color": [light.color.x, light.color.y, light.color.z],
                "intensity": light.intensity,
            }
            lights_data["point_lights"].append(light_data)

        for light in scene.directional_lights:
            light_data = {
                "type": "DirectionalLight",
                "name": light.name,
                "transform": self._serialize_transform(light.transform),
                "direction": [light.direction.x, light.direction.y, light.direction.z],
                "color": [light.color.x, light.color.y, light.color.z],
                "intensity": light.intensity,
            }
            lights_data["directional_lights"].append(light_data)

        for light in scene.rectangular_lights:
            light_data = {
                "type": "RectangularLight",
                "name": light.name,
                "transform": self._serialize_transform(light.transform),
                "vertices": [[v.x, v.y, v.z] for v in light.vertices],
                "color": [light.color.x, light.color.y, light.color.z],
                "intensity": light.intensity,
                "doubleSided": light.doubleSided,
            }
            lights_data["rectangular_lights"].append(light_data)

        return lights_data

    def deserialize_from_zip(self, zip_path: Path) -> Scene:
        """Deserialize a scene from a zip file.

        :param zip_path: Path to the zip file.
        :return: The deserialized Scene object.
        """
        logger.info(f"Deserializing scene from {zip_path}")

        scene = Scene()

        with zipfile.ZipFile(zip_path, "r") as zipf:
            # Load metadata
            with zipf.open("metadata.json") as f:
                metadata = json.load(f)
                scene.ambient_color = tuple(metadata["ambient_color"])

            # Load camera
            with zipf.open("camera.json") as f:
                camera_data = json.load(f)
                scene.camera = self._deserialize_camera(camera_data)

            # Load scene graph
            with zipf.open("scene_graph.json") as f:
                scene_graph = json.load(f)
                scene.root = self._deserialize_scene_object(scene_graph, zipf)
                scene.lookup[scene.root.name] = scene.root
                self._update_lookup_recursive(scene.root, scene.lookup)

            # Load lights separately
            if "lights.json" in zipf.namelist():
                with zipf.open("lights.json") as f:
                    lights_data = json.load(f)
                    self._deserialize_lights(lights_data, scene, zipf)

        logger.info(f"Scene successfully deserialized from {zip_path}")
        return scene

    def _deserialize_camera(self, camera_data: Dict[str, Any]) -> PerspectiveCamera:
        """Deserialize a PerspectiveCamera from a dictionary."""
        transform = self._deserialize_transform(camera_data["transform"])
        camera = PerspectiveCamera(
            name=camera_data["name"],
            fov=camera_data["fov"],
            near=camera_data["near"],
            far=camera_data["far"],
            transform=transform,
        )
        return camera

    def _deserialize_transform(
        self, transform_data: Dict[str, List[float]]
    ) -> Transform3D:
        """Deserialize a Transform3D from a dictionary."""
        pos = transform_data["position"]
        rot = transform_data["rotation"]
        scale = transform_data["scale"]

        return Transform3D(
            position=glm.vec3(pos[0], pos[1], pos[2]),
            rotation=glm.quat(
                rot[3], rot[0], rot[1], rot[2]
            ),  # glm.quat is (w, x, y, z)
            scale=glm.vec3(scale[0], scale[1], scale[2]),
        )

    def _deserialize_scene_object(
        self, obj_data: Dict[str, Any], zipf: zipfile.ZipFile
    ) -> SceneObject:
        """Deserialize a SceneObject and its children recursively."""
        obj_type = obj_data["type"]
        name = obj_data["name"]
        transform = self._deserialize_transform(obj_data["transform"])

        if obj_type == "Mesh":
            obj = self._deserialize_mesh(obj_data, zipf, name, transform)
        elif obj_type == "DenseVolume":
            obj = self._deserialize_volume(obj_data, zipf, name, transform)
        else:
            obj = SceneObject(name=name, transform=transform)

        # Recursively deserialize children
        for child_data in obj_data.get("children", []):
            child = self._deserialize_scene_object(child_data, zipf)
            obj.children.append(child)
            child.parent = obj

        return obj

    def _deserialize_mesh(
        self,
        mesh_data: Dict[str, Any],
        zipf: zipfile.ZipFile,
        name: str,
        transform: Transform3D,
    ) -> Mesh:
        """Deserialize a Mesh object."""
        mesh = Mesh(name=name, transform=transform)

        # Load mesh data
        mesh_file = mesh_data["mesh_data_file"]
        with zipf.open(mesh_file) as f:
            arrays = np.load(io.BytesIO(f.read()), allow_pickle=True)
            vertices = arrays["vertices"]
            colors = arrays["colors"]
            uvs = arrays["uvs"]
            normals = arrays["normals"]

            mesh.triangles = []
            for i in range(len(vertices)):
                triangle = Triangle(
                    vertices=[glm.vec3(*v) for v in vertices[i]],
                    colors=[glm.vec3(*c) for c in colors[i]],
                    uvs=[glm.vec2(*u) for u in uvs[i]],
                    normals=[glm.vec3(*n) for n in normals[i]],
                )
                mesh.triangles.append(triangle)

        # Compute bounding box from triangles
        mesh._compute_bounding_box_from_triangles()

        # Create o3d mesh for rendering
        o3d_mesh = self._create_o3d_mesh_from_triangles(mesh.triangles)
        mesh._o3d_mesh = o3d_mesh

        # Load material
        mesh.material = self._deserialize_material(mesh_data["material"], zipf)

        return mesh

    def _deserialize_material(
        self, material_data: Dict[str, Any], zipf: zipfile.ZipFile
    ) -> PhysicsBasedMaterial:
        """Deserialize a PhysicsBasedMaterial."""
        material = PhysicsBasedMaterial()
        material.albedo = self._deserialize_material_field(
            material_data["albedo"], zipf
        )
        if "smoothness" in material_data:
            material.smoothness = material_data["smoothness"]
        if "brdf_type" in material_data:
            material.brdf_type = BRDFType(material_data["brdf_type"])
        if "ior" in material_data:
            material.ior = material_data["ior"]
        return material

    def _create_o3d_mesh_from_triangles(
        self, triangles: List[Triangle]
    ) -> o3d.geometry.TriangleMesh:
        """Create an open3d mesh from a list of Triangle objects.

        :param triangles: List of Triangle objects to convert
        :return: open3d TriangleMesh object
        """
        if not triangles:
            return o3d.geometry.TriangleMesh()

        # Collect all vertices, normals, colors
        vertices_list = []
        normals_list = []
        colors_list = []
        triangle_indices = []

        # Each triangle has 3 vertices, so we need 3 vertex entries per triangle
        for tri_idx, triangle in enumerate(triangles):
            start_vertex_idx = tri_idx * 3

            # Add vertices for this triangle
            for i in range(3):
                vertices_list.append(
                    [
                        triangle.vertices[i].x,
                        triangle.vertices[i].y,
                        triangle.vertices[i].z,
                    ]
                )
                normals_list.append(
                    [
                        triangle.normals[i].x,
                        triangle.normals[i].y,
                        triangle.normals[i].z,
                    ]
                )
                colors_list.append(
                    [triangle.colors[i].x, triangle.colors[i].y, triangle.colors[i].z]
                )

            # Add triangle indices (0, 1, 2), (3, 4, 5), etc.
            triangle_indices.append(
                [start_vertex_idx, start_vertex_idx + 1, start_vertex_idx + 2]
            )

        # Convert to numpy arrays
        vertices_array = np.array(vertices_list, dtype=np.float64)
        normals_array = np.array(normals_list, dtype=np.float64)
        colors_array = np.array(colors_list, dtype=np.float64)
        triangles_array = np.array(triangle_indices, dtype=np.int32)

        # Create o3d mesh
        o3d_mesh = o3d.geometry.TriangleMesh()
        o3d_mesh.vertices = o3d.utility.Vector3dVector(vertices_array)
        o3d_mesh.triangles = o3d.utility.Vector3iVector(triangles_array)
        o3d_mesh.vertex_normals = o3d.utility.Vector3dVector(normals_array)
        o3d_mesh.vertex_colors = o3d.utility.Vector3dVector(colors_array)

        return o3d_mesh

    def _deserialize_material_field(
        self, field_data: Dict[str, Any], zipf: zipfile.ZipFile
    ) -> MaterialField:
        """Deserialize a MaterialField."""
        uniform_value = field_data["uniform_value"]
        if uniform_value is not None:
            if isinstance(uniform_value, list) and len(uniform_value) == 3:
                uniform_value = glm.vec3(
                    uniform_value[0], uniform_value[1], uniform_value[2]
                )

        # Load textures first
        textures = []
        for texture_file in field_data["textures"]:
            with zipf.open(texture_file) as f:
                arrays = np.load(io.BytesIO(f.read()), allow_pickle=True)
                textures.append(arrays["texture"])

        # Create field with textures
        field = MaterialField(
            uniform_value=uniform_value,
            use_texture=field_data["use_texture"],
            filtering_method=FilteringMethod(field_data["filtering_method"]),
            textures=textures,
        )

        return field

    def _deserialize_volume(
        self,
        volume_data: Dict[str, Any],
        zipf: zipfile.ZipFile,
        name: str,
        transform: Transform3D,
    ) -> DenseVolume:
        """Deserialize a DenseVolume object."""
        # Load volume data
        volume_file = volume_data["volume_data_file"]
        with zipf.open(volume_file) as f:
            arrays = np.load(io.BytesIO(f.read()), allow_pickle=True)
            data = arrays["data"]

        properties: VolumeProperties = {
            "voxel_size": volume_data["properties"]["voxel_size"],
            "pivot": tuple(volume_data["properties"]["pivot"]),
        }

        volume = DenseVolume(
            name=name, transform=transform, data=data, properties=properties
        )
        return volume

    def _deserialize_lights(
        self, lights_data: Dict[str, Any], scene: Scene, zipf: zipfile.ZipFile
    ) -> None:
        """Deserialize all lights and add them to the scene."""
        # Deserialize point lights
        for light_data in lights_data.get("point_lights", []):
            transform = self._deserialize_transform(light_data["transform"])
            color_list = light_data["color"]
            light = PointLight(
                name=light_data["name"],
                transform=transform,
                color=glm.vec3(color_list[0], color_list[1], color_list[2]),
                intensity=light_data["intensity"],
            )
            scene.add_object(light)
            scene.point_lights.append(light)

        # Deserialize directional lights
        for light_data in lights_data.get("directional_lights", []):
            transform = self._deserialize_transform(light_data["transform"])
            direction_list = light_data["direction"]
            color_list = light_data["color"]
            light = DirectionalLight(
                name=light_data["name"],
                transform=transform,
                direction=glm.vec3(
                    direction_list[0], direction_list[1], direction_list[2]
                ),
                color=glm.vec3(color_list[0], color_list[1], color_list[2]),
                intensity=light_data["intensity"],
            )
            scene.add_object(light)
            scene.directional_lights.append(light)

        # Deserialize rectangular lights
        for light_data in lights_data.get("rectangular_lights", []):
            transform = self._deserialize_transform(light_data["transform"])
            vertices = [glm.vec3(v[0], v[1], v[2]) for v in light_data["vertices"]]
            color_list = light_data["color"]
            light = RectangularLight(
                name=light_data["name"],
                transform=transform,
                vertices=vertices,
                color=glm.vec3(color_list[0], color_list[1], color_list[2]),
                intensity=light_data["intensity"],
                doubleSided=light_data["doubleSided"],
            )
            scene.add_object(light)
            scene.rectangular_lights.append(light)

    def _update_lookup_recursive(
        self, obj: SceneObject, lookup: Dict[str, SceneObject]
    ) -> None:
        """Recursively update the lookup dictionary with all objects in the scene graph."""
        for child in obj.children:
            lookup[child.name] = child
            self._update_lookup_recursive(child, lookup)
