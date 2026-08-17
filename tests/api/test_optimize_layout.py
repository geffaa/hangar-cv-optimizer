from fastapi.testclient import TestClient

from hangar_cv_optimizer.api.main import app

client = TestClient(app)


def test_optimize_layout_endpoint():
    payload = {
        "hangar": {
            "vertices": [
                {"x": 0, "y": 0},
                {"x": 80, "y": 0},
                {"x": 80, "y": 80},
                {"x": 0, "y": 80},
            ],
            "obstacles": [],
        },
        "aircraft": [
            {"id": f"a{i}", "wingspan_m": 8, "length_m": 10} for i in range(6)
        ],
        "clearance_m": 3.0,
        "iterations": 20,
        "seed": 1,
    }

    response = client.post("/optimize-layout", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["collision_report"]["is_clear"] is True
    assert 0.0 <= body["result"]["utilization"] <= 1.0
    placed_and_unplaced = {a["id"] for a in body["result"]["placed"]} | set(body["result"]["unplaced_ids"])
    assert placed_and_unplaced == {f"a{i}" for i in range(6)}
