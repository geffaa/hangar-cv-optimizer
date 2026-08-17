from __future__ import annotations

from enum import Enum
from itertools import combinations

from pydantic import BaseModel

from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary

DEFAULT_CLEARANCE_M = 3.0
"""Minimum wingtip-to-wingtip / wingtip-to-obstacle clearance.

Conservative default based on general FAA/ICAO taxiway & apron wingtip
clearance guidance for small-to-midsize GA aircraft. Real deployments
should configure this per hangar/aircraft category rather than relying
on the default.
"""


class ViolationType(str, Enum):
    AIRCRAFT_OVERLAP = "aircraft_overlap"
    CLEARANCE_BREACH = "clearance_breach"
    OUTSIDE_BOUNDARY = "outside_boundary"
    OBSTACLE_OVERLAP = "obstacle_overlap"


class Violation(BaseModel):
    type: ViolationType
    aircraft_ids: list[str]
    detail: str
    distance_m: float | None = None


class CollisionReport(BaseModel):
    is_clear: bool
    violations: list[Violation]


def check_collisions(
    aircraft: list[AircraftFootprint],
    hangar: HangarBoundary,
    clearance_m: float = DEFAULT_CLEARANCE_M,
) -> CollisionReport:
    violations: list[Violation] = []

    boundary_poly = hangar.to_polygon()
    footprints = {a.id: a.to_polygon() for a in aircraft}

    for aircraft_id, poly in footprints.items():
        if not boundary_poly.contains(poly):
            violations.append(
                Violation(
                    type=ViolationType.OUTSIDE_BOUNDARY,
                    aircraft_ids=[aircraft_id],
                    detail=f"Aircraft '{aircraft_id}' footprint is not fully within the hangar boundary",
                )
            )

    for obstacle_vertices in hangar.obstacles:
        from shapely.geometry import Polygon as ShapelyPolygon

        obstacle_poly = ShapelyPolygon([(p.x, p.y) for p in obstacle_vertices])
        for aircraft_id, poly in footprints.items():
            if poly.intersects(obstacle_poly):
                violations.append(
                    Violation(
                        type=ViolationType.OBSTACLE_OVERLAP,
                        aircraft_ids=[aircraft_id],
                        detail=f"Aircraft '{aircraft_id}' overlaps a hangar obstacle",
                    )
                )

    for id_a, id_b in combinations(footprints.keys(), 2):
        poly_a, poly_b = footprints[id_a], footprints[id_b]

        if poly_a.intersects(poly_b):
            violations.append(
                Violation(
                    type=ViolationType.AIRCRAFT_OVERLAP,
                    aircraft_ids=[id_a, id_b],
                    detail=f"Aircraft '{id_a}' and '{id_b}' footprints overlap",
                    distance_m=0.0,
                )
            )
            continue

        distance = poly_a.distance(poly_b)
        if distance < clearance_m:
            violations.append(
                Violation(
                    type=ViolationType.CLEARANCE_BREACH,
                    aircraft_ids=[id_a, id_b],
                    detail=(
                        f"Clearance between '{id_a}' and '{id_b}' is {distance:.2f}m, "
                        f"below the required {clearance_m:.2f}m minimum"
                    ),
                    distance_m=distance,
                )
            )

    return CollisionReport(is_clear=len(violations) == 0, violations=violations)
