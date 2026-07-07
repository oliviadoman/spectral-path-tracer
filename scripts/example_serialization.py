#!/usr/bin/env python3
"""
Example script demonstrating scene serialization and deserialization.

This script shows how to:
1. Create a scene with meshes/volumes
2. Serialize it to a zip file
3. Deserialize and verify the loaded scene
"""

import logging
from pathlib import Path
import numpy as np
from pyglm import glm

from cs248a_renderer.view_model.scene_manager import SceneManager
from cs248a_renderer.model.volumes import DenseVolume, VolumeProperties
from cs248a_renderer.model.transforms import Transform3D
from cs248a_renderer.model.scene_object import SceneObject

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def example_serialize_volume_scene():
    """Example: Create, serialize, and deserialize a volume scene."""
    logger.info("=== Volume Scene Serialization Example ===")

    # Create a scene manager
    manager = SceneManager()

    # Create a simple volume (64x64x64 with 4 channels)
    volume_size = (64, 64, 64, 4)
    volume_data = np.random.rand(*volume_size).astype(np.float32)

    # Create a DenseVolume and add it to the scene
    volume = DenseVolume(
        name="test_volume",
        data=volume_data,
        properties=VolumeProperties(voxel_size=0.01, pivot=(0.5, 0.5, 0.5)),
        transform=Transform3D(
            position=glm.vec3(0.0, 0.0, 0.0),
            rotation=glm.quat(1.0, 0.0, 0.0, 0.0),
            scale=glm.vec3(1.0, 1.0, 1.0),
        ),
    )
    manager.scene.add_object(volume)

    # Create additional scene objects with hierarchy
    parent_obj = SceneObject(
        name="parent_object",
        transform=Transform3D(
            position=glm.vec3(1.0, 0.0, 0.0),
            rotation=glm.quat(1.0, 0.0, 0.0, 0.0),
            scale=glm.vec3(1.0, 1.0, 1.0),
        ),
    )
    manager.scene.add_object(parent_obj)

    child_obj = SceneObject(
        name="child_object",
        transform=Transform3D(
            position=glm.vec3(0.5, 0.0, 0.0),
        ),
    )
    manager.scene.add_object(child_obj, parent_name="parent_object")

    # Update camera position
    manager.scene.camera.transform.position = glm.vec3(0.0, 0.0, 3.0)

    # Print scene before serialization
    logger.info("Scene before serialization:")
    logger.info(manager.scene)

    # Serialize the scene
    output_path = Path("example_volume_scene.zip")
    manager.serialize_scene(output_path)
    logger.info(f"✓ Scene serialized to {output_path}")

    # Deserialize into a new manager
    new_manager = SceneManager()
    new_manager.deserialize_scene(output_path)
    logger.info(f"✓ Scene deserialized from {output_path}")

    # Print scene after deserialization
    logger.info("Scene after deserialization:")
    logger.info(new_manager.scene)

    # Verify data integrity
    logger.info("\n=== Verification ===")
    logger.info(f"Original volume shape: {volume_data.shape}")
    deserialized_volume = None
    for child in new_manager.scene.root.children:
        if isinstance(child, DenseVolume):
            deserialized_volume = child
            break

    if deserialized_volume:
        logger.info(f"Deserialized volume shape: {deserialized_volume.data.shape}")
        max_diff = np.max(np.abs(volume_data - deserialized_volume.data))
        logger.info(f"Maximum data difference: {max_diff}")
        if max_diff < 1e-5:
            logger.info("✓ Volume data matches!")
    else:
        logger.warning("✗ Volume not found in deserialized scene")

    # Cleanup
    output_path.unlink()
    logger.info(f"✓ Cleaned up {output_path}")


