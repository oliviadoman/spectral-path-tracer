implementing "../renderer.slang";

import math;
import texture;

public static uint MAX_STEPS = 1024;
public static float EPSILON = 1e-6;

public static float STEP_SIZE = 0.01;
public static float DENSITY_SCALE = 5.0;

/**
 * Perform ray marching through the volume and accumulate color.
 * @param uv The normalized uv coordinate from (0, 0) in the bottom-left to (1, 1) in the top-right.
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @param tMax The maximum t value for ray marching (usually the nearest primitive intersection t).
 * @param primColor The color of the nearest primitive intersection.
 * @return The accumulated color after ray marching through the volume.
 */
public float4 volumeSample(float2 uv, RendererUniform uniforms, float tMax, float4 primColor)
{
    // TODO: Student implementation starts here.

    Ray ray = uniforms.camera.generateRay(uv);
    ray.tRange.y = min(ray.tRange.y, tMax);
    Ray localRay = ray.transform(uniforms.volume.invModelMatrix);

    float4 color = accumulateColor<1024>(
            localRay,
            uniforms.volume.bound,
            MAX_STEPS,
            STEP_SIZE,
            DENSITY_SCALE,
            primColor,
            uniforms.volume.tex
        );

    return color;
    // TODO: Student implementation ends here.
}

/**
 * Backward pass for volumetric ray marching at a single uv.
 * @param uv The normalized uv coordinate from (0, 0) in the bottom-left to (1, 1) in the top-right.
 * @param uniforms The renderer uniform containing camera, sampling, and scene information.
 * @param outGrad The output gradient w.r.t. the sampled color.
 */
public void volumeSampleBwd(float2 uv, RendererUniform uniforms, float4 outGrad)
{
    Ray ray = uniforms.camera.generateRay(uv);
    Ray localRay = ray.transform(uniforms.volume.invModelMatrix);

    DifferentialPtrPair<DiffTexture3D<float, 4>> texPair =  {
        uniforms.volume.tex,
        uniforms.volume.dTex
    };

    bwd_diff(accumulateColor<1024>)(
        localRay,
        uniforms.volume.bound,
        MAX_STEPS,
        STEP_SIZE,
        DENSITY_SCALE,
        float4(0.0, 0.0, 0.0, 1.0),
        texPair,
        outGrad
    );
}

/**
 * Ray march through the volume and accumulate color.
 * @param ray The ray in local space.
 * @param volumeBound The bounding box of the volume in local space.
 * @param maxSteps The maximum number of marching steps.
 * @param stepSize The size of each marching step.
 * @param densityScale The scale factor for the volume density (alpha channel).
 * @param backgroundColor The background color behind the volume
                          (this can be the ambient color if there's no primitive behind the volume, or the color of the primitive hit if there's one).
 * @param data The 3D texture storing the volume data (rgba).
 * @return The accumulated color after ray marching through the volume.
 */
[Differentiable]
public float4 accumulateColor<let N : uint>(
    no_diff Ray ray,
    no_diff BoundingBox volumeBound,
    no_diff uint maxSteps,
    no_diff float stepSize,
    no_diff float densityScale,
    no_diff float4 backgroundColor,
    DiffTexture3D<float, 4> data)
{
    // TODO: Student implementation starts here.

    float2 tHit = volumeBound.hit(ray);
    float tEnter = tHit.x;
    float tExit  = tHit.y;
    
    if (tExit < tEnter)
        return backgroundColor;
    
    // Clamp start to in front of the camera
    tEnter = max(tEnter, 0.0);
    tExit = min(tExit, ray.tRange.y);
    
    float3 boxSize = volumeBound.size();
    float3 radiance = float3(0.0);
    float transmittance = 1.0;
    
    // March from tEnter to tExit
    float t = tEnter;
    
    [MaxIters(1024)] 
    for (uint i = 0; i < maxSteps; i++)
    {
        if (t > tExit || transmittance < 1e-4)
            break;
        
        float3 p = ray.origin + t * ray.direction;
        
        // Map point in box-> texture coords
        float3 uvw = (p - volumeBound.pMin) / boxSize;
        uvw = clamp(uvw, 0.0, 1.0);
        float4 s = sampleTrilinear(data, uvw);
        
        float density = max(s.a, 0.0) * densityScale;
        
        // Emission 
        radiance += transmittance * s.rgb * density * stepSize;
        
        // Update transmittance
        transmittance *= exp(-density * stepSize);
        
        t += stepSize;
        
    }
    float3 finalColor = radiance + backgroundColor.rgb * transmittance;

    return float4(finalColor, 1.0);

    // TODO: Student implementation ends here.
}
