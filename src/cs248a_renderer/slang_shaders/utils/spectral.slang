implementing "../utils.slang";

// CIE 1931 2-degree standard observer color matching functions.
// 81 samples from 380 nm to 780 nm in 5 nm steps.
// Source: CIE 15:2004 tables.

static const uint CIE_TABLE_SIZE = 81;
static const float CIE_LAMBDA_MIN = 380.0;
static const float CIE_LAMBDA_MAX = 780.0;
static const float CIE_LAMBDA_STEP = 5.0;

// x-bar color matching function
static float cie_x_bar(uint i)
{
    static const float table[81] = {
        0.0014, 0.0022, 0.0042, 0.0076, 0.0143,
        0.0232, 0.0435, 0.0776, 0.1344, 0.2148,
        0.2839, 0.3285, 0.3483, 0.3481, 0.3362,
        0.3187, 0.2908, 0.2511, 0.1954, 0.1421,
        0.0956, 0.0580, 0.0320, 0.0147, 0.0049,
        0.0024, 0.0093, 0.0291, 0.0633, 0.1096,
        0.1655, 0.2257, 0.2904, 0.3597, 0.4334,
        0.5121, 0.5945, 0.6784, 0.7621, 0.8425,
        0.9163, 0.9786, 1.0263, 1.0567, 1.0622,
        1.0456, 1.0026, 0.9384, 0.8544, 0.7514,
        0.6424, 0.5419, 0.4479, 0.3608, 0.2835,
        0.2187, 0.1649, 0.1212, 0.0874, 0.0636,
        0.0468, 0.0329, 0.0227, 0.0158, 0.0114,
        0.0081, 0.0058, 0.0041, 0.0029, 0.0020,
        0.0014, 0.0010, 0.0007, 0.0005, 0.0003,
        0.0002, 0.0002, 0.0001, 0.0001, 0.0001,
        0.0000
    };
    return table[min(i, 80)];
}

// y-bar color matching function (luminous efficiency)
static float cie_y_bar(uint i)
{
    static const float table[81] = {
        0.0000, 0.0001, 0.0001, 0.0002, 0.0004,
        0.0006, 0.0012, 0.0022, 0.0040, 0.0073,
        0.0116, 0.0168, 0.0230, 0.0298, 0.0380,
        0.0480, 0.0600, 0.0739, 0.0910, 0.1126,
        0.1390, 0.1693, 0.2080, 0.2586, 0.3230,
        0.4073, 0.5030, 0.6082, 0.7100, 0.7932,
        0.8620, 0.9149, 0.9540, 0.9803, 0.9950,
        1.0000, 0.9950, 0.9786, 0.9520, 0.9154,
        0.8700, 0.8163, 0.7570, 0.6949, 0.6310,
        0.5668, 0.5030, 0.4412, 0.3810, 0.3210,
        0.2650, 0.2170, 0.1750, 0.1382, 0.1070,
        0.0816, 0.0610, 0.0446, 0.0320, 0.0232,
        0.0170, 0.0119, 0.0082, 0.0057, 0.0041,
        0.0029, 0.0021, 0.0015, 0.0010, 0.0007,
        0.0005, 0.0004, 0.0002, 0.0002, 0.0001,
        0.0001, 0.0001, 0.0000, 0.0000, 0.0000,
        0.0000
    };
    return table[min(i, 80)];
}

// z-bar color matching function
static float cie_z_bar(uint i)
{
    static const float table[81] = {
        0.0065, 0.0105, 0.0201, 0.0362, 0.0679,
        0.1102, 0.2074, 0.3713, 0.6456, 1.0391,
        1.3856, 1.6230, 1.7471, 1.7826, 1.7721,
        1.7441, 1.6692, 1.5281, 1.2876, 1.0419,
        0.8130, 0.6162, 0.4652, 0.3533, 0.2720,
        0.2123, 0.1582, 0.1117, 0.0782, 0.0573,
        0.0422, 0.0298, 0.0203, 0.0134, 0.0087,
        0.0057, 0.0039, 0.0027, 0.0021, 0.0018,
        0.0017, 0.0014, 0.0011, 0.0010, 0.0008,
        0.0006, 0.0003, 0.0002, 0.0002, 0.0001,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
        0.0000
    };
    return table[min(i, 80)];
}

// Convert a single wavelength (in nm) to CIE XYZ tristimulus values
// using linear interpolation of the tabulated color matching functions.
public float3 wavelength_to_XYZ(float wavelength_nm)
{
    float t = (wavelength_nm - CIE_LAMBDA_MIN) / CIE_LAMBDA_STEP;
    // Clamp to valid table range
    t = clamp(t, 0.0, float(CIE_TABLE_SIZE - 2));
    uint i = uint(t);
    float frac = t - float(i);

    float x = lerp(cie_x_bar(i), cie_x_bar(i + 1), frac);
    float y = lerp(cie_y_bar(i), cie_y_bar(i + 1), frac);
    float z = lerp(cie_z_bar(i), cie_z_bar(i + 1), frac);

    return float3(x, y, z);
}

// Convert CIE XYZ to linear sRGB using the standard IEC 61966-2-1 matrix
// (D65 illuminant, 2-degree observer).
public float3 XYZ_to_linear_sRGB(float3 xyz)
{
    float3 rgb;
    rgb.x =  3.2406255 * xyz.x - 1.5372080 * xyz.y - 0.4986286 * xyz.z;
    rgb.y = -0.9689307 * xyz.x + 1.8757561 * xyz.y + 0.0415175 * xyz.z;
    rgb.z =  0.0557101 * xyz.x - 0.2040211 * xyz.y + 1.0569959 * xyz.z;
    return rgb;
}

// Convert a wavelength to a linear sRGB color suitable for framebuffer accumulation.
// The result is NOT clamped — negative values can occur for highly saturated spectral
// colors and are expected to cancel out during Monte Carlo integration over many samples.
public float3 wavelength_to_sRGB(float wavelength_nm)
{
    float3 xyz = wavelength_to_XYZ(wavelength_nm);
    return XYZ_to_linear_sRGB(xyz);
}
