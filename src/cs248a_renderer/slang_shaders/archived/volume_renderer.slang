import math;
import model;
import primitives;

public struct RayMarcherConfig
{
    uint maxSteps;
    float stepSize;
    float densityScale;
};

struct UniformsForward
{
    // Unlearnable parameters.
    uint2 canvasSize;
    float4x4 invViewMatrix;
    float focalLength;
    float4 ambientColor;
    RayMarcherConfig rayMarcherConfig;
    // Learnable parameters.
    Volume volume;
    // Output
    RWTexture2D<float4> outputTexture;
};

struct UniformsBackward
{
    // Unlearnable parameters.
    uint2 canvasSize;
    float4x4 invViewMatrix;
    float focalLength;
    float4 ambientColor;
    RayMarcherConfig rayMarcherConfig;
    // Learnable parameters.
    Volume volume;
    // Output
    RWTexture2D<float4> dOutputTexture;
};

[Differentiable]
float4 accumulateColor<let N : int>(
    no_diff float2 tBounds,
    no_diff float3 rayOrigin,
    no_diff float3 rayDirection,
    no_diff uint maxSteps,
    no_diff float stepSize,
    no_diff float densityScale,
    no_diff float4 ambientColor,
    no_diff float3 minBound,
    no_diff float3 maxBound,
    DiffTexture3D<float, 4> data,
    no_diff bool useAlbedoVolume,
    no_diff float3 albedo)
{
    float attenuation = 1.0;
    float4 color = float4(0.0, 0.0, 0.0, 0.0);
    float t = max(tBounds.x, 0.0);
    [MaxIters(N)]
    for (uint i = 0; i < maxSteps; ++i)
    {
        if (t > tBounds.y || attenuation < 0.05)
        {
            break;
        }

        float3 pos = rayOrigin + t * rayDirection;
        float3 uv = (pos - minBound) / (maxBound - minBound);
        float4 sampleData = clamp(sampleTrilinear(data, uv), float4(0.0), float4(1.0));
        float sampleDensity = sampleData.a;
        float alpha = sampleDensity * stepSize * densityScale;
        // TODO: Replace the black radiance with volume albedo.
        float3 sampledAlbedo = albedo;
        if (useAlbedoVolume)
        {
            sampledAlbedo = sampleData.rgb;
        }
        color.rgb += attenuation * alpha * sampledAlbedo;
        color.a += attenuation * alpha;
        attenuation *= (1.0 - alpha);
        t += stepSize;
    }
    // Composite with ambient color if not fully opaque.
    color.rgb += attenuation * ambientColor.rgb;
    color.a += attenuation * ambientColor.a;
    return color;
}

// Forward ray marching function.
public float4 marchRay<let N : int>(RayMarcherConfig config, Ray ray, Volume volume, float4 ambientColor)
{
    // Intersect ray with volume bounding box.
    BoundingBox box = BoundingBox(volume.minBound, volume.maxBound);
    float2 tBounds = box.hit(ray);
    if (tBounds.y <= tBounds.x)
    {
        // No intersection, write background color.
        return ambientColor;
    }
    // Ray march through the volume.
    return accumulateColor<N>(
        tBounds,
        ray.origin,
        ray.direction,
        config.maxSteps,
        config.stepSize,
        config.densityScale,
        ambientColor,
        volume.minBound,
        volume.maxBound,
        volume.data,
        volume.useAlbedoVolume,
        volume.albedo);
}

// Backward ray marching function that produces the gradients w.r.t. volume density.
public void marchRayBackward<let N : int>(RayMarcherConfig config, Ray ray, Volume volume, float4 ambientColor, float4 dOutput)
{
    // Intersect ray with volume bounding box.
    BoundingBox box = BoundingBox(volume.minBound, volume.maxBound);
    float2 tBounds = box.hit(ray);
    if (tBounds.y <= tBounds.x)
    {
        // No intersection, no gradients.
        return;
    }
    // Setup density differential pair.
    DifferentialPtrPair<DiffTexture3D<float, 4>> dataPair = { volume.data, volume.dData };

    bwd_diff(accumulateColor<N>)(
        tBounds,
        ray.origin,
        ray.direction,
        config.maxSteps,
        config.stepSize,
        config.densityScale,
        ambientColor,
        volume.minBound,
        volume.maxBound,
        dataPair,
        volume.useAlbedoVolume,
        volume.albedo,
        dOutput);
}

[shader("compute")]
[numthreads(16, 16, 1)]
void renderForward(uint2 tid: SV_DispatchThreadID, uniform UniformsForward uniforms)
{
    // Calculate screen space uv coordinate.
    float2 uv = (float2(tid) + 0.5) / float2(uniforms.canvasSize);
    // Generate ray in view space.
    float3 rayOrigin = float3(0.0, 0.0, 0.0);
    float3 rayDirection = normalize(
        float3((uv - 0.5) * float2(uniforms.canvasSize), -uniforms.focalLength));
    Ray ray = Ray(rayOrigin, rayDirection);
    // Transform ray to world space.
    ray = ray.transform(uniforms.invViewMatrix);
    // Transform ray to volume local space.
    ray = ray.transform(uniforms.volume.invModelMatrix);
    // March the ray through the volume.
    uniforms.outputTexture[tid] = marchRay<196>(uniforms.rayMarcherConfig, ray, uniforms.volume, uniforms.ambientColor);
}

[shader("compute")]
[numthreads(16, 16, 1)]
void renderBackward(uint2 tid: SV_DispatchThreadID, uniform UniformsBackward uniforms)
{
    // Calculate screen space uv coordinate.
    float2 uv = (float2(tid) + 0.5) / float2(uniforms.canvasSize);
    // Generate ray in view space.
    float3 rayOrigin = float3(0.0, 0.0, 0.0);
    float3 rayDirection = normalize(
        float3((uv - 0.5) * float2(uniforms.canvasSize), -uniforms.focalLength));
    Ray ray = Ray(rayOrigin, rayDirection);
    // Transform ray to world space.
    ray = ray.transform(uniforms.invViewMatrix);
    // Transform ray to volume local space.
    ray = ray.transform(uniforms.volume.invModelMatrix);
    // March the ray through the volume.
    marchRayBackward<196>(uniforms.rayMarcherConfig, ray, uniforms.volume, uniforms.ambientColor, uniforms.dOutputTexture[tid]);
}
