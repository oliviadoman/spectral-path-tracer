implementing "../brdf.slang";

public struct MirrorBRDF
{
    public float3 albedo;

    public float3 evaluate()
    {
        return albedo;
    }

    public float3 sample(float3 rayOut, float3 normal)
    {
        float3 sampleDirection = rayOut;
        float3x3 worldToLocalMatrix = getWorldToLocalMatrix(normal, rayOut);
        float3x3 localToWorldMatrix = transposeMatrix(worldToLocalMatrix);

        // HINT: First convert the reflected ray direction to the local space,
        // then compute the incident ray direction in the local space,
        // and finally convert it to the world space.

        // TODO: Student implementation starts here.

        sampleDirection = 2.0 * dot(rayOut, normal) * normal - rayOut;

        // TODO: Student implementation ends here.

        return sampleDirection;
    }

    public float pdf(float3 rayIn, float3 rayOut, float3 normal)
    {
        const float EPSILON = 1e-6;
        float pdf = all(abs(rayIn - rayOut) < EPSILON) ? 1.0 : 0.0;
        float3x3 worldToLocalMatrix = getWorldToLocalMatrix(normal, rayOut);

        // TODO: Student implementation starts here.

        pdf = 1.0;

        // TODO: Student implementation ends here.

        return pdf;
    }
}
