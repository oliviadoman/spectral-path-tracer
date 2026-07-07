implementing "../brdf.slang";

// Cauchy dispersion equation: n(lambda) = A + B / lambda^2
// Returns wavelength-dependent index of refraction.
// wavelength_nm: wavelength in nanometers
// If wavelength_nm <= 0, falls back to the material's fixed IOR.
public float cauchy_ior(float wavelength_nm, float base_ior)
{
    if (wavelength_nm <= 0.0)
        return base_ior;
    // Flint glass constants (high dispersion)
    static const float CAUCHY_A = 1.7;
    static const float CAUCHY_B = 10000.0; // in nm^2 (high dispersion flint glass)
    return CAUCHY_A + CAUCHY_B / (wavelength_nm * wavelength_nm);
}

public struct GlassBRDF
{
    public float3 albedo;
    public float ior;

    public float3 evaluate()
    {
        return albedo;
    }

    // Compute refraction/reflection direction using wavelength-dependent IOR.
    // wavelength: ray wavelength in nm (pass 0 to use the fixed material IOR).
    public float3 sample(float3 rayOut, float3 normal, float wavelength = 0.0)
    {

        float3 sampleDirection = rayOut;
        float3x3 worldToLocalMatrix = getWorldToLocalMatrix(normal, rayOut);
        float3x3 localToWorldMatrix = transposeMatrix(worldToLocalMatrix);

        // Use wavelength-dependent IOR when spectral rendering is active.
        float effectiveIOR = cauchy_ior(wavelength, this.ior);

        // TODO: Student implementation starts here.

        float cosI = dot(rayOut, normal);
        float3 n = normal;
        float eta;
        if (cosI > 0.0)
        {
            eta = 1.0 / effectiveIOR;
        }
        else
        {
            eta = effectiveIOR;
            n = -normal;
            cosI = -cosI;
        }

        float sin2T = eta * eta * (1.0 - cosI * cosI);

        if (sin2T >= 1.0)
        {
            sampleDirection = 2.0 * dot(rayOut, normal) * normal - rayOut;
        }
        else
        {
            float cosT = sqrt(1.0 - sin2T);
            sampleDirection = -eta * rayOut + (eta * cosI - cosT) * n;
        }

        // TODO: Student implementation ends here.

        return sampleDirection;
    }

    public float pdf(float3 rayIn, float3 rayOut, float3 normal)
    {
        // For dielectric materials, the PDF is 1.0 for the single direction
        // (either refracted or reflected due to total internal reflection)
        return 1.0;
    }
}
