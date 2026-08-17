from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from hangar_cv_optimizer.collision.checker import DEFAULT_CLEARANCE_M, CollisionReport, check_collisions
from hangar_cv_optimizer.cv.detector import DEFAULT_CONFIDENCE_THRESHOLD, detect_aircraft
from hangar_cv_optimizer.cv.models import DetectionResult
from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary
from hangar_cv_optimizer.optimization.models import PlaceableAircraft, PlacementResult
from hangar_cv_optimizer.optimization.service import optimize_layout

app = FastAPI(
    title="Hangar CV Optimizer",
    description="Aircraft positioning, hangar space optimization, and collision detection.",
    version="0.1.0",
)


class CollisionCheckRequest(BaseModel):
    hangar: HangarBoundary
    aircraft: list[AircraftFootprint]
    clearance_m: float = DEFAULT_CLEARANCE_M


class OptimizeLayoutRequest(BaseModel):
    hangar: HangarBoundary
    aircraft: list[PlaceableAircraft]
    clearance_m: float = DEFAULT_CLEARANCE_M
    grid_step_m: float = 2.0
    iterations: int = 150
    seed: int | None = None


class OptimizeLayoutResponse(BaseModel):
    result: PlacementResult
    collision_report: CollisionReport
    """Post-hoc validation of the solver's own output. Should always be
    clear by construction (the greedy placer enforces clearance), but is
    run and returned so a client never has to trust the solver blindly."""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check-collision", response_model=CollisionReport)
def check_collision_endpoint(request: CollisionCheckRequest) -> CollisionReport:
    return check_collisions(request.aircraft, request.hangar, clearance_m=request.clearance_m)


@app.post("/detect", response_model=DetectionResult)
async def detect_endpoint(
    file: UploadFile = File(...),
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> DetectionResult:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    try:
        return detect_aircraft(image_bytes, confidence_threshold=confidence_threshold)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/optimize-layout", response_model=OptimizeLayoutResponse)
def optimize_layout_endpoint(request: OptimizeLayoutRequest) -> OptimizeLayoutResponse:
    result = optimize_layout(
        request.aircraft,
        request.hangar,
        clearance_m=request.clearance_m,
        grid_step_m=request.grid_step_m,
        iterations=request.iterations,
        seed=request.seed,
    )
    collision_report = check_collisions(result.placed, request.hangar, clearance_m=request.clearance_m)
    return OptimizeLayoutResponse(result=result, collision_report=collision_report)
