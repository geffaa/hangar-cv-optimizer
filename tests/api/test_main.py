from fastapi.testclient import TestClient

from hangar_cv_optimizer.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_check_collision_endpoint_clear():
    payload = {
        "hangar": {
            "vertices": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 60},
                {"x": 0, "y": 60},
            ],
            "obstacles": [],
        },
        "aircraft": [
            {"id": "a1", "wingspan_m": 10, "length_m": 12, "center": {"x": 20, "y": 20}},
            {"id": "a2", "wingspan_m": 10, "length_m": 12, "center": {"x": 70, "y": 20}},
        ],
    }

    response = client.post("/check-collision", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["is_clear"] is True
    assert body["violations"] == []


def test_check_collision_endpoint_overlap():
    payload = {
        "hangar": {
            "vertices": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 60},
                {"x": 0, "y": 60},
            ],
            "obstacles": [],
        },
        "aircraft": [
            {"id": "a1", "wingspan_m": 10, "length_m": 12, "center": {"x": 30, "y": 30}},
            {"id": "a2", "wingspan_m": 10, "length_m": 12, "center": {"x": 32, "y": 30}},
        ],
    }

    response = client.post("/check-collision", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["is_clear"] is False
    assert body["violations"][0]["type"] == "aircraft_overlap"


def test_check_collision_endpoint_invalid_payload():
    response = client.post("/check-collision", json={"hangar": {"vertices": []}, "aircraft": []})
    assert response.status_code == 422
