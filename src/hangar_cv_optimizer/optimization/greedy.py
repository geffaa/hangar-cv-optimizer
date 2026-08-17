from __future__ import annotations

from shapely.geometry import Polygon

from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary, Point
from hangar_cv_optimizer.optimization.models import PlaceableAircraft

ROTATIONS_DEG = (0.0, 90.0)


def greedy_place(
    order: list[PlaceableAircraft],
    hangar: HangarBoundary,
    clearance_m: float,
    grid_step_m: float = 2.0,
) -> list[AircraftFootprint]:
    """Bottom-left-ish first-fit placement.

    Scans a grid of candidate center points (in placement order, one aircraft
    at a time) and places each aircraft at the first position/rotation where
    its footprint fits fully inside the hangar boundary, avoids obstacles,
    and keeps at least `clearance_m` distance from every already-placed
    aircraft. Aircraft that don't fit anywhere are skipped (left unplaced).
    """
    boundary_poly = hangar.to_polygon()
    obstacle_polys = [Polygon([(p.x, p.y) for p in obs]) for obs in hangar.obstacles]

    min_x, min_y, max_x, max_y = boundary_poly.bounds

    placed: list[AircraftFootprint] = []
    placed_polys: list[Polygon] = []

    for aircraft in order:
        candidate = _find_first_fit(
            aircraft,
            boundary_poly,
            obstacle_polys,
            placed_polys,
            clearance_m,
            min_x,
            min_y,
            max_x,
            max_y,
            grid_step_m,
        )
        if candidate is not None:
            placed.append(candidate)
            placed_polys.append(candidate.to_polygon())

    return placed


def _find_first_fit(
    aircraft: PlaceableAircraft,
    boundary_poly: Polygon,
    obstacle_polys: list[Polygon],
    placed_polys: list[Polygon],
    clearance_m: float,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    grid_step_m: float,
) -> AircraftFootprint | None:
    y = min_y
    while y <= max_y:
        x = min_x
        while x <= max_x:
            for rotation in ROTATIONS_DEG:
                footprint = AircraftFootprint(
                    id=aircraft.id,
                    label=aircraft.label,
                    wingspan_m=aircraft.wingspan_m,
                    length_m=aircraft.length_m,
                    center=Point(x=x, y=y),
                    rotation_deg=rotation,
                )
                poly = footprint.to_polygon()

                if not boundary_poly.contains(poly):
                    continue
                if any(poly.intersects(obs) for obs in obstacle_polys):
                    continue
                if any(poly.distance(other) < clearance_m for other in placed_polys):
                    continue

                return footprint
            x += grid_step_m
        y += grid_step_m
    return None
