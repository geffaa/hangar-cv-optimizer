from __future__ import annotations

from hangar_cv_optimizer.geometry.models import HangarBoundary
from hangar_cv_optimizer.optimization.annealing import anneal_layout
from hangar_cv_optimizer.optimization.models import PlaceableAircraft, PlacementResult


def optimize_layout(
    aircraft: list[PlaceableAircraft],
    hangar: HangarBoundary,
    clearance_m: float,
    grid_step_m: float = 2.0,
    iterations: int = 150,
    seed: int | None = None,
) -> PlacementResult:
    placed = anneal_layout(
        aircraft,
        hangar,
        clearance_m,
        grid_step_m=grid_step_m,
        iterations=iterations,
        seed=seed,
    )

    placed_ids = {a.id for a in placed}
    unplaced_ids = [a.id for a in aircraft if a.id not in placed_ids]

    hangar_area = hangar.to_polygon().area
    placed_area = sum(a.to_polygon().area for a in placed)
    utilization = placed_area / hangar_area if hangar_area > 0 else 0.0

    return PlacementResult(placed=placed, unplaced_ids=unplaced_ids, utilization=utilization)
