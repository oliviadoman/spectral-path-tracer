implementing "../brdf.slang";

import utils;

public struct RetroreflectiveBRDF
{
    // A Retroreflective BRDF reflects the incident ray into the 
    // view direction. This BRDF does not perform any scattering.

    public float3 albedo;

    public float3 evaluate()
    {
        return albedo;
    }

    public float3 sample(float3 rayOut)
    {
        // A RetroreflectiveLambertianBRDF always returns the ray along 
        // the reflected ray direction.
        // Same as RetroreflectiveLambertianBRDF.
        return rayOut;
    }

    public float pdf(float3 rayIn, float3 rayOut, float3 normal)
    {
        // Same as RetroreflectiveLambertianBRDF.
        // A RetroreflectiveBRDF always returns the ray along the 
        // reflected ray direction.
        // Therefore, the PDF is 1.0 if the incident ray direction is the same 
        //as the reflected ray direction.
        const float EPSILON = 1e-6;
        return all(abs(rayIn - rayOut) < EPSILON) ? 1.0 : 0.0;
    }
}