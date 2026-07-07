module light;

__include "./light/flash_light.slang";
__include "./light/directional_light.slang";
__include "./light/point_light.slang";
__include "./light/rect_light.slang";

public struct LightSample
{
    public float3 lightDirection;
    public float3 radiance;
    public float pdf;
    public float lightDistance;
}
