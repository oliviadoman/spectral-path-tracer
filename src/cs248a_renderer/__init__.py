from typing import List
from pathlib import Path

import slangpy as spy
import slangpy_nn as nn

SHADER_PATH = Path(__file__).parent / "slang_shaders"


def setup_device(notebook_shader_paths: List[Path]) -> spy.Device:
    # CS 248A Shaders
    shader_paths = [
        SHADER_PATH.absolute(),
    ]
    # SlangNN Shaders
    shader_paths.extend(nn.slang_include_paths())
    # Extra Notebook Shaders
    shader_paths.extend([p.absolute() for p in notebook_shader_paths])
    device = spy.create_device(include_paths=shader_paths)
    return device


class RendererModules:
    math_module: spy.Module
    texture_module: spy.Module
    material_module: spy.Module
    primitive_module: spy.Module
    light_module: spy.Module
    model_module: spy.Module
    renderer_module: spy.Module

    def __init__(self, device: spy.Device):
        self.math_module = spy.Module.load_from_file(
            device=device,
            path="math.slang",
        )
        self.texture_module = spy.Module.load_from_file(
            device=device,
            path="texture.slang",
            link=[self.math_module],
        )
        self.material_module = spy.Module.load_from_file(
            device=device,
            path="material.slang",
            link=[self.math_module],
        )
        self.primitive_module = spy.Module.load_from_file(
            device=device,
            path="primitive.slang",
            link=[self.math_module, self.texture_module],
        )
        self.light_module = spy.Module.load_from_file(
            device=device,
            path="light.slang",
        )
        self.model_module = spy.Module.load_from_file(
            device=device,
            path="model.slang",
            link=[self.math_module],
        )
        self.utils_module = spy.Module.load_from_file(
            device=device,
            path="utils.slang",
        )
        self.brdf_module = spy.Module.load_from_file(
            device=device,
            path="brdf.slang",
        )
        self.renderer_module = spy.Module.load_from_file(
            device=device,
            path="renderer.slang",
            link=[
                self.math_module,
                self.texture_module,
                self.material_module,
                self.primitive_module,
                self.model_module,
                self.utils_module,
                self.light_module,
                self.brdf_module,
            ],
        )
