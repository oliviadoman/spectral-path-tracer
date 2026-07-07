implementing "../renderer.slang";

import brdf;
import light;

public struct SampleBRDFResult
{
    public float3 fr;
    public float3 sampledDirection;
    public float sampledPdf;
}

public float3 getSampleIrradiance(LightSample lightSample, float3 normal, bool isLambertian, float fallOffFactor = 1.0)
{
    const float EPSILON = 1e-2;
    float3 lightDirection = lightSample.lightDirection;
    if (isLambertian)
    {
        float cosTheta = max(dot(normalize(normal), normalize(lightDirection)), 0.0);
        return lightSample.radiance * cosTheta / (fallOffFactor + EPSILON);
    }
    else
    {
        return lightSample.radiance / (fallOffFactor + EPSILON);
    }
}

public Ray getShadowRay(LightSample lightSample, float3 hitPoint)
{
    const float EPSILON = 1e-2;
    Ray shadowRay = Ray(float3(0.0), float3(0.0), float2(EPSILON, lightSample.lightDistance - EPSILON), 0.0);

    // TODO: Student implementation starts here.

    shadowRay.origin = hitPoint;
    shadowRay.direction = normalize(lightSample.lightDirection);

    // TODO: Student implementation ends here.

    return shadowRay;
}

public bool isLightOccluded(LightSample lightSample, float3 hitPoint, RendererUniform uniforms)
{
    bool occluded = false;

    // TODO: Student implementation starts here.

    Ray shadowRay = getShadowRay(lightSample, hitPoint);

    Optional<RayMeshIntersectionResult> meshHit = rayMeshIntersection(shadowRay, uniforms, true);
    Optional<RectangularLight.LightHitResult> lightHit = rayRectangularLightIntersection(shadowRay, uniforms);

    if (meshHit.hasValue || lightHit.hasValue)
    {
        occluded = true;
    }

    // TODO: Student implementation ends here.

    return occluded;
}

public float3 evaluateFlashLightContribution(float3 hitPoint, float3 fr, float3 normal, RendererUniform uniforms, float3 rayOut, bool lambertianScattering = false)
{
    float3 outgoingRadiance = float3(0.0);
    float fallOffFactor = 1.0;  // Never falls off with distance

    // We have only one flash light source, so we can simply sample it.
    LightSample lightSample = FlashLight().sample(rayOut);

    // Unlike other light sources, a flash light is never occluded because it
    // always points at the closest hit from camera, and returning back to it.
    // Therefore, ideally we would not need to check for occlusion.
    // Yet, we do it anyway to be consistent with the function bodies of other light sources.
    bool occluded = isLightOccluded(lightSample, hitPoint, uniforms);
    if (occluded)
    {
        return outgoingRadiance;
    }

    float3 sampleIrradiance = getSampleIrradiance(lightSample, normal, lambertianScattering, fallOffFactor);
    // PDF is used for Monte-Carlo integration. But it is only needed for light 
    // sources that have an area, for eg. rectangular light. Therefore, we are 
    // using `lightSample.pdf=1` here.
    float3 irradiance = sampleIrradiance / lightSample.pdf;
    outgoingRadiance = fr * irradiance;

    return outgoingRadiance;
}

public float3 evaluatePointLightContribution(StructuredBuffer<PointLight> pointLightBuf, uint pointLightCount, float3 hitPoint, float3 fr, float3 normal, RendererUniform uniforms, bool lambertianScattering = false)
{
    float3 outgoingRadiance = float3(0.0);
    float fallOffFactor = 1.0;  // Point light falls off with distance. Calculate it below.
    for (int i = 0; i < pointLightCount; i++)
    {
        LightSample lightSample = pointLightBuf[i].sample(hitPoint);
        bool occluded = isLightOccluded(lightSample, hitPoint, uniforms);
        if (occluded)
        {
            continue;
        }

        // TODO: Student implementation starts here.

        fallOffFactor = lightSample.lightDistance * lightSample.lightDistance;

        // TODO: Student implementation ends here.

        float3 sampleIrradiance = getSampleIrradiance(lightSample, normal, lambertianScattering, fallOffFactor);
        // PDF is used for Monte-Carlo integration. But it is only needed for light
        // sources that have an area, for eg. rectangular light. Therefore, we are
        // using `lightSample.pdf=1` here.
        float3 irradiance = sampleIrradiance / lightSample.pdf;
        outgoingRadiance += fr * irradiance;
    }
    return outgoingRadiance;
}

