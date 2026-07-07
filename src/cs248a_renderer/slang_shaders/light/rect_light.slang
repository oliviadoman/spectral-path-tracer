implementing "../light.slang";

import math;
import primitive;
import utils;

public struct RectangularLight
{
    public float3 bottomLeftVertex;
    public float3 bottomEdge;
    public float3 leftEdge;
    public float3 normal;
    public float area;
    public float3 color;
    public float intensity;
    public bool doubleSided;

    public struct LightHitResult
    {
        public float t;
        public float3 normal;
        public float3 radiance;
    }

    public LightSample sample(float3 hitPoint, float2 randomEpsilon)
    {
        float3 randomPointOnLight = this.bottomLeftVertex + this.bottomEdge * randomEpsilon.x + this.leftEdge * randomEpsilon.y;
        float3 toLight = randomPointOnLight - hitPoint;
        float3 lightDirection = normalize(toLight);
        float lightDistance = length(toLight);
        float3 radiance = getRadiance(lightDirection, lightDistance);
        float pdf = getPdf(hitPoint, randomPointOnLight);
        return LightSample(lightDirection, radiance, pdf, lightDistance);
    }

    public float getPdf(float3 hitPoint, float3 pointOnLight)
    {
        const float EPSILON = 1e-6;
        float pdf = 1.0;

        // TODO: Student implementation starts here.

        float3 toHitPoint = hitPoint - pointOnLight;
        float distance = length(toHitPoint);
        float3 dirToHitPoint = toHitPoint / (distance + EPSILON);
        float cosTheta = abs(dot(this.normal, dirToHitPoint));
        pdf = (distance * distance) / (cosTheta * this.area + EPSILON);

        // TODO: Student implementation ends here.

        return pdf;
    }

    public float3 getRadiance(float3 lightDirection, float lightDistance)
    {
        return this.color * this.intensity;
    }

    public Optional<LightHitResult> hit(Ray ray)
    {
        Optional<LightHitResult> lightHitResult = Optional<LightHitResult>();
        // Create 2 triangles from the rectangle
        // Recover the vertices of the triangles
        float3 v0 = this.bottomLeftVertex;
        float3 v1 = v0 + this.bottomEdge;
        float3 v2 = v1 + this.leftEdge;
        float3 v3 = v0 + this.leftEdge;

        float3[3] vertices1 = float3[3](v0, v1, v2);
        float3[3] vertices2 = float3[3](v0, v2, v3);
        float3[3] normals = float3[3](this.normal, this.normal, this.normal);
        float2[3] uvs = float2[3](float2(0.0, 0.0), float2(1.0, 0.0), float2(1.0, 1.0));
        float3[3] colors = float3[3](this.color, this.color, this.color);

        Triangle triangle1 = Triangle(vertices1, normals, uvs, colors);
        Triangle triangle2 = Triangle(vertices2, normals, uvs, colors);

        Optional<RayHitResult> hitResult = Optional<RayHitResult>();
        Optional<RayHitResult> hitResult1 = triangle1.hit(ray);

        if (hitResult1.hasValue && hitResult.value.t <= ray.tRange.y)
        {
            hitResult = hitResult1;
        }
        else
        {
            Optional<RayHitResult> hitResult2 = triangle2.hit(ray);
            if (hitResult2.hasValue && hitResult.value.t <= ray.tRange.y)
            {
                hitResult = hitResult2;
            }
        }

        if (hitResult.hasValue)
        {
            // Calculate the radiance at the hit point
            float3 hitPoint = ray.origin + hitResult.value.t * ray.direction;
            float lightDistance = length(hitPoint - ray.origin - ray.tRange.x * ray.direction);
            float3 radiance = getRadiance(ray.direction, lightDistance);
            return Optional<LightHitResult>(LightHitResult(hitResult.value.t, hitResult.value.normal, radiance));
        }

        return Optional<LightHitResult>();
    }
}
