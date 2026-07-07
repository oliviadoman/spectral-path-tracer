implementing "../model.slang";
import math;

public struct Camera
{
    // The inverse view matrix of the camera (matrix transform from view space to world space).
    public float4x4 invViewMatrix;
    // The canvas size of the target image in pixels.
    public uint2 canvasSize;
    // The focal length of the camera in pixels (distance between the pinhole and the image plane).
    public float focalLength;

    /**
     * Generate a camera ray given a normalized uv coordinate on canvas.
     * @param uv The normalized uv coordinate from (0, 0) in the bottom-left to (1, 1) in the top-right.
     * @return The generated Ray. Before you start working the transform section, generate ray as if the camera is at origin looking towards negative z direction.
     * After you finish the transform section, you should transform the ray from view space to world space using the inverse view matrix.
     */
    public Ray generateRay(float2 uv)
    {
        // TODO: Student implementation starts here.
        Ray ray;

        float2 ndc = (uv - 0.5) * float2(canvasSize);

        ray.origin = float3(0.0, 0.0, 0.0);
        ray.direction = normalize(float3(ndc, -focalLength));
        
        ray.tRange = float2(0.0, 1e10);
        ray = ray.transform(this.invViewMatrix);

        return ray;
        // TODO: Student implementation ends here.
    }
}