public float3 evaluateDirectionalLightContribution(StructuredBuffer<DirectionalLight> directionalLightBuf, uint directionalLightCount, float3 hitPoint, float3 fr, float3 normal, RendererUniform uniforms, bool lambertianScattering = false)
{
    float3 outgoingRadiance = float3(0.0);
    float fallOffFactor = 1.0; // Never falls off with distance
    for (int i = 0; i < directionalLightCount; i++)
    {
        LightSample lightSample = directionalLightBuf[i].sample();
        bool occluded = isLightOccluded(lightSample, hitPoint, uniforms);
        if (occluded)
        {
            continue;
        }
        float3 sampleIrradiance = getSampleIrradiance(lightSample, normal, lambertianScattering, fallOffFactor);
        // PDF is used for Monte-Carlo integration. But it is only needed for light
        // sources that have an area, for eg. rectangular light. Therefore, we are
        // using `lightSample.pdf=1` here.
        float3 irradiance = sampleIrradiance / lightSample.pdf;
        outgoingRadiance += fr * irradiance;
    }
    return outgoingRadiance;
}

public float3 evaluateRectangularLightContribution(StructuredBuffer<RectangularLight> rectangularLightBuf, uint rectangularLightCount, float3 hitPoint, float3 fr, float3 normal, RendererUniform uniforms, inout RNG rng, bool lambertianScattering = false)
{
    float3 outgoingRadiance = float3(0.0);
    float fallOffFactor = 1.0;  // Never falls off with distance
    for (int i = 0; i < rectangularLightCount; i++)
    {
        // Monte Carlo Estimator of the irradiance from the rectangular light source.
        // It is integral of the BRDF over the rectangular light source.
        float3 accumulatedIrradiance = float3(0.0);
        for (int j = 0; j < uniforms.numRectangularLightSamples; j++)
        {
            float2 randomEpsilon = rng.next_2d();
            LightSample lightSample = rectangularLightBuf[i].sample(hitPoint, randomEpsilon);
            bool occluded = isLightOccluded(lightSample, hitPoint, uniforms);
            if (occluded)
            {
                continue;
            }
            float3 sampleIrradiance = getSampleIrradiance(lightSample, normal, lambertianScattering, fallOffFactor);
            accumulatedIrradiance += sampleIrradiance / lightSample.pdf;
        }
        float3 irradiance = accumulatedIrradiance / uniforms.numRectangularLightSamples;
        // Monte-Carlo Integration over.

        outgoingRadiance += fr * irradiance;
    }
    return outgoingRadiance;
}

public float3 getDirectIllumination(PhysicsBasedParameters parameters, RendererUniform uniforms, float3 rayOut, float3 normal, float3 hitPoint, inout RNG rng)
{
    float3 outgoingRadiance = float3(0.0);
    float3 fr = float3(0.0);
    bool lambertianScattering = false; // True only for Lambertian BRDF and Retroreflective Lambertian BRDF
    float3 retroreflectiveLambertianFr = float3(0.0);

    if (parameters.brdfType == 0)
    {
        LambertianBRDF brdf = LambertianBRDF(parameters.albedo, uniforms.useCosineWeightedSampling);
        fr = brdf.evaluate();
        lambertianScattering = true;
    }
    else if (parameters.brdfType == 1)
    {
        MirrorBRDF brdf = MirrorBRDF(parameters.albedo);
        // Mirror BRDF has nearly 0 chance of hitting a light source, unless the
        // light source lies along the path of ray direction bounced off it.
        // Remember that mirror bounces the ray in only one unique direction.
        // Check brdf/mirror.slang for more details.
        // Hence, we can simply return 0 for the BRDF value.
        fr = float3(0.0);
    }
    else if (parameters.brdfType == 2)
    {
        GlassBRDF brdf = GlassBRDF(parameters.albedo, parameters.ior);
        // Glass BRDF passes light through with minimal direct illumination contribution
        fr = float3(0.0);
    }
    else if (parameters.brdfType == 3)
    {
        RetroreflectiveBRDF brdf = RetroreflectiveBRDF(parameters.albedo);
        retroreflectiveLambertianFr = brdf.evaluate(); // Used only with Flash light
        fr = float3(0.0);
    }
    else if (parameters.brdfType == 4)
    {
        RetroreflectiveLambertianBRDF brdf = RetroreflectiveLambertianBRDF(parameters.albedo);
        retroreflectiveLambertianFr = brdf.evaluate(); // Used only with Flash light
        fr = float3(0.0);
        lambertianScattering = true;
    }

    // If there are no light sources, we simply use the flash light source.
    if (uniforms.pointLightCount == 0 && uniforms.directionalLightCount == 0 && uniforms.rectangularLightCount == 0)
    {
        // For the combination of Retroreflective (Lambertian or not) BRDF and Flash light,
        if (parameters.brdfType == 3 || parameters.brdfType == 4)
        {
            fr = retroreflectiveLambertianFr;
        }
        float3 flashLightContribution = evaluateFlashLightContribution(hitPoint, fr, normal, uniforms, rayOut, lambertianScattering);
        outgoingRadiance = flashLightContribution;
    }
    else
    {
        float3 pointLightContribution = evaluatePointLightContribution(uniforms.pointLightBuf, uniforms.pointLightCount, hitPoint, fr, normal, uniforms, lambertianScattering);
        float3 directionalLightContribution = evaluateDirectionalLightContribution(uniforms.directionalLightBuf, uniforms.directionalLightCount, hitPoint, fr, normal, uniforms, lambertianScattering);
        float3 rectangularLightContribution = evaluateRectangularLightContribution(uniforms.rectangularLightBuf, uniforms.rectangularLightCount, hitPoint, fr, normal, uniforms, rng, lambertianScattering);
        outgoingRadiance = pointLightContribution + directionalLightContribution + rectangularLightContribution;
    }

    return outgoingRadiance;
}

