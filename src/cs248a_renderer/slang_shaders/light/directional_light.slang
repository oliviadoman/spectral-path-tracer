implementing "../light.slang";

public struct DirectionalLight
{
    public float3 direction;
    public float3 color;
    public float intensity;

    public LightSample sample()
    {
        float3 lightDirection = -this.direction;
        float3 radiance = getRadiance();
        float lightDistance = float.maxValue;
        float pdf = 1.0;
        return LightSample(lightDirection, radiance, pdf, lightDistance);
    }

    public float3 getRadiance()
    {
        return this.color * this.intensity;
    }
}
