using System.Text.Json.Serialization;

namespace HangarDashboard.Models;

// Mirrors hangar_cv_optimizer.geometry.models / collision.checker /
// optimization.models / cv.models (Python, Pydantic) so the JSON contract
// stays in sync by inspection. Explicit JsonPropertyName on every field
// rather than relying on a snake_case naming policy - avoids ambiguity on
// names like XMin/YMax where automatic word-splitting is easy to get wrong.

public record Point(
    [property: JsonPropertyName("x")] double X,
    [property: JsonPropertyName("y")] double Y
);

public record HangarBoundary(
    [property: JsonPropertyName("vertices")] List<Point> Vertices,
    [property: JsonPropertyName("obstacles")] List<List<Point>> Obstacles
);

public record AircraftFootprint(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("wingspan_m")] double WingspanM,
    [property: JsonPropertyName("length_m")] double LengthM,
    [property: JsonPropertyName("center")] Point Center,
    [property: JsonPropertyName("rotation_deg")] double RotationDeg
);

public record PlaceableAircraft(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("wingspan_m")] double WingspanM,
    [property: JsonPropertyName("length_m")] double LengthM
);

public record Violation(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("aircraft_ids")] List<string> AircraftIds,
    [property: JsonPropertyName("detail")] string Detail,
    [property: JsonPropertyName("distance_m")] double? DistanceM
);

public record CollisionReport(
    [property: JsonPropertyName("is_clear")] bool IsClear,
    [property: JsonPropertyName("violations")] List<Violation> Violations
);

public record PlacementResult(
    [property: JsonPropertyName("placed")] List<AircraftFootprint> Placed,
    [property: JsonPropertyName("unplaced_ids")] List<string> UnplacedIds,
    [property: JsonPropertyName("utilization")] double Utilization
);

public record OptimizeLayoutRequest(
    [property: JsonPropertyName("hangar")] HangarBoundary Hangar,
    [property: JsonPropertyName("aircraft")] List<PlaceableAircraft> Aircraft,
    [property: JsonPropertyName("clearance_m")] double ClearanceM,
    [property: JsonPropertyName("grid_step_m")] double GridStepM,
    [property: JsonPropertyName("iterations")] int Iterations,
    [property: JsonPropertyName("seed")] int? Seed
);

public record OptimizeLayoutResponse(
    [property: JsonPropertyName("result")] PlacementResult Result,
    [property: JsonPropertyName("collision_report")] CollisionReport CollisionReport
);

public record Detection(
    [property: JsonPropertyName("class_name")] string ClassName,
    [property: JsonPropertyName("confidence")] double Confidence,
    [property: JsonPropertyName("x_min")] double XMin,
    [property: JsonPropertyName("y_min")] double YMin,
    [property: JsonPropertyName("x_max")] double XMax,
    [property: JsonPropertyName("y_max")] double YMax
);

public record DetectionResult(
    [property: JsonPropertyName("image_width")] int ImageWidth,
    [property: JsonPropertyName("image_height")] int ImageHeight,
    [property: JsonPropertyName("detections")] List<Detection> Detections
);
