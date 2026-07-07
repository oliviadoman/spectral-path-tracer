implementing "../texture.slang";

public struct SharedTexture2DBuffer<T>
    where T : IFloat
{
    public StructuredBuffer<T> buffer;

    T getBufferValue(SharedTexture2D tex, uint2 texelCoord)
    {
        uint2 texSize = tex.size;
        uint offset = tex.offset;
        uint index = texelCoord.y * texSize.x + texelCoord.x;
        return buffer[offset + index];
    }

    public T pointSample(SharedTexture2D tex, float2 uv)
    {
        T outV = T(0.0);
        // TODO: Student implementation starts here.

        int w = int(tex.size.x);
        int h = int(tex.size.y);

        float2 clampUV = clamp(uv, float2(0.0), float2(1.0));

        float x = clampUV.x * float(w) - 0.5;
        float y = clampUV.y * float(h) - 0.5;

        // nearest neighbor
        int ix = (int)floor(x);
        int iy = (int)floor(y);

        ix = clamp(ix, 0, w - 1);
        iy = clamp(iy, 0, h - 1);
        outV = getBufferValue(tex, uint2((uint)ix, (uint)iy));

        // TODO: Student implementation ends here.
        return outV;
    }

    public T bilinearSample(SharedTexture2D tex, float2 uv)
    {
        T outV = T(0.0);
        // TODO: Student implementation starts here.

        int w = int(tex.size.x);
        int h = int(tex.size.y);

        float2 clampUV = clamp(uv, float2(0.0), float2(1.0));

        float x = clampUV.x * float(w) - 0.5;
        float y = clampUV.y * float(h) - 0.5;

        // neighboring pixel coords 
        int ix = (int)floor(x);
        int iy = (int)floor(y);

        // clamp neighbors 
        int ix0 = clamp(ix, 0, w - 1);
        int ix1 = clamp(ix + 1, 0, w - 1);

        int iy0 = clamp(iy, 0, h - 1);
        int iy1 = clamp(iy + 1, 0, h - 1);

        float tX = x - float(ix0);
        float tY = y - float(iy0);

        // get neighboring texels
        T c00 = getBufferValue(tex, uint2((uint)ix0, (uint)iy0));
        T c10 = getBufferValue(tex, uint2((uint)ix1, (uint)iy0));
        T c01 = getBufferValue(tex, uint2((uint)ix0, (uint)iy1));
        T c11 = getBufferValue(tex, uint2((uint)ix1, (uint)iy1));

        T c0 = c00 * T(1.0 - tX) + c10 * T(tX); // bottom
        T c1 = c01 * T(1.0 - tX) + c11 * T(tX); // top

        outV = c0 * T(1.0 - tY) + c1 * T(tY); // top and bottom

        // TODO: Student implementation ends here.
        return outV;
    }

    public T trilinearSample(SharedTexture2D[] mipmapLevels, float2 uv, float d, uint totalLevels)
    {
        T outV = T(0.0);
        // TODO: Student implementation starts here.

        uint level0 = (uint)floor(d);
        uint level1 = min(level0 + 1, totalLevels - 1);
        float t = d - float(level0);
        T c0 = bilinearSample(mipmapLevels[level0], uv);
        T c1 = bilinearSample(mipmapLevels[level1], uv);
        outV = c0 * T(1.0 - t) + c1 * T(t);


        // TODO: Student implementation ends here.
        return outV;
    }
}

public struct SharedTexture2D
{
    public uint2 size;
    public uint offset;
}

public struct SharedTexture3DBuffer<T>
    where T : IFloat
{
    public StructuredBuffer<T> buffer;

    T getBufferValue(SharedTexture3D tex, uint3 voxelCoord)
    {
        uint3 texSize = tex.size;
        uint offset = tex.offset;
        uint index = voxelCoord.z * texSize.y * texSize.x +
                     voxelCoord.y * texSize.x +
                     voxelCoord.x;
        return buffer[offset + index];
    }

    /**
     * Sample the texture at the given uvw coordinates using nearest neighbor interpolation.
     * @param tex The texture to sample.
     * @param uvw The uvw coordinates to sample the texture at.
     * @return The sampled value.
     */
    public T pointSample(SharedTexture3D tex, float3 uvw)
    {
        // TODO: Student implementation starts here.
        uint3 size = tex.size;
        float3 u = clamp(uvw, float3(0.0), float3(1.0));
        float3 p = u * (float3(size) - 1.0);

        uint ix = (uint)round(p.x);
        uint iy = (uint)round(p.y);
        uint iz = (uint)round(p.z);

        ix = min(ix, size.x - 1);
        iy = min(iy, size.y - 1);
        iz = min(iz, size.z - 1);        
        
        return getBufferValue(tex, uint3(ix, iy, iz));

        // TODO: Student implementation ends here.
    }

    /**
     * Sample the texture at the given uvw coordinates using trilinear interpolation.
     * @param tex The texture to sample.
     * @param uvw The uvw coordinates to sample the texture at.
     * @return The sampled value.
     **/
    public T trilinearSample(SharedTexture3D tex, float3 uvw)
    {
        // TODO: Student implementation starts here.
        uint3 size = tex.size;

        float3 u = clamp(uvw, float3(0.0), float3(1.0));
        float3 p = u * (float3(size) - 1.0);

        int x0 = (int)floor(p.x);
        int y0 = (int)floor(p.y);
        int z0 = (int)floor(p.z);

        int x1 = x0 + 1;
        int y1 = y0 + 1;
        int z1 = z0 + 1;

        // clamp indices to valid
        x0 = clamp(x0, 0, (int)(size.x - 1));
        y0 = clamp(y0, 0, (int)(size.y - 1));
        z0 = clamp(z0, 0, (int)(size.z - 1));
        x1 = clamp(x1, 0, (int)(size.x - 1));
        y1 = clamp(y1, 0, (int)(size.y - 1));
        z1 = clamp(z1, 0, (int)(size.z - 1));

        float3 f = frac(p);

        // Get 8 corner samples 
        T c000 = getBufferValue(tex, uint3((uint)x0, (uint)y0, (uint)z0));
        T c100 = getBufferValue(tex, uint3((uint)x1, (uint)y0, (uint)z0));
        T c010 = getBufferValue(tex, uint3((uint)x0, (uint)y1, (uint)z0));
        T c110 = getBufferValue(tex, uint3((uint)x1, (uint)y1, (uint)z0));

        T c001 = getBufferValue(tex, uint3((uint)x0, (uint)y0, (uint)z1));
        T c101 = getBufferValue(tex, uint3((uint)x1, (uint)y0, (uint)z1));
        T c011 = getBufferValue(tex, uint3((uint)x0, (uint)y1, (uint)z1));
        T c111 = getBufferValue(tex, uint3((uint)x1, (uint)y1, (uint)z1));

        // Interpolate along x, y, anf then z
        T c00 = (T(1.0) - T(f.x)) * c000 + T(f.x) * c100;
        T c10 = (T(1.0) - T(f.x)) * c010 + T(f.x) * c110;
        T c01 = (T(1.0) - T(f.x)) * c001 + T(f.x) * c101;
        T c11 = (T(1.0) - T(f.x)) * c011 + T(f.x) * c111;

        T c0 = (T(1.0) - T(f.y)) * c00 + T(f.y) * c10;
        T c1 =  (T(1.0) - T(f.y)) * c01 + T(f.y) * c11;

        return (T(1.0) - T(f.z)) * c0 + T(f.z) * c1;

        // TODO: Student implementation ends here.
    }
}

public struct SharedTexture3D
{
    public uint3 size;
    public uint offset;
}

