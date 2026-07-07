from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple
from pathlib import Path
import slangpy as spy
from pyglm import glm
import numpy as np
from PIL import Image


@dataclass
class PhysicsBasedMaterialTextureBuf:
    albedo: spy.NDBuffer


class FilteringMethod(Enum):
    NEAREST = 0
    BILINEAR = 1
    BILINEAR_DISCRETIZED_LEVEL = 2
    TRILINEAR = 3


class BRDFType(Enum):
    LAMBERTIAN = 0
    MIRROR = 1
    GLASS = 2
    RETROREFLECTIVE = 3
    RETROREFLECTIVE_LAMBERTIAN = 4

@dataclass
class MaterialField[T]:
    uniform_value: T | None = None
    use_texture: bool = False
    filtering_method: FilteringMethod = FilteringMethod.NEAREST
    textures: List[np.ndarray] = field(default_factory=list)

    def __init__(
        self,
        uniform_value: T | None = None,
        use_texture: bool = False,
        filtering_method: FilteringMethod = FilteringMethod.NEAREST,
        texture_map_path: str = None,
        textures: List[np.ndarray] = None,
    ):
        self.uniform_value = uniform_value
        self.use_texture = use_texture
        self.filtering_method = filtering_method
        self.MAX_MIP_LEVELS = 8
        self.textures = textures if textures is not None else []

        # If textures are provided directly (e.g., from deserialization), use them
        if textures is not None:
            self.textures = textures
            return

        # Otherwise, load from file if provided
        if texture_map_path is not None:
            self.load_texture_from_image(texture_map_path)
        elif use_texture:
            raise ValueError(
                "Texture map path or textures array is required for texture material"
            )

    def generate_mipmaps(self, base_texture: np.ndarray) -> None:
        """Generate mipmaps from a base texture image.

        :param base_texture: The base texture as numpy array (H, W, C)
        """
        # This is level 0 mipmap. It is the original texture. Populate this list
        #  with other mipmap levels, in increasing order of levels.
        textures = [base_texture]

        # TODO: Student implementation starts here.

        curr = textures[0]
        for level in range(1, self.MAX_MIP_LEVELS):
            h, w, c = curr.shape

            # Stop if 1x1 texture
            if h ==1 and w == 1:
                break

            # next level resolution
            newh = max(1, h // 2)
            neww = max(1, w // 2)

            h2 = newh * 2
            w2 = neww * 2
            crop = curr[:h2, :w2, :]

            # Average over non-overlappign 2x2 blocks
            reshaped = crop.reshape(newh, 2, neww, 2, c).mean(axis=(1, 3))
            textures.append(reshaped)
            curr = reshaped

        # TODO: Student implementation ends here.

        self.textures = textures

    def load_texture_from_image(self, image_path: str | Path) -> None:
        """Load a texture from an image file and generate mipmaps.

        :param image_path: Path to the image file (PNG, JPG, etc.)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load image
        pil_img = Image.open(image_path)
        # Only keep the rgb channels
        pil_img = pil_img.convert("RGB")
        # Convert to numpy array and normalize to [0, 1]
        texture_array = np.array(pil_img).astype(np.float32) / 255.0

        # Generate mipmaps
        self.generate_mipmaps(texture_array)

    def get_this(self, offset: int) -> Tuple[Dict, int]:
        mipmaps = []
        for i in range(self.MAX_MIP_LEVELS):
            if i >= len(self.textures):
                mipmaps.append(
                    {
                        "size": [0, 0],
                        "offset": offset,
                    }
                )
            else:
                texture = self.textures[i]
                mipmaps.append(
                    {
                        "size": [texture.shape[1], texture.shape[0]],
                        "offset": offset,
                    }
                )
                offset += texture.shape[0] * texture.shape[1]
        return {
            "uniformData": self.uniform_value,
            "useTexture": self.use_texture,
            "filteringMethod": self.filtering_method.value,
            "mipmap": mipmaps,
            "totalLevels": len(self.textures),
        }, offset


@dataclass
class PhysicsBasedMaterial:
    albedo: MaterialField[glm.vec3] = field(
        default_factory=lambda: MaterialField(glm.vec3(1.0, 0.0, 1.0))
    )
    smoothness: float = 0.0
    ior: float = 1.5  # Index of Refraction (default: glass ~1.5)
    brdf_type: BRDFType = BRDFType.RETROREFLECTIVE_LAMBERTIAN

    def get_this(self, offset: int) -> Tuple[Dict, int]:
        albedo_data, offset = self.albedo.get_this(offset)
        return {
            "albedo": albedo_data,
            "smoothness": self.smoothness,
            "brdfType": self.brdf_type.value,
            "ior": self.ior,
        }, offset


def create_material_buf(
    module: spy.Module, materials: List[PhysicsBasedMaterial]
) -> Tuple[spy.NDBuffer, PhysicsBasedMaterialTextureBuf]:
    device = module.device
    material_buf = spy.NDBuffer(
        device=device,
        dtype=module.PhysicsBasedMaterial.as_struct(),
        shape=(max(len(materials), 1),),
    )
    albedo_textures = []
    cursor = material_buf.cursor()
    offset = 0
    for idx, material in enumerate(materials):
        material_data, offset = material.get_this(offset)
        for level_texture in material.albedo.textures:
            albedo_textures.append(level_texture.astype(np.float32).reshape(-1, 3))
        cursor[idx].write(material_data)
    cursor.apply()
    # Concatenate all albedo textures into a single buffer.
    np_alebdo_texture = (
        np.concatenate(albedo_textures, axis=0)
        if albedo_textures
        else np.zeros((1, 3), dtype=np.float32)
    )
    albedo_tex_buf = spy.NDBuffer(
        device=device,
        dtype=module.float3,
        shape=(np_alebdo_texture.shape[0],),
    )
    albedo_tex_buf.copy_from_numpy(np_alebdo_texture)
    physics_based_material_texture_buf = PhysicsBasedMaterialTextureBuf(
        albedo=albedo_tex_buf
    )
    return material_buf, physics_based_material_texture_buf
