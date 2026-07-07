implementing "../model.slang";
import math;

public struct BVHNode
{
    public BoundingBox bound;
    public int left;
    public int right;
    public int primLeft;
    public int primRight;
    public int depth;

    public __init(BoundingBox bound, int left = -1, int right = -1, int primLeft = -1, int primRight = -1, int depth = -1)
    {
        this.bound = bound;
        this.left = left;
        this.right = right;
        this.primLeft = primLeft;
        this.primRight = primRight;
        this.depth = depth;
    }

    public float2 hit(Ray ray)
    {
        return this.bound.hit(ray);
    }
}

public struct BVH<T>
    where T : IRayCastable
{
    public struct HitResult
    {
        public T primitive;
        public RayHitResult rayHitResult;
    }

    // Slang buffer of BVHNode copied from Python.
    public RWStructuredBuffer<BVHNode> nodes;
    // Maximum number of nodes in the BVH, in this case, it'll be the size of the nodes buffer.
    public uint maxNodes;
    // Slang buffer of primitives represented by the BVH.
    public RWStructuredBuffer<T> primitives;
    // Number of primitives in the primitives buffer.
    public uint numPrimitives;

    public __init(RWStructuredBuffer<BVHNode> nodes, RWStructuredBuffer<T> primitives, uint numPrimitives, uint maxNodes)
    {
        this.nodes = nodes;
        this.primitives = primitives;
        this.numPrimitives = numPrimitives;
        this.maxNodes = maxNodes;
    }

    struct HitStack<int N>
    {
        uint[N] nodeIndices;
        uint top;

        __init()
        {
            this.top = 0;
        }

        [mutating]
        void push(uint nodeIndex)
        {
            this.nodeIndices[this.top] = nodeIndex;
            this.top += 1;
        }

        [mutating]
        uint pop()
        {
            this.top -= 1;
            return this.nodeIndices[this.top];
        }

        bool isEmpty()
        {
            return this.top == 0;
        }

        uint size()
        {
            return this.top;
        }
    }

    // BVH traversal to find the closest hit.
    public Optional<HitResult> hit(Ray ray)
    {
        // Initialize traversal.
        Optional<HitResult> hitResult = Optional<HitResult>();
        HitStack<64> stack;

        // TODO: Student implementation starts here.
        float closestT = ray.tRange.y; 
        stack.push(0);
        
        while (!stack.isEmpty())
        {
            uint nodeIndex = stack.pop();
            BVHNode node = nodes[nodeIndex];

            // Bounding box hit test
            float2 tBox = node.hit(ray); 

            // Check for misses, skip if tBox invalid, beyond closest hit or outside range
            bool boxValid = (tBox.x <= tBox.y);
            if (!boxValid) continue;
            if (tBox.y < ray.tRange.x) continue;
            if (tBox.x > closestT) continue;

            bool isLeaf = (node.left < 0 && node.right < 0);

            if (isLeaf)
            {
                // Leaf
                uint start = node.primLeft;
                uint end   = node.primRight;

                if (start < 0 || end < 0) continue;

                for (uint i = start; i < end; i++)
                {
                    T prim = primitives[i];
                    Optional<RayHitResult> hOpt = prim.hit(ray);

                    if (hOpt.hasValue)
                    {
                        RayHitResult h = hOpt.value;
                        if (h.t >= ray.tRange.x && h.t < closestT)
                        {
                            closestT = h.t;
                            hitResult = Optional<HitResult>(HitResult(prim, h));
                        }
                    }
                }
            }
            else
            {
                // Internal node:
                int l = node.left;
                int r = node.right;

                bool hasL = (l >= 0);
                bool hasR = (r >= 0);

                if (hasL && hasR)
                {
                    float2 tL = nodes[(uint)l].hit(ray);
                    float2 tR = nodes[(uint)r].hit(ray);

                    bool hitL = (tL.x <= tL.y) && (tL.y >= ray.tRange.x) && (tL.x <= closestT);
                    bool hitR = (tR.x <= tR.y) && (tR.y >= ray.tRange.x) && (tR.x <= closestT);

                    if (hitL && hitR)
                    {
                        if (tL.x < tR.x)
                        {
                            stack.push((uint)r);
                            stack.push((uint)l);
                        }
                        else
                        {
                            stack.push((uint)l);
                            stack.push((uint)r);
                        }
                    }
                    else if (hitL)
                    {
                        stack.push((uint)l);
                    }
                    else if (hitR)
                    {
                        stack.push((uint)r);
                    }
                }
                else if (hasL)
                {
                    stack.push((uint)l);
                }
                else if (hasR)
                {
                    stack.push((uint)r);
                }
            }
        }

        // TODO: Student implementation ends here.

        return hitResult;
    }
}
