implementing "../primitive.slang";
import math;

public struct Gaussian : IDifferentiable, IBoundingBox
{
    public float3 position;
    public float4 rotation;
    public float3 scale;

    public float3 color;
    public float opacity;

    [Differentiable]
    public __init(float3 position, float4 rotation, float3 scale, float3 color, float opacity)
    {
        this.position = position;
        this.rotation = rotation;
        this.scale = scale;
        this.color = color;
        this.opacity = opacity;
    }

    [Differentiable]
    public float3 scaleExp()
    {
        return exp(this.scale);
    }

    [Differentiable]
    public float3 colorSigmoid()
    {
        return sigmoid(this.color);
    }

    [Differentiable]
    public float opacitySigmoid()
    {
        return sigmoid(this.opacity).x;
    }

    [Differentiable]
    public float3x3 covarianceMatrix()
    {
        float3 scale = this.scaleExp();
        float3x3 R = quat.asRotMat(this.rotation);
        float3x3 S = float3x3(
            float3(scale.x, 0.0, 0.0),
            float3(0.0, scale.y, 0.0),
            float3(0.0, 0.0, scale.z));
        float3x3 M = mul(R, S);
        return mul(M, linalg.transpose(M));
    }

    [Differentiable]
    public float3x3 invCovarianceMatrix()
    {
        float3 scale = this.scaleExp();
        float3x3 R = quat.asRotMat(this.rotation);
        float3x3 invS = float3x3(
            float3(1 / scale.x, 0.0, 0.0),
            float3(0.0, 1 / scale.y, 0.0),
            float3(0.0, 0.0, 1 / scale.z));
        float3x3 M = mul(R, invS);
        return mul(M, linalg.transpose(M));
    }

    [Differentiable]
    public float4 eval(float3 pos)
    {
        float3 d = pos - this.position;
        float3x3 invCov = this.invCovarianceMatrix();
        float rho = exp(-dot(d, mul(invCov, d)));
        float alpha = rho * this.opacitySigmoid();
        // TODO: Implement spherical harmonics.
        return float4(this.colorSigmoid(), alpha);
    }

    public BoundingBox boundingBox()
    {
        return this.boundingBox(2.0); // 2 standard deviations.
    }

    public BoundingBox boundingBox(float nStdDev)
    {
        float3 scale = this.scaleExp() * nStdDev;
        // Calculate the bounding box based on six endpoints.
        float3 extents[6] = {
            float3(scale.x, 0.0, 0.0),
            float3(-scale.x, 0.0, 0.0),
            float3(0.0, scale.y, 0.0),
            float3(0.0, -scale.y, 0.0),
            float3(0.0, 0.0, scale.z),
            float3(0.0, 0.0, -scale.z)
        };
        float3 pMin = this.position;
        float3 pMax = this.position;
        [ForceUnroll]
        for (int i = 0; i < 6; ++i)
        {
            float3 endpoint = this.position + quat.rotate(this.rotation, extents[i]);
            pMin = min(pMin, endpoint);
            pMax = max(pMax, endpoint);
        }
        return BoundingBox(pMin, pMax);
    }

    // Finidng \tau_{max} = argmax_{\tau} \rho (o + \tau d) based on https://arxiv.org/abs/2407.07090
    public float maxResponse(Ray ray)
    {
        float3 scale = this.scaleExp();
        float3x3 invS = float3x3(
            float3(1 / scale.x, 0.0, 0.0),
            float3(0.0, 1 / scale.y, 0.0),
            float3(0.0, 0.0, 1 / scale.z));
        float3x3 transR = linalg.transpose(quat.asRotMat(this.rotation));
        float3 og = mul(invS, mul(transR, ray.origin - this.position));
        float3 dg = mul(invS, mul(transR, ray.direction));
        return -dot(og, dg) / dot(dg, dg);
    }
};

// Gaussian splat in struct of array format.
public struct SOAGaussianSplat
{
    public StructuredBuffer<float3> position;
    public StructuredBuffer<float4> rotation;
    public StructuredBuffer<float3> scale;
    public StructuredBuffer<float3> color;
    public StructuredBuffer<float> opacity;
}

// Unpack gaussian splat from struct of array format to Gaussian buffer.
public void unpackGaussianSplat(
    uint tid,
    SOAGaussianSplat soaSplat,
    RWStructuredBuffer<Gaussian> gaussians)
{
    uint idx = tid;
    gaussians[idx] = Gaussian(
        soaSplat.position[idx],
        soaSplat.rotation[idx],
        soaSplat.scale[idx],
        soaSplat.color[idx],
        soaSplat.opacity[idx]);
}
