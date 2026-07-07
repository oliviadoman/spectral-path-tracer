implementing "../primitive.slang";
import math;

public struct Triangle : IBoundingBox, IRayCastable
{
    public float3[3] vertices;
    public float3[3] normals;
    public float2[3] uvs;
    public float3[3] colors;
    public uint materialId;
    public uint offset;

    public BoundingBox boundingBox()
    {
        return BoundingBox(float3(0.0), float3(0.0));
    }

    /* Returns the average color of the triangle. */
    public float3 averageColor()
    {
        return (this.colors[0] + this.colors[1] + this.colors[2]) / 3.0;
    }

    /**
     * Calculates the barycentric coordinates of a point on the triangle.
     * @param p The point on the triangle to calculate the barycentric coordinates for.
     * @return The barycentric coordinates of the point.
     */
    public float3 calculateBarycentricCoord(float3 p)
    {
        const float EPSILON = 1e-6;
        float u = 0.0;
        float v = 0.0;
        float w = 0.0;

        // TODO: Student implementation starts here.

        float3 p0 = this.vertices[2];
        float3 p1 = this.vertices[0];
        float3 p2 = this.vertices[1];
 
        float3 v0 = p1 - p0;
        float3 v1 = p2 - p0;
        float3 v2 = p - p0;

        float dot00 = dot(v0, v0);
        float dot01 = dot(v0, v1);
        float dot02 = dot(v0, v2);
        float dot11 = dot(v1, v1);
        float dot12 = dot(v1, v2);
        float dot20 = dot(v2, v0);
        float dot21 = dot(v2, v1);

        float denom = dot00 * dot11 - dot01 * dot01;

        // Check if the triangle is degenerate
        if (abs(denom) < EPSILON){
            return float3(0.0, 0.0, 0.0);
        }

        float invDenom = 1.0 / denom;

        u = (dot11 * dot20 - dot01 * dot21) * invDenom;
        v = (dot00 * dot21 - dot01 * dot20) * invDenom;
        w = 1.0 - u - v;

        // TODO: Student implementation ends here.

        return float3(u, v, w);
    }

    public float2 getUV(float3 barycentricCoord)
    {
        float2 uv = float2(0.0);

        float u = barycentricCoord.x;
        float v = barycentricCoord.y;
        float w = barycentricCoord.z;
        uv = u * this.uvs[0] + v * this.uvs[1] + w * this.uvs[2];
        
        return uv;
    }

    public float3 getColor(float3 barycentricCoord)
    {
        float u = barycentricCoord.x;
        float v = barycentricCoord.y;
        float w = barycentricCoord.z;
        float3 color = u * this.colors[0] + v * this.colors[1] + w * this.colors[2];
        return color;
    }

    public float3 getNormal(float3 barycentricCoord)
    {
        float u = barycentricCoord.x;
        float v = barycentricCoord.y;
        float w = barycentricCoord.z;
        float3 normal = u * this.normals[0] + v * this.normals[1] + w * this.normals[2];
        return normalize(normal);
    }

    /**
     * Test ray-triangle intersection.
     * @param ray The ray to test against the triangle.
     * @return An Optional containing RayHitResult if the ray hits the triangle, otherwise an empty Optional.
     */
    public Optional<RayHitResult> hit(Ray ray)
    {
        // TODO: Student implementation starts here.

        // Triangle vertices
        float3 v0 = this.vertices[0];
        float3 v1 = this.vertices[1];
        float3 v2 = this.vertices[2];

        // Edge vectors
        float3 e1 = v1 - v0;
        float3 e2 = v2 - v0;    
        
        // Calc determinat 
        float3 p = cross(ray.direction, e2);
        float det = dot(e1, p);
        
        // Check if ray is in plane or in parallel
        if (abs(det) < 1e-8)
        {
            return Optional<RayHitResult>();
        }
        
        float invDet = 1.0 / det;

        // barycentric coords
        float3 s = ray.origin - v0;
        float u = dot(s, p) * invDet;
        if (u < 0.0 || u > 1.0)
        {
            return Optional<RayHitResult>();
        }
        
        float3 q = cross(s, e1);
        float v = dot(ray.direction, q) * invDet;
        if (v < 0.0 || (u + v) > 1.0)
        {
            return Optional<RayHitResult>();
        }
        
        float t = dot(e2, q) * invDet;
        if (t < ray.tRange.x || t > ray.tRange.y)
        {
            return Optional<RayHitResult>();
        }
        
        RayHitResult result;
        result.t = t;
        result.normal = normalize(cross(e1, e2));
        
        return Optional<RayHitResult>(result);

        // TODO: Student implementation ends here.
    }

    public uint getMaterialId()
    {
        return this.materialId + this.offset;
    }
}
