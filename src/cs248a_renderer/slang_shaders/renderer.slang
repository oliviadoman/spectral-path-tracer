module renderer;

import math;
import texture;
import material;
import model;
import primitive;
import light;
import utils;
import brdf;

__include "./renderer/mesh_renderer.slang";
__include "./renderer/volume_renderer.slang";

public struct RendererUniform
{
    // Camera parameters.
    public Camera camera;
    // Ambient color, used when no ray hits a primitive
    public float4 ambientColor;
    // Ray samples per pixel
    public uint numSamples;
    // Primitives.
    public StructuredBuffer<Triangle> triangleBuf;
    public uint triangleCount;
    public SharedTexture3DBuffer<float4> surfaceVolumeTexBuf;
    public StructuredBuffer<Volume> surfaceVolumeBuf;
    public uint surfaceVolumeCount;
    public SDFBuffer sdfBuf;
    // Volumetric data.
    public DiffVolume volume;
    // Acceleration structure.
    public bool useBVH;
    public BVH<Triangle> bvh;
    // Materials.
    public PhysicsBasedMaterialTextureBuf physicsBasedMaterialTextureBuf;
    public StructuredBuffer<PhysicsBasedMaterial> physicsBasedMaterialBuf;
    public uint materialCount;
    // Filtering
    public uint filteringMethod;
    // Lights
    public StructuredBuffer<PointLight> pointLightBuf;
    public uint pointLightCount;
    public StructuredBuffer<DirectionalLight> directionalLightBuf;
    public uint directionalLightCount;
    public StructuredBuffer<RectangularLight> rectangularLightBuf;
    public uint rectangularLightCount;
    // Number of samples per rectangular light
    public uint numRectangularLightSamples;
    // Use cosine weighted sampling for Lambertian BRDF
    public bool useCosineWeightedSampling;
    // Path trace depth
    public uint pathTraceDepth;
    // Enable fresnel effect for glass materials
    public bool enableFresnelEffect;
    // Seed for RNG
    public uint seed;
    // Debug flags.
    public bool renderDepth;
    public bool renderNormal;
    public bool visualizeBarycentricCoords;
    public bool visualizeTexUV;
    public bool visualizeLevelOfDetail;
    public bool visualizeAlbedo;
    public bool smoothShading;
}

/**
 * Sample the scene at the given uv coordinate.
 * @param uv The normalized uv coordinate from (0, 0) in the bottom-left to (1, 1) in the top-right.
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @return The color of the ray sample at the given uv coordinate.
 */
public float4 sample(float2 uv, RendererUniform uniforms, inout RNG rng)
{
    // Ray mesh intersection (wavelength is sampled inside meshSample).

    Optional<RayMeshSampleResult> rayMeshSampleRes = meshSample(uv, uniforms, rng);

    float4 primColor = uniforms.ambientColor;
    if (rayMeshSampleRes.hasValue)
    {
        primColor = rayMeshSampleRes.value.color;
    }

    if (uniforms.renderDepth)
    {
        // Map depth to [0, 1] range for visualization
        return float4(float3(rayMeshSampleRes.value.t), 1.0);
    }

    if (uniforms.renderNormal)
    {
        // Map normal from [-1, 1] to [0, 1] range for visualization
        return float4(rayMeshSampleRes.value.normal * 0.5 + 0.5, 1.0);
    }

    // Ray volume intersection.
    float tMax = rayMeshSampleRes.hasValue ? rayMeshSampleRes.value.t : float.maxValue;
    float4 volumeColor = volumeSample(uv, uniforms, tMax, primColor);

    return volumeColor;
}

/**
 * The entry point of the renderer.
 * @param tid The 2D coordinate of the current thread. Ranges from (0, 0) to (canvasSize.x - 1, canvasSize.y - 1).
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @return The color of the pixel at the given thread coordinate.
 */
public float4 render(uint2 tid, RendererUniform uniforms, float4 currentColor)
{
    // Basic version: no supersampling.
    // float2 uv = (float2(tid) + 0.5) / float2(uniforms.camera.canvasSize);
    // return sample(uv, uniforms);

    float4 outputColor = float4(0.0, 0.0, 0.0, 0.0);
    RNG rng = RNG(tid, (tid.y * uniforms.camera.canvasSize.x + tid.x) * 10000 + uniforms.seed);

    // Calculate screen space uv coordinate.
    float2 offset = rng.next_2d();
    float2 uv = (float2(tid) + offset) / float2(uniforms.camera.canvasSize);
    outputColor += sample(uv, uniforms, rng);

    return currentColor * (uniforms.numSamples - 1) / uniforms.numSamples + outputColor / uniforms.numSamples;
}

/**
 * Backward pass for volume sampling at a single uv.
 * @param uv The normalized uv coordinate from (0, 0) in the bottom-left to (1, 1) in the top-right.
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @param outGrad The output gradient w.r.t. the sampled color.
 */
public void sampleVolumeBwd(float2 uv, RendererUniform uniforms, float4 outGrad)
{
    volumeSampleBwd(uv, uniforms, outGrad);
}

/**
 * Backward pass for volume rendering at a pixel.
 * @param tid The 2D coordinate of the current thread. Ranges from (0, 0) to (canvasSize.x - 1, canvasSize.y - 1).
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @param outGrad The output gradient w.r.t. the rendered pixel color.
 */
public void renderVolumeBwd(uint2 tid, RendererUniform uniforms, float4 outGrad)
{
    // For simplicity, we're not implementing supersampling in the backward pass.
    float2 uv = (float2(tid) + 0.5) / float2(uniforms.camera.canvasSize);
    sampleVolumeBwd(uv, uniforms, outGrad);
}
