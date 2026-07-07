implementing "../renderer.slang";

__include "./mesh_renderer/ray_mesh_intersection.slang";
__include "./mesh_renderer/mesh_material.slang";
__include "./mesh_renderer/mesh_illumination.slang";

public struct RayMeshSampleResult
{
    public float t;
    public float3 normal;
    public float4 color;
}

public Optional<RayMeshSampleResult> meshSample(float2 uv, RendererUniform uniforms, inout RNG rng)
{
    Ray ray = uniforms.camera.generateRay(uv);
    // Sample a wavelength for this ray (visible spectrum: 380–700 nm).
    ray.wavelength = 380.0 + rng.next_1d() * 320.0;

    float3 radiance = float3(0.0);
    float3 throughput = float3(1.0);
    float t = float.maxValue;
    float3 normalAtFirstHit = float3(0.0);
    const float EPSILON = 1e-2;
    bool renderLight = true;
    float distance = 0.0;

    for (int depth = 0; depth < uniforms.pathTraceDepth; depth++)
    {
        bool breakRendering = false;
        bool hitGlass = false;
        const int maxGlassBounce = 10;
        for (int i = 0; i < maxGlassBounce; i++)
        {
            // Step 1: Check if the ray intersects with any rectangular light or mesh.
            // Use the radiance of whichever one (light source or mesh) that's closer.
            Optional<RectangularLight.LightHitResult> rayRectangularLightIntersectionResult = rayRectangularLightIntersection(ray, uniforms);
            Optional<RayMeshIntersectionResult> rayMeshIntersectionResult = rayMeshIntersection(ray, uniforms);

            // If the ray does not intersect with any light source or mesh.
            if (!rayRectangularLightIntersectionResult.hasValue && !rayMeshIntersectionResult.hasValue)
            {
                radiance += throughput * uniforms.ambientColor.xyz;
                breakRendering = true;
                break;
            }

            // If the ray intersects with the light source, and light source is closer than the mesh,
            if (!rayMeshIntersectionResult.hasValue || rayRectangularLightIntersectionResult.hasValue && rayMeshIntersectionResult.value.closestHit.t > rayRectangularLightIntersectionResult.value.t)
            {
                // renderLIght is set to false at a later point in code, for
                // indirect illumination. This is because we've already accounted
                // for it in the direct illumination.
                if (renderLight)
                {
                    radiance += throughput * rayRectangularLightIntersectionResult.value.radiance;
                }
                if (depth == 0)
                {
                    t = rayRectangularLightIntersectionResult.value.t;
                    normalAtFirstHit = rayRectangularLightIntersectionResult.value.normal;
                }
                breakRendering = true;
                break;
            }

            // If the ray intersects with the mesh, and mesh is closer than the light source,
            if (!rayRectangularLightIntersectionResult.hasValue || rayMeshIntersectionResult.hasValue && rayMeshIntersectionResult.value.closestHit.t < rayRectangularLightIntersectionResult.value.t)
            {
                // Step 2: Get the Material Parameters for the hit point.
                // Step 2a: Get the hit point and the triangle hit by the ray.
                RayHitResult result = rayMeshIntersectionResult.value.closestHit;
                Triangle hitTriangle = rayMeshIntersectionResult.value.hitTriangle;
                float3 hitPoint = ray.origin + result.t * ray.direction;
                float3 barycentricCoord = hitTriangle.calculateBarycentricCoord(hitPoint);
                float3 normal = result.normal;
                if (uniforms.smoothShading)
                {
                    normal = normalize(hitTriangle.getNormal(barycentricCoord));
                }

                // Bookkeeping for the first hit.
                if (depth == 0)
                {
                    t = result.t;
                    normalAtFirstHit = normal;
                }

                // Step 2b: Get the Material Parameters for the hit point.
                PhysicsBasedParameters parameters = getHitPointParameters(uv, uniforms, hitTriangle, normal, barycentricCoord, hitPoint);
                if (uniforms.visualizeLevelOfDetail || uniforms.visualizeAlbedo)
                {
                    float4 color = float4(float3(parameters.albedo), 1.0);
                    return Optional<RayMeshSampleResult>(RayMeshSampleResult(result.t, normal, color));
                }

                // Step 3: Compute the direct illumination at the hit point using the Material Parameters.
                float3 rayOut = -ray.direction;
                float3 directIllumination = getDirectIllumination(parameters, uniforms, rayOut, normal, hitPoint, rng);
                radiance += directIllumination * throughput;

                // TODO: Student implementation starts here.
                // Step 4: Setup for Indirect Illumination by sampling the BRDF for
                // the ray direction of the next bounce.

                // TODO Step 4a: Student implementation starts here.

                SampleBRDFResult brdfResult = sampleBRDF(parameters, rayOut, normal, uniforms, rng, ray.wavelength);

                // TODO Step 4a: Student implementation ends here.

                // NOTE: For Lambertian surfaces, we've just accounted for direct
                // illumination at depth=0. Therefore, we ensure that the next
                // bounce is not on a light source.
                if (parameters.brdfType == 0)
                {
                    renderLight = false;
                }

                // Step 4a: Sample BRDF for the next bounce.

                // Step 4b: Update the throughput for the next bounce.
                // Not glass BRDF.
                if (parameters.brdfType != 2)
                {
                    // TODO Step 4b: Student implementation starts here.

                    float cosTheta = max(dot(normal, brdfResult.sampledDirection), 0.0);
                    throughput *= brdfResult.fr * cosTheta / (brdfResult.sampledPdf + EPSILON);

                    // TODO Step 4b: Student implementation ends here.

                    if (max(throughput.x, max(throughput.y, throughput.z)) < 1e-2)
                    {
                        breakRendering = true;
                        break;
                    }
                }

                // If glass BRDF, we don't update the throughput since we assume the glass is perfectly transparent.
                // We just need to keep track of whether we've hit a glass surface, since we want to allow up to `maxGlassBounce` bounces on glass surfaces.
                // When we hit a glass, we'll also allow rendering light directly for the caustics effect.
                if (parameters.brdfType == 2)
                {
                    renderLight = true;
                    hitGlass = true;
                }

                // Step 4c: Update the ray for the next bounce.
                // TODO Step 4c: Student implementation starts here.

                ray = Ray(hitPoint, brdfResult.sampledDirection, float2(EPSILON, float.maxValue), ray.wavelength);

                // TODO Step 4c: Student implementation ends here.

                // TODO: Student implementation ends here.
            }

            if (!hitGlass)
            {
                break;
            }
        }
        if (breakRendering)
        {
            break;
        }
    }

    // Spectral accumulation: weight the radiance by this ray's wavelength color.
    // Each ray contributes its CIE color matching function value, and the Monte Carlo
    // average over many uniformly-sampled wavelengths integrates to the correct pixel color.
    // Normalization: wavelength_range / integral(y_bar) ≈ 320 / 106.85 ≈ 3.0
    // ensures an equal-energy white spectrum converges to (1, 1, 1).
    static const float SPECTRAL_NORM = 3.0;
    float3 spectralColor = radiance * wavelength_to_sRGB(ray.wavelength) * SPECTRAL_NORM;

    return Optional<RayMeshSampleResult>(RayMeshSampleResult(t, normalAtFirstHit, float4(spectralColor, 1.0)));
}
