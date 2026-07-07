implementing "../math.slang";

// A ray represented by an origin, a direction, and a t range along the ray.
public struct Ray
{
    public float3 origin;
    public float3 direction;
    // A point on the ray is given by origin + t * direction
    // tRange represents the valid interval of talong the ray: [tRange.x, tRange.y]
    public float2 tRange;
    // Wavelength of this ray in nanometers (380–700 nm visible spectrum).
    // Used for spectral rendering with wavelength-dependent refraction.
    public float wavelength;

    public __init(float3 origin, float3 direction, float2 tRange = float2(0.0, float.maxValue), float wavelength = 0.0)
    {
        this.origin = origin;
        this.direction = direction;
        this.tRange = tRange;
        this.wavelength = wavelength;
    }

    /**
     * Transform the ray by a 4x4 matrix.
     * @param matrix The transformation matrix.
     * @return The transformed ray.
     */
    public Ray transform(float4x4 matrix)
    {
        // TODO: Student implementation starts  here.
        // Transform ray origin as a point & direction as vector
        Ray transformRay = this;
        float4 o = mul(matrix, float4(this.origin, 1.0));
        float4 dir = mul(matrix, float4(this.direction, 0.0));

        // Normalize
        transformRay.origin = o.xyz;
        transformRay.direction = normalize(dir.xyz);

        transformRay.tRange = this.tRange;
        // Preserve wavelength through transforms
        transformRay.wavelength = this.wavelength;

        return transformRay;

        // TODO: Student implementation ends here.
    }
};

public struct RayHitResult
{
    // The parameter t at which the ray intersects the primitive.
    public float t;
    // The normal of the primitive at the intersection point.
    public float3 normal;
};

public interface IRayCastable
{
    public Optional<RayHitResult> hit(Ray ray);
}
