using System.Globalization;

namespace HangarDashboard.Services;

/// <summary>
/// SVG attribute values must use "." as the decimal separator regardless of
/// server locale. Razor's default @value interpolation calls ToString()
/// under the *current* culture - on a server running under an id-ID (or any
/// comma-decimal) locale, that renders e.g. "617,37" instead of "617.37",
/// which browsers reject as an invalid SVG length. Every numeric value
/// interpolated into SVG markup must go through this helper instead of
/// being written directly as @someDouble.
/// </summary>
public static class InvariantFormat
{
    public static string Inv(this double value) => value.ToString(CultureInfo.InvariantCulture);
}
