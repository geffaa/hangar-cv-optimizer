from __future__ import annotations

from pydantic import BaseModel


class Detection(BaseModel):
    """A single detected aircraft, in *pixel* coordinates of the source image.

    Pixel coordinates, not meters: the detector has no notion of ground
    sample distance (GSD) or camera calibration for an arbitrary uploaded
    image, so it cannot know how many pixels correspond to one meter.
    Converting a Detection into an AircraftFootprint (which is metric,
    consumed by the optimization/collision services) requires an externally
    supplied pixels_per_meter scale - see DetectionResult.to_footprints().
    """

    class_name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectionResult(BaseModel):
    image_width: int
    image_height: int
    detections: list[Detection]
