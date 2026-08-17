"""Tests for the aircraft detector.

These depend on artifacts that are intentionally gitignored (trained
weights under runs/, dataset images under data/) since they're large
binaries reproducible via scripts/prepare_yolo_dataset.py + `yolo detect
train` (see docs/experiments/EXPERIMENTS.md). On a fresh clone without
those artifacts, these tests skip rather than fail, so `pytest` stays
green for anyone just checking out the collision/optimization services.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hangar_cv_optimizer.cv.detector import _resolve_model_path, detect_aircraft

TEST_IMAGES_DIR = Path(__file__).resolve().parents[2] / "data" / "yolo" / "images" / "test"

MODEL_AVAILABLE = _resolve_model_path().exists()
SAMPLE_IMAGES_AVAILABLE = TEST_IMAGES_DIR.is_dir() and any(TEST_IMAGES_DIR.iterdir())

pytestmark = pytest.mark.skipif(
    not (MODEL_AVAILABLE and SAMPLE_IMAGES_AVAILABLE),
    reason="Trained weights and/or dataset images not present locally (both are gitignored)",
)


def _first_sample_image_bytes() -> bytes:
    image_path = next(iter(sorted(TEST_IMAGES_DIR.iterdir())))
    return image_path.read_bytes()


def test_detect_aircraft_returns_detections_for_known_image():
    image_bytes = _first_sample_image_bytes()

    result = detect_aircraft(image_bytes, confidence_threshold=0.25)

    assert result.image_width > 0
    assert result.image_height > 0
    assert len(result.detections) > 0


def test_detections_have_valid_bounding_boxes_within_image():
    image_bytes = _first_sample_image_bytes()

    result = detect_aircraft(image_bytes, confidence_threshold=0.25)

    for det in result.detections:
        assert 0 <= det.x_min < det.x_max <= result.image_width
        assert 0 <= det.y_min < det.y_max <= result.image_height
        assert 0.0 <= det.confidence <= 1.0
        assert det.class_name == "Airplane"


def test_higher_confidence_threshold_yields_fewer_or_equal_detections():
    image_bytes = _first_sample_image_bytes()

    loose = detect_aircraft(image_bytes, confidence_threshold=0.1)
    strict = detect_aircraft(image_bytes, confidence_threshold=0.9)

    assert len(strict.detections) <= len(loose.detections)
