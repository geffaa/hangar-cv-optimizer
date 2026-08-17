from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hangar_cv_optimizer.api.main import app
from hangar_cv_optimizer.cv.detector import _resolve_model_path

TEST_IMAGES_DIR = Path(__file__).resolve().parents[2] / "data" / "yolo" / "images" / "test"

MODEL_AVAILABLE = _resolve_model_path().exists()
SAMPLE_IMAGES_AVAILABLE = TEST_IMAGES_DIR.is_dir() and any(TEST_IMAGES_DIR.iterdir())

client = TestClient(app)


def test_detect_endpoint_rejects_empty_file():
    response = client.post("/detect", files={"file": ("empty.jpg", b"", "image/jpeg")})
    assert response.status_code == 422


@pytest.mark.skipif(
    not (MODEL_AVAILABLE and SAMPLE_IMAGES_AVAILABLE),
    reason="Trained weights and/or dataset images not present locally (both are gitignored)",
)
def test_detect_endpoint_returns_detections_for_real_image():
    image_path = next(iter(sorted(TEST_IMAGES_DIR.iterdir())))

    with image_path.open("rb") as f:
        response = client.post("/detect", files={"file": (image_path.name, f, "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert body["image_width"] > 0
    assert len(body["detections"]) > 0
    assert all(d["class_name"] == "Airplane" for d in body["detections"])


def test_detect_endpoint_503_when_model_missing(monkeypatch):
    monkeypatch.setenv("HANGAR_CV_MODEL_PATH", "/nonexistent/weights.pt")
    from hangar_cv_optimizer.cv import detector

    detector._load_model.cache_clear()

    with _dummy_image() as f:
        response = client.post("/detect", files={"file": ("x.jpg", f, "image/jpeg")})

    detector._load_model.cache_clear()
    assert response.status_code == 503


def _dummy_image():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color="white").save(buf, format="JPEG")
    buf.seek(0)
    return buf
