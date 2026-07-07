from dataclasses import dataclass, field
from pyglm import glm
import slangpy as spy
from typing import List, Dict
import numpy as np

from cs248a_renderer.model.scene_object import SceneObject


@dataclass
class PointLight(SceneObject):
    """A point light source."""

    position: glm.vec3 = glm.vec3(0.0, 0.0, 0.0)
    color: glm.vec3 = glm.vec3(0.0, 0.0, 0.0)
    intensity: float = 0.0

    def get_this(self) -> Dict:
        pos = self.get_transform_matrix() @ glm.vec4(self.position, 1.0)
        position = glm.vec3(pos.x, pos.y, pos.z)
        return {
            "position": position.to_list(),
            "color": self.color.to_list(),
            "intensity": self.intensity,
        }


@dataclass
class DirectionalLight(SceneObject):
    """A directional light source."""

    direction: glm.vec3 = glm.vec3(0.0, 0.0, -1.0)
    color: glm.vec3 = glm.vec3(0.0, 0.0, 0.0)
    intensity: float = 0.0

    def get_this(self) -> Dict:
        dir = self.get_transform_matrix() @ glm.vec4(self.direction, 0.0)
        direction = glm.vec3(dir.x, dir.y, dir.z)
        return {
            "direction": self.direction.to_list(),
            "color": self.color.to_list(),
            "intensity": self.intensity,
        }


@dataclass
class RectangularLight(SceneObject):
    """A rectangular light source."""

    vertices: List[glm.vec3] = field(
        default_factory=lambda: [
            glm.vec3(0.0, 0.0, 0.0),
            glm.vec3(0.0, 0.0, 0.0),
            glm.vec3(0.0, 0.0, 0.0),
            glm.vec3(0.0, 0.0, 0.0),
        ]
    )
    color: glm.vec3 = glm.vec3(0.0, 0.0, 0.0)
    intensity: float = 0.0
    doubleSided: bool = False

    def __post_init__(self):
        self.update_param(self.get_vertices())

    def update_param(self, vertices: List[glm.vec3]):
        self.bottomLeftVertex = vertices[0]
        self.bottomEdge = vertices[1] - vertices[0]
        self.leftEdge = vertices[3] - vertices[0]
        cross_product = glm.cross(self.bottomEdge, self.leftEdge)
        self.area = glm.length(cross_product)
        self.normal = glm.normalize(cross_product)

    def get_vertices(self) -> List[glm.vec3]:
        trans_mat = self.get_transform_matrix()
        return [glm.vec3(trans_mat @ glm.vec4(vertex, 1.0)) for vertex in self.vertices]

    def get_this(self) -> Dict:
        self.update_param(
            self.get_vertices()
        )  # Ensure that the derived attributes are updated
        return {
            "bottomLeftVertex": self.bottomLeftVertex.to_list(),
            "bottomEdge": self.bottomEdge.to_list(),
            "leftEdge": self.leftEdge.to_list(),
            "normal": self.normal.to_list(),
            "area": self.area,
            "color": self.color.to_list(),
            "intensity": self.intensity,
            "doubleSided": self.doubleSided,
        }


def create_point_light_buf(
    module: spy.Module, point_lights: List[PointLight]
) -> spy.NDBuffer:
    device = module.device
    buffer = spy.NDBuffer(
        device=device,
        dtype=module.PointLight.as_struct(),
        shape=(max(len(point_lights), 1),),
    )
    cursor = buffer.cursor()
    for idx, light in enumerate(point_lights):
        cursor[idx].write(light.get_this())
    cursor.apply()
    return buffer


def create_directional_light_buf(
    module: spy.Module, directional_lights: List[DirectionalLight]
) -> spy.NDBuffer:
    device = module.device
    buffer = spy.NDBuffer(
        device=device,
        dtype=module.DirectionalLight.as_struct(),
        shape=(max(len(directional_lights), 1),),
    )
    cursor = buffer.cursor()
    for idx, light in enumerate(directional_lights):
        cursor[idx].write(light.get_this())
    cursor.apply()
    return buffer


def create_rectangular_light_buf(
    module: spy.Module, rectangular_lights: List[RectangularLight]
) -> spy.NDBuffer:
    device = module.device
    buffer = spy.NDBuffer(
        device=device,
        dtype=module.RectangularLight.as_struct(),
        shape=(max(len(rectangular_lights), 1),),
    )
    cursor = buffer.cursor()
    for idx, light in enumerate(rectangular_lights):
        cursor[idx].write(light.get_this())
    cursor.apply()
    return buffer
