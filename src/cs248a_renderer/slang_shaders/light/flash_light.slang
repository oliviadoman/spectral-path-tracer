implementing "../light.slang";

public struct FlashLight
{
    public float3 color = float3(1.0, 1.0, 1.0);
    public float intensity = 1.0;

    // A flash light source that follows the camera ray direction.
    public LightSample sample(float3 rayOut)
    {
        float3 radiance = getRadiance();
        float lightDistance = 1.0; // dummy value, not used
        float pdf = 1.0;
        return LightSample(rayOut, radiance, pdf, lightDistance);
    }

    public float3 getRadiance()
    {
        return this.color * this.intensity;
    }
}
