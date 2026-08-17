using System.Net.Http.Json;
using HangarDashboard.Models;

namespace HangarDashboard.Services;

/// <summary>
/// Thin typed wrapper around the Python (FastAPI) backend. Deliberately
/// contains no business logic of its own - collision/optimization/detection
/// all live in hangar_cv_optimizer; this is purely a REST consumer, mirroring
/// how Starlight Hangars' own Blazor product likely talks to whatever
/// service layer does the heavy lifting.
/// </summary>
public class HangarApiClient(HttpClient httpClient)
{
    public async Task<OptimizeLayoutResponse> OptimizeLayoutAsync(OptimizeLayoutRequest request, CancellationToken ct = default)
    {
        var response = await httpClient.PostAsJsonAsync("/optimize-layout", request, ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<OptimizeLayoutResponse>(cancellationToken: ct))!;
    }

    public async Task<CollisionReport> CheckCollisionAsync(HangarBoundary hangar, List<AircraftFootprint> aircraft, double clearanceM, CancellationToken ct = default)
    {
        var payload = new { hangar, aircraft, clearance_m = clearanceM };
        var response = await httpClient.PostAsJsonAsync("/check-collision", payload, ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<CollisionReport>(cancellationToken: ct))!;
    }

    public async Task<DetectionResult> DetectAsync(byte[] imageBytes, string fileName, double confidenceThreshold = 0.25, CancellationToken ct = default)
    {
        using var content = new MultipartFormDataContent();
        using var imageContent = new ByteArrayContent(imageBytes);
        imageContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");
        content.Add(imageContent, "file", fileName);

        var response = await httpClient.PostAsync($"/detect?confidence_threshold={confidenceThreshold}", content, ct);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<DetectionResult>(cancellationToken: ct))!;
    }
}
