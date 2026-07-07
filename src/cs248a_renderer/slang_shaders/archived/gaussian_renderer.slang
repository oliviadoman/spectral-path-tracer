import model;
import math;

public struct UniformsForward
{
    // Unlearnable parameters.
    public uint2 canvasSize;
    public float4x4 invModelMatrix;
    public float4x4 invViewMatrix;
    public float focalLength;
    public float4 ambientColor;
};

const static float EPS = 1e-5;

float4 accumulateColor<let N : int>(
    no_diff float2 tBounds,
    no_diff Ray ray,
    no_diff uint maxSteps,
    no_diff float densityScale,
    no_diff float4 ambientColor,
    StructuredBuffer<Gaussian> gaussians,
    uint numGaussians)
{
    float attenuation = 1.0;
    float4 color = float4(0.0, 0.0, 0.0, 0.0);
    float t = max(tBounds.x, 0.0);
    [MaxIters(N)]
    for (uint i = 0; i < maxSteps; ++i)
    {
        // Find the closest Gaussian hit by the ray.
        float closestT = float.maxValue;
        Optional<Gaussian> closestGaussian = Optional<Gaussian>();
        for (uint j = 0; j < numGaussians; ++j)
        {
            Gaussian gaussian = gaussians[j];
            float2 hit = gaussian.boundingBox(2.0).hit(ray);
            if (hit.y > hit.x)
            {
                float tau = gaussian.maxResponse(ray);
                if (tau < closestT && tau >= t)
                {
                    closestT = tau;
                    closestGaussian = Optional<Gaussian>(gaussian);
                }
            }
        }
        if (closestT == float.maxValue || attenuation < 0.05)
        {
            break;
        }
        // Sample the closest Gaussian.
        Gaussian gaussian = closestGaussian.value;
        float3 pos = ray.origin + closestT * ray.direction;
        float4 sampleData = gaussian.eval(pos);
        float sampleDensity = sampleData.a;
        float alpha = sampleDensity * densityScale;
        // TODO: Replace the black radiance with volume albedo.
        float3 sampledAlbedo = sampleData.rgb;
        color.rgb += attenuation * alpha * sampledAlbedo;
        color.a += attenuation * alpha;
        attenuation *= (1.0 - alpha);
        t = closestT + EPS;
    }
    // Composite with ambient color if not fully opaque.
    color.rgb += attenuation * ambientColor.rgb;
    color.a += attenuation * ambientColor.a;
    return color;
}

public float4 renderForward(uint2 tid, UniformsForward uniforms, StructuredBuffer<Gaussian> gaussians, uint numGaussians)
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
    return accumulateColor<64>(
        float2(0.0, float.maxValue),
        ray,
        64,
        1.0,
        uniforms.ambientColor,
        gaussians,
        numGaussians);
}
