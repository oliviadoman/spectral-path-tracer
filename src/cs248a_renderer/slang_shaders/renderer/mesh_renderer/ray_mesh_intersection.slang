implementing "../renderer.slang";

import light;

public struct RayMeshIntersectionResult
{
    public RayHitResult closestHit;
    public Triangle hitTriangle;
}

public Optional<RectangularLight.LightHitResult> rayRectangularLightIntersection(Ray ray, RendererUniform uniforms)
{
    Optional<RectangularLight.LightHitResult> closestLightHitResult = Optional<RectangularLight.LightHitResult>();
    for (int i = 0; i < uniforms.rectangularLightCount; i++)
    {
        Optional<RectangularLight.LightHitResult> lightHitResult = uniforms.rectangularLightBuf[i].hit(ray);
        if (lightHitResult.hasValue)
        {
            if (!closestLightHitResult.hasValue || lightHitResult.value.t < closestLightHitResult.value.t)
            {
                closestLightHitResult = lightHitResult;
            }
        }
    }
    return closestLightHitResult;
}

public Optional<RayMeshIntersectionResult> rayMeshIntersection(Ray ray, RendererUniform uniforms, bool occlusionTest = false)
{
    Optional<RayHitResult> result = Optional<RayHitResult>();
    Optional<RayMeshIntersectionResult> allResult = Optional<RayMeshIntersectionResult>();
    Optional<Triangle> hitTriangle = Optional<Triangle>();

    // IMPORTANT NOTE: Check the modified signature of `rayMeshIntersection` function in ray_mesh_intersection.slang.
    // Can you modify your existing code to make use of this flag? This is helpful in `isLightOccluded` function.

    // TODO: Student implementation starts here.
    if (uniforms.useBVH)
    {
        Optional<BVH<Triangle>.HitResult> bvhHit = uniforms.bvh.hit(ray);
        if (bvhHit.hasValue)
        {
            result = bvhHit.value.rayHitResult;
            hitTriangle = bvhHit.value.primitive;
        }
    }
    else
    {
        Optional<RayHitResult> closestHit = Optional<RayHitResult>();
        float bestT = ray.tRange.y;

        for (uint i = 0; i < uniforms.triangleCount; i++)
        {
            Triangle triangle = uniforms.triangleBuf[i];
            Optional<RayHitResult> hitResult = triangle.hit(ray);

            if (hitResult.hasValue)
            {
                RayHitResult r = hitResult.value;
                if (r.t < bestT)
                {
                    bestT = r.t;
                    closestHit = r;
                    hitTriangle = triangle;

                    if (occlusionTest)
                        break;
                }
            }
        }

        if (closestHit.hasValue)
        {
            result = closestHit.value;
        }
    }

    // TODO: Student implementation ends here.

    if (result.hasValue && hitTriangle.hasValue)
    {
        allResult = Optional<RayMeshIntersectionResult>(RayMeshIntersectionResult(result.value, hitTriangle.value));
    }

    return allResult;
}