public SampleBRDFResult sampleBRDF(PhysicsBasedParameters parameters, float3 rayOut, float3 normal, RendererUniform uniforms, inout RNG rng, float wavelength = 0.0)
{
    float3 fr = float3(0.0);
    float3 sampledDirection = float3(0.0);
    float sampledPdf = 0.0;
    if (parameters.brdfType == 0)
    {
        // Sample Lambertian BRDF
        LambertianBRDF brdf = LambertianBRDF(parameters.albedo, uniforms.useCosineWeightedSampling);
        fr = brdf.evaluate();
        sampledDirection = brdf.sample(rayOut, normal, rng.next_2d());
        float lambertianPdf = brdf.pdf(sampledDirection, rayOut, normal);
        // Account for the probability of choosing lambertian in the overall PDF
        sampledPdf = lambertianPdf;
    }
    else if (parameters.brdfType == 1)
    {
        MirrorBRDF brdf = MirrorBRDF(parameters.albedo);
        // Note that BRDF evaluates to mirror's albedo here, unlike in
        // `getIllumination` where it evaluates to 0.
        // This is because we are sampling the BRDF for the next bounce for
        // indiret illumination, and not for the direct illumination.
        fr = brdf.evaluate();
        sampledDirection = brdf.sample(rayOut, normal);
        sampledPdf = brdf.pdf(sampledDirection, rayOut, normal);
    }
    else if (parameters.brdfType == 2)
    {
        if (uniforms.enableFresnelEffect)
        {
            // Extra Credit: Fresnel effect for Glass BRDF
            // TODO: Student implementation starts here.

            // Use wavelength-dependent IOR for Fresnel computation
            float effectiveIOR = cauchy_ior(wavelength, parameters.ior);

            float cosI = dot(rayOut, normal);
            float etaI = 1.0;
            float etaT = effectiveIOR;
            if (cosI < 0.0)
            {
                etaI = effectiveIOR;
                etaT = 1.0;
                cosI = -cosI;
            }

            float R = 1.0;
            float eta = etaI / etaT;
            float sin2T = eta * eta * (1.0 - cosI * cosI);
            if (sin2T < 1.0)
            {
                float cosT = sqrt(1.0 - sin2T);
                float cosFresnel = (etaI <= etaT) ? cosI : cosT;
                float R0 = (etaI - etaT) / (etaI + etaT);
                R0 = R0 * R0;
                float oneMinusCos = 1.0 - cosFresnel;
                R = R0 + (1.0 - R0) * oneMinusCos * oneMinusCos * oneMinusCos * oneMinusCos * oneMinusCos;
            }

            float u = rng.next_1d();
            if (u < R)
            {
                MirrorBRDF mirrorBrdf = MirrorBRDF(parameters.albedo);
                fr = mirrorBrdf.evaluate();
                sampledDirection = mirrorBrdf.sample(rayOut, normal);
                sampledPdf = 1.0;
            }
            else
            {
                GlassBRDF glassBrdf = GlassBRDF(parameters.albedo, parameters.ior);
                fr = glassBrdf.evaluate();
                sampledDirection = glassBrdf.sample(rayOut, normal, wavelength);
                sampledPdf = 1.0;
            }

            // TODO: Student implementation ends here.
        }
        else
        {
            // Naive Glass BRDF sampling without Fresnel effect.
            GlassBRDF brdf = GlassBRDF(parameters.albedo, parameters.ior);
            fr = brdf.evaluate();
            sampledDirection = brdf.sample(rayOut, normal, wavelength);
            float glassPdf = brdf.pdf(sampledDirection, rayOut, normal);
            // Account for the probability of choosing glass in the overall PDF
            sampledPdf = glassPdf;
        }
    }
    else if (parameters.brdfType == 3)
    {
        RetroreflectiveBRDF brdf = RetroreflectiveBRDF(parameters.albedo);
        fr = brdf.evaluate();
        sampledDirection = brdf.sample(rayOut);
        sampledPdf = brdf.pdf(sampledDirection, rayOut, normal);
    }
    else if (parameters.brdfType == 4)
    {
        RetroreflectiveLambertianBRDF brdf = RetroreflectiveLambertianBRDF(parameters.albedo);
        fr = brdf.evaluate();
        sampledDirection = brdf.sample(rayOut);
        sampledPdf = brdf.pdf(sampledDirection, rayOut, normal);
    }

    return SampleBRDFResult(fr, sampledDirection, sampledPdf);
}
