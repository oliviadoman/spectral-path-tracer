import model;
import math;
__exported import NeuralNetworks;

public struct NeRFAABB
{
    public float3 minBound;
    public float3 maxBound;
};

public struct RayMarcherConfig
{
    public uint maxSteps;
    public float stepSize;
    public float densityScale;
};

public struct UniformsForward
{
    // Unlearnable parameters.
    public uint2 canvasSize;
    public float4x4 invModelMatrix;
    public float4x4 invViewMatrix;
    public float focalLength;
    public float4 ambientColor;
    public RayMarcherConfig rayMarcherConfig;
    // Learnable parameters.
    public NeRFAABB nerfAABB;
};

public struct UniformsBackward
{
    // Unlearnable parameters.
    public uint2 canvasSize;
    public float4x4 invModelMatrix;
    public float4x4 invViewMatrix;
    public float focalLength;
    public float4 ambientColor;
    public RayMarcherConfig rayMarcherConfig;
    // Learnable parameters.
    public NeRFAABB nerfAABB;
    // Output
    public RWTexture2D<float4> dOutputTexture;
};

[BackwardDifferentiable]
float4 accumulateColor<let N : int, NeRFMLP : INeRFMLP>(
    no_diff float2 tBounds,
    no_diff float3 rayOrigin,
    no_diff float3 rayDirection,
    no_diff uint maxSteps,
    no_diff float stepSize,
    no_diff float densityScale,
    no_diff float4 ambientColor,
    no_diff float3 minBound,
    no_diff float3 maxBound,
    NeRFMLP mlp)
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
        // Positional encoding.
        float[45] pe;
        pe[0] = uv.x;
        pe[1] = uv.y;
        pe[2] = uv.z;
        int idx = 3;
        for (int l = 0; l < 7; ++l)
        {
            float freq = pow(2.0, float(l)) * 3.14;
            pe[idx++] = sin(freq * uv.x);
            pe[idx++] = cos(freq * uv.x);
            pe[idx++] = sin(freq * uv.y);
            pe[idx++] = cos(freq * uv.y);
            pe[idx++] = sin(freq * uv.z);
            pe[idx++] = cos(freq * uv.z);
        }
        float4 sampleData = sigmoid(mlp.forward(pe));
        // float4 sampleData = float4(uv.x, uv.y, uv.z, 1.0); // Placeholder for MLP output.
        // Accumulate color and opacity.
        float sampleDensity = sampleData.a;
        float alpha = sampleDensity * stepSize * densityScale;
        float3 sampledAlbedo = sampleData.rgb;
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
public float4 marchRay<let N : int, NeRFMLP : INeRFMLP>(RayMarcherConfig config, Ray ray, NeRFAABB nerfAABB, NeRFMLP mlp, float4 ambientColor)
{
    // Intersect ray with volume bounding box.
    BoundingBox box = BoundingBox(nerfAABB.minBound, nerfAABB.maxBound);
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
        nerfAABB.minBound,
        nerfAABB.maxBound,
        mlp);
}

// Backward ray marching function that produces the gradients w.r.t. volume density.
public void marchRayBackward<let N : int, NeRFMLP : INeRFMLP>(RayMarcherConfig config, Ray ray, NeRFAABB nerfAABB, NeRFMLP mlp, float4 ambientColor, float4 dOutput)
{
    // Intersect ray with volume bounding box.
    BoundingBox box = BoundingBox(nerfAABB.minBound, nerfAABB.maxBound);
    float2 tBounds = box.hit(ray);
    if (tBounds.y <= tBounds.x)
    {
        // No intersection, no gradients.
        return;
    }

    bwd_diff(accumulateColor<N, NeRFMLP>)(
        tBounds,
        ray.origin,
        ray.direction,
        config.maxSteps,
        config.stepSize,
        config.densityScale,
        ambientColor,
        nerfAABB.minBound,
        nerfAABB.maxBound,
        mlp,
        dOutput);
}

public float4 renderForward<NeRFMLP : INeRFMLP>(uint2 tid, UniformsForward uniforms, NeRFMLP mlp)
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
    ray = ray.transform(uniforms.invModelMatrix);
    // March the ray through the volume.
    return marchRay<64>(uniforms.rayMarcherConfig, ray, uniforms.nerfAABB, mlp, uniforms.ambientColor);
}

public void renderBackward<NeRFMLP : INeRFMLP>(uint2 tid, UniformsBackward uniforms, NeRFMLP mlp)
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
    ray = ray.transform(uniforms.invModelMatrix);
    // March the ray through the volume.
    marchRayBackward<64>(uniforms.rayMarcherConfig, ray, uniforms.nerfAABB, mlp, uniforms.ambientColor, uniforms.dOutputTexture[tid]);
}
