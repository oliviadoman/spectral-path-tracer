implementing "../light.slang";

public struct PointLight
{
    public float3 position;
    public float3 color;
    public float intensity;

    public LightSample sample(float3 hitPoint)
    {
        float3 toLight = this.position - hitPoint;
        float3 lightDirection = normalize(toLight);
        float lightDistance = length(toLight);
        float3 radiance = getRadiance(lightDistance);
        float pdf = 1.0;
        return LightSample(lightDirection, radiance, pdf, lightDistance);
    }

    public float3 getRadiance(float lightDistance)
    {
        return this.color * this.intensity;
    }
}

