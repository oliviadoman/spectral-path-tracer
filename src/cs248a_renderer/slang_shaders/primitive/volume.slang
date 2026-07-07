implementing "../primitive.slang";
import math;
import texture;

// The size of each marching step.
static float STEP_SIZE = 0.005;
// The density threshold to consider a hit.
static float DENSITY_THRESHOLD = 0.25;
// The delta used for finite difference normal estimation.
static float FINITE_DIFF_DELTA = 0.001;

public struct Volume
{
    public BoundingBox bound;
    public SharedTexture3D tex;
    public float4x4 modelMatrix;
    public float4x4 invModelMatrix;

    /**
     * Test ray-volume bounding box intersection.
     * @param ray The ray to test against the volume.
     * @param volumeTexBuf The texture buffer contains all the volumetrically represented models in the scene .
     * @return An Optional containing RayHitResult if the ray hits the volume, otherwise an empty Optional.
     */
    public Optional<RayHitResult> hit(Ray ray, SharedTexture3DBuffer<float4> volumeTexBuf)
    {
        // TODO: Student implementation starts here.
        // Transform ray to local 
        Ray localr = ray.transform(invModelMatrix);

        float t = ray.tRange.x;
        float tMax = ray.tRange.y;

        // March through volume
        while (t < tMax)
        {
            float3 p = localr.origin + localr.direction * t;
            float3 uvw = getUVW(p);

            // Check uvw valid
            if (uvw.x >= 0.0 && uvw.x <= 1.0 &&
                uvw.y >= 0.0 && uvw.y <= 1.0 &&
                uvw.z >= 0.0 && uvw.z <= 1.0) 
            {
                // Sample density
                float4 sample = volumeTexBuf.trilinearSample(tex, uvw);
                float density = sample.a;

                // Density check 
                if (density >= DENSITY_THRESHOLD){

                    // Compute normal with finite differences
                    float3 dpdx = float3(FINITE_DIFF_DELTA, 0,0);
                    float3 dpdy = float3(0, FINITE_DIFF_DELTA, 0);
                    float3 dpdz = float3(0, 0, FINITE_DIFF_DELTA);

                    float dx = volumeTexBuf.trilinearSample(tex, getUVW(p+ dpdx)).a 
                               - volumeTexBuf.trilinearSample(tex, getUVW(p - dpdx)).a;

                    float dy = volumeTexBuf.trilinearSample(tex, getUVW(p + dpdy)).a 
                               - volumeTexBuf.trilinearSample(tex, getUVW(p - dpdy)).a;

                    float dz = volumeTexBuf.trilinearSample(tex, getUVW(p + dpdz)).a 
                               - volumeTexBuf.trilinearSample(tex, getUVW(p - dpdz)).a;

                    float3 normal = normalize(float3(dx, dy, dz));

                    // Transform to world space
                    float3 worldP = mul(modelMatrix, float4(p, 1.0)).xyz;
                    float3 worldN = mul(modelMatrix, float4(normal, 0.0)).xyz;

                    RayHitResult result;
                    result.t = t;
                    result.normal = normalize(worldN);

                    return Optional<RayHitResult>(result);
                }
               
            } 
            t += STEP_SIZE;   
        }
        // TODO: Student implementation ends here.

        return Optional<RayHitResult>();
    }

    /**
     * Get the uvw coordinates of a point in local space.
     * @param p The point in world space.
     * @return The uvw coordinates in [0, 1].
     */
    public float3 getUVW(float3 p)
    {
        // Compute uvw coordinates in [0, 1].
        float3 minBound = this.bound.pMin;
        float3 maxBound = this.bound.pMax;
        return (p - minBound) / (maxBound - minBound);
    }
};

