implementing "../math.slang";

public struct BoundingBox
{
    public float3 pMin;
    public float3 pMax;

    public static BoundingBox union
    (BoundingBox a, BoundingBox b)
    {
        float3 uMin = min(a.pMin, b.pMin);
        float3 uMax = max(a.pMax, b.pMax);
        return BoundingBox(uMin, uMax);
    }

    public __init(float3 pMin, float3 pMax)
    {
        this.pMin = pMin;
        this.pMax = pMax;
    }

    public float3 centroid()
    {
        return 0.5 * (this.pMin + this.pMax);
    }

    public float3 size()
    {
        return this.pMax - this.pMin;
    }

    public float area()
    {
        float3 size = this.size();
        return 2 * (size.x * size.y + size.y * size.z + size.z * size.x);
    }

    public float2 hit(Ray ray)
    {
        // TODO: Student implementation starts here.

        float3 invDir = 1.0 / ray.direction;
        float3 t0 = (this.pMin - ray.origin) * invDir;
        float3 t1 = (this.pMax - ray.origin) * invDir;
        
        // Makesure t0 has the near, t1 the far 
        float3 tMin = min(t0, t1);
        float3 tMax = max(t0, t1);
        
        // Find largest tMin and smallest tMax
        float tNear = max(max(tMin.x, tMin.y), tMin.z);
        float tFar = min(min(tMax.x, tMax.y), tMax.z);
        
        // Return the interval [tNear, tFar]
        return float2(tNear, tFar);

        // TODO: Student implementation ends here.
    }
};

public interface IBoundingBox
{
    public BoundingBox boundingBox();
}

public void loadBoundingBoxes<T : IBoundingBox>(
    uint tid,
    uint offset,
    StructuredBuffer<T> primitives,
    RWStructuredBuffer<BoundingBox> boundingBoxes)
{
    uint idx = tid + offset;
    boundingBoxes[tid] = primitives[idx].boundingBox();
}

public void splitPrimitives<T : IBoundingBox>(
    uint tid,
    uint offset,
    StructuredBuffer<T> primitives,
    RWStructuredBuffer<uint> leftFlags,
    RWStructuredBuffer<uint> rightFlags,
    uint axis,
    float threshold)
{
    BoundingBox box = primitives[tid + offset].boundingBox();
    float3 centroid = box.centroid();
    if (centroid[uint(axis)] < threshold)
    {
        leftFlags[tid + offset] = 1;
        rightFlags[tid + offset] = 0;
    }
    else
    {
        leftFlags[tid + offset] = 0;
        rightFlags[tid + offset] = 1;
    }
}

public void reduceUnionPass(
    uint tid,
    uint numBoxes,
    StructuredBuffer<BoundingBox> inputBoxes,
    RWStructuredBuffer<BoundingBox> outputBoxes)
{
    uint idx = tid * 2;
    if (idx >= numBoxes)
        return;
    BoundingBox boxA = inputBoxes[idx];
    BoundingBox boxB = (idx + 1 < numBoxes) ? inputBoxes[idx + 1] : boxA;
    BoundingBox unionBox = BoundingBox.union
    (boxA, boxB);
    outputBoxes[tid] = unionBox;
}
