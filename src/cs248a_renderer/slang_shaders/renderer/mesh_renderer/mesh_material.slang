implementing "../renderer.slang";

import utils;

public float2 getShiftedTexUV(float2 uv, RendererUniform uniforms, Triangle triangle, float2 delta, float2 tex_uv)
{
    float2 shifted_uv = uv + delta;
    Ray ray = uniforms.camera.generateRay(shifted_uv);
    Optional<RayHitResult> hitResult = triangle.hit(ray);
    float2 result = tex_uv;
    if (hitResult.hasValue)
    {
        float3 hitPoint = ray.origin + hitResult.value.t * ray.direction;
        float3 barycentricCoord = triangle.calculateBarycentricCoord(hitPoint);
        return triangle.getUV(barycentricCoord);
    }

    Optional<RayMeshIntersectionResult> rayMeshIntersectionResult_dx = rayMeshIntersection(ray, uniforms);
    if (rayMeshIntersectionResult_dx.hasValue)
    {
        Triangle hitTriangle = rayMeshIntersectionResult_dx.value.hitTriangle;
        if (hitTriangle.getMaterialId() == triangle.getMaterialId())
        {
            float3 hitPoint = ray.origin + rayMeshIntersectionResult_dx.value.closestHit.t * ray.direction;
            float3 barycentricCoord = hitTriangle.calculateBarycentricCoord(hitPoint);
            return hitTriangle.getUV(barycentricCoord);
        }
    }

    return tex_uv;
}

public float getLevel(float2 uv, RendererUniform uniforms, Triangle triangle, float2 tex_uv)
{
    float level = 0.0;

    // TODO: Student implementation starts here.

    const float EPSILON = 1e-8;

    float w = uniforms.camera.canvasSize.x;
    float h = uniforms.camera.canvasSize.y;

    float2 pixelSize = 1.0 / float2(w, h);

    Ray ray_xp;
    Ray ray_xn;
    Ray ray_yp;
    Ray ray_yn;

    ray_xp = uniforms.camera.generateRay(uv + float2(pixelSize.x, 0));
    ray_xn = uniforms.camera.generateRay(uv + float2(-pixelSize.x, 0));
    ray_yp = uniforms.camera.generateRay(uv + float2(0, pixelSize.y));
    ray_yn = uniforms.camera.generateRay(uv + float2(0, -pixelSize.y));

    Optional<RayHitResult> hit_xp = triangle.hit(ray_xp);
    Optional<RayHitResult> hit_xn = triangle.hit(ray_xn);
    Optional<RayHitResult> hit_yp = triangle.hit(ray_yp);
    Optional<RayHitResult> hit_yn = triangle.hit(ray_yn);

    float2 texUV_xp = tex_uv;
    float2 texUV_xn = tex_uv;
    float2 texUV_yp = tex_uv;
    float2 texUV_yn = tex_uv;

    if (hit_xp.hasValue)
    {
        float3 bary_xp = triangle.calculateBarycentricCoord(hit_xp.value.t * ray_xp.direction + ray_xp.origin);
        texUV_xp = triangle.getUV(bary_xp);
    }

    if (hit_xn.hasValue)
    {
        float3 bary_xn = triangle.calculateBarycentricCoord(hit_xn.value.t * ray_xn.direction + ray_xn.origin);
        texUV_xn = triangle.getUV(bary_xn);
    }

    if (hit_yp.hasValue)
    {
        float3 bary_yp = triangle.calculateBarycentricCoord(hit_yp.value.t * ray_yp.direction + ray_yp.origin);
        texUV_yp = triangle.getUV(bary_yp);
    }

    if (hit_yn.hasValue)
    {
        float3 bary_yn = triangle.calculateBarycentricCoord(hit_yn.value.t * ray_yn.direction + ray_yn.origin);
        texUV_yn = triangle.getUV(bary_yn);
    }

    float2 du_dx = (texUV_xp - texUV_xn) / (2.0 * pixelSize.x);
    float2 du_dy = (texUV_yp - texUV_yn) / (2.0 * pixelSize.y);

    float rho_x = sqrt(du_dx.x * du_dx.x + du_dx.y * du_dx.y);
    float rho_y = sqrt(du_dy.x * du_dy.x + du_dy.y * du_dy.y);

    float rho = max(rho_x, rho_y);
    rho = max(rho, EPSILON);

    level = log2(rho);
    level = max(level, 0.0);

    return level;

    // TODO: Student implementation ends here.

    return level;
}

public PhysicsBasedParameters getHitPointParameters(float2 uv, RendererUniform uniforms, Triangle triangle, float3 normal, float3 barycentricCoord, float3 hitPoint)
{
    float2 tex_uv = triangle.getUV(barycentricCoord);
    float level = getLevel(uv, uniforms, triangle, tex_uv);
    uint materialId = triangle.materialId + triangle.offset;
    PhysicsBasedMaterial physicsBasedMaterial = uniforms.physicsBasedMaterialBuf[materialId];
    PhysicsBasedParameters parameters = sampleMaterial(physicsBasedMaterial, uniforms.physicsBasedMaterialTextureBuf, tex_uv, level, uniforms.visualizeLevelOfDetail);
    if (uniforms.visualizeBarycentricCoords)
    {
        parameters.albedo = barycentricCoord;
    }
    if (uniforms.visualizeTexUV)
    {
        parameters.albedo = float3(tex_uv, 0.0);
    }
    return parameters;
}
