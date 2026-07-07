module brdf;

__include "./brdf/lambertian.slang";
__include "./brdf/mirror.slang";
__include "./brdf/glass.slang";

__include "./brdf/retroreflective.slang";
__include "./brdf/retroreflective_lambertian.slang";

public float3x3 getWorldToLocalMatrix(float3 normal, float3 rayOut)
{
    float3x3 worldToLocalMatrix = float3x3(1.0);
    float3 y = normalize(normal);
    float3 z = normalize(cross(y, rayOut));
    float3 x = normalize(cross(y, z));
    worldToLocalMatrix[0][0] = x.x;
    worldToLocalMatrix[0][1] = x.y;
    worldToLocalMatrix[0][2] = x.z;
    worldToLocalMatrix[1][0] = y.x;
    worldToLocalMatrix[1][1] = y.y;
    worldToLocalMatrix[1][2] = y.z;
    worldToLocalMatrix[2][0] = z.x;
    worldToLocalMatrix[2][1] = z.y;
    worldToLocalMatrix[2][2] = z.z;
    return worldToLocalMatrix;
}

public float3x3 transposeMatrix(float3x3 matrix)
{
    float3x3 transposedMatrix = float3x3(1.0);
    transposedMatrix[0][0] = matrix[0][0];
    transposedMatrix[0][1] = matrix[1][0];
    transposedMatrix[0][2] = matrix[2][0];
    transposedMatrix[1][0] = matrix[0][1];
    transposedMatrix[1][1] = matrix[1][1];
    transposedMatrix[1][2] = matrix[2][1];
    transposedMatrix[2][0] = matrix[0][2];
    transposedMatrix[2][1] = matrix[1][2];
    transposedMatrix[2][2] = matrix[2][2];
    return transposedMatrix;
}
