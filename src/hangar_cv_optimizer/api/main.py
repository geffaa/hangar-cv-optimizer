from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from hangar_cv_optimizer.collision.checker import DEFAULT_CLEARANCE_M, CollisionReport, check_collisions
from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary

app = FastAPI(
    title="Hangar CV Optimizer",
    description="Aircraft positioning, hangar space optimization, and collision detection.",
    version="0.1.0",
)


class CollisionCheckRequest(BaseModel):
    hangar: HangarBoundary
    aircraft: list[AircraftFootprint]
    clearance_m: float = DEFAULT_CLEARANCE_M


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check-collision", response_model=CollisionReport)
def check_collision_endpoint(request: CollisionCheckRequest) -> CollisionReport:
    return check_collisions(request.aircraft, request.hangar, clearance_m=request.clearance_m)
