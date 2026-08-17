from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image

from hangar_cv_optimizer.cv.models import Detection, DetectionResult

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MODEL_PATH = REPO_ROOT / "runs" / "detect" / "runs" / "aircraft_merged" / "weights" / "best.pt"
"""Points at the v2 (single-class, merged) run - see docs/experiments/EXPERIMENTS.md.
Override via the HANGAR_CV_MODEL_PATH env var to point at a different run
(e.g. a future v3 tiling/yolov8s checkpoint) without touching this code."""

DEFAULT_CONFIDENCE_THRESHOLD = 0.25


def _resolve_model_path() -> Path:
    override = os.environ.get("HANGAR_CV_MODEL_PATH")
    return Path(override) if override else DEFAULT_MODEL_PATH


@lru_cache(maxsize=1)
def _load_model(model_path: str):
    from ultralytics import YOLO

    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"Aircraft detection weights not found at {model_path}. "
            "Train a model first (see docs/experiments/EXPERIMENTS.md) or set "
            "the HANGAR_CV_MODEL_PATH env var to an existing .pt file."
        )
    return YOLO(model_path)


def detect_aircraft(
    image_bytes: bytes,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> DetectionResult:
    model = _load_model(str(_resolve_model_path()))

    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        width, height = image.size

        results = model.predict(image, conf=confidence_threshold, verbose=False)

    result = results[0]
    names = result.names

    detections = [
        Detection(
            class_name=names[int(box.cls.item())],
            confidence=float(box.conf.item()),
            x_min=float(box.xyxy[0][0]),
            y_min=float(box.xyxy[0][1]),
            x_max=float(box.xyxy[0][2]),
            y_max=float(box.xyxy[0][3]),
        )
        for box in result.boxes
    ]

    return DetectionResult(image_width=width, image_height=height, detections=detections)