def example_serialize_scene_with_hierarchy():
    """Example: Create a complex scene with multiple objects and hierarchy."""
    logger.info("\n=== Scene with Hierarchy Example ===")

    manager = SceneManager()

    # Create a hierarchy:
    # root
    #  ├── container_1
    #  │   ├── volume_1
    #  │   └── object_1
    #  └── container_2
    #      └── volume_2

    container_1 = SceneObject(
        name="container_1",
        transform=Transform3D(position=glm.vec3(-2.0, 0.0, 0.0)),
    )
    manager.scene.add_object(container_1)

    container_2 = SceneObject(
        name="container_2",
        transform=Transform3D(position=glm.vec3(2.0, 0.0, 0.0)),
    )
    manager.scene.add_object(container_2)

    # Add volumes to containers
    vol1_data = np.ones((32, 32, 32, 4), dtype=np.float32)
    vol1 = DenseVolume(
        name="volume_1",
        data=vol1_data,
        properties=VolumeProperties(voxel_size=0.01, pivot=(0.5, 0.5, 0.5)),
    )
    manager.scene.add_object(vol1, parent_name="container_1")

    vol2_data = np.ones((32, 32, 32, 4), dtype=np.float32) * 0.5
    vol2 = DenseVolume(
        name="volume_2",
        data=vol2_data,
        properties=VolumeProperties(voxel_size=0.01, pivot=(0.5, 0.5, 0.5)),
    )
    manager.scene.add_object(vol2, parent_name="container_2")

    # Add generic object to container_1
    obj1 = SceneObject(
        name="object_1", transform=Transform3D(position=glm.vec3(0.0, 1.0, 0.0))
    )
    manager.scene.add_object(obj1, parent_name="container_1")

    # Print hierarchy
    logger.info("Scene hierarchy:")
    logger.info(manager.scene)

    # Serialize
    output_path = Path("example_hierarchy_scene.zip")
    manager.serialize_scene(output_path)
    logger.info(f"✓ Hierarchical scene serialized to {output_path}")

    # Deserialize and verify hierarchy
    new_manager = SceneManager()
    new_manager.deserialize_scene(output_path)

    def print_hierarchy(obj, depth=0):
        indent = "  " * depth
        logger.info(f"{indent}├─ {obj.name} ({type(obj).__name__})")
        for child in obj.children:
            print_hierarchy(child, depth + 1)

    logger.info("Deserialized hierarchy:")
    print_hierarchy(new_manager.scene.root)

    # Cleanup
    output_path.unlink()
    logger.info(f"✓ Cleaned up {output_path}")


def example_scene_modifications():
    """Example: Modify a scene after deserialization."""
    logger.info("\n=== Scene Modification Example ===")

    manager = SceneManager()

    # Create initial scene
    vol_data = np.ones((32, 32, 32, 4), dtype=np.float32)
    volume = DenseVolume(
        name="original_volume",
        data=vol_data,
        properties=VolumeProperties(voxel_size=0.01, pivot=(0.5, 0.5, 0.5)),
        transform=Transform3D(position=glm.vec3(0.0, 0.0, 0.0)),
    )
    manager.scene.add_object(volume)

    # Serialize original scene
    path1 = Path("example_scene_v1.zip")
    manager.serialize_scene(path1)
    logger.info(f"✓ Original scene serialized to {path1}")

    # Load and modify
    manager.deserialize_scene(path1)
    manager.scene.camera.fov = 60.0

    # Add a new object
    new_obj = SceneObject(
        name="new_object", transform=Transform3D(position=glm.vec3(1.0, 1.0, 1.0))
    )
    manager.scene.add_object(new_obj)

    # Serialize modified scene
    path2 = Path("example_scene_v2.zip")
    manager.serialize_scene(path2)
    logger.info(f"✓ Modified scene serialized to {path2}")

    # Verify modifications
    final_manager = SceneManager()
    final_manager.deserialize_scene(path2)
    logger.info(f"✓ Camera FOV after reload: {final_manager.scene.camera.fov}°")
    logger.info(
        f"✓ Scene objects: {[obj.name for obj in final_manager.scene.root.children]}"
    )

    # Cleanup
    path1.unlink()
    path2.unlink()
    logger.info("✓ Cleaned up temporary files")


if __name__ == "__main__":
    try:
        example_serialize_volume_scene()
        example_serialize_scene_with_hierarchy()
        example_scene_modifications()
        logger.info("\n✓ All examples completed successfully!")
    except Exception as e:
        logger.error(f"Error during example execution: {e}", exc_info=True)
