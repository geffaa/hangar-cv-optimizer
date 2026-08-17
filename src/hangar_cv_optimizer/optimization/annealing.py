from __future__ import annotations

import math
import random

from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary
from hangar_cv_optimizer.optimization.greedy import greedy_place
from hangar_cv_optimizer.optimization.models import PlaceableAircraft


def _objective(placed: list[AircraftFootprint]) -> float:
    """Primary: number of aircraft placed. Secondary: total footprint area,
    as a tie-breaker that nudges the search toward denser packing."""
    total_area = sum(a.to_polygon().area for a in placed)
    return len(placed) * 1_000_000.0 + total_area


def anneal_layout(
    aircraft: list[PlaceableAircraft],
    hangar: HangarBoundary,
    clearance_m: float,
    grid_step_m: float = 2.0,
    iterations: int = 150,
    initial_temperature: float = 10.0,
    cooling_rate: float = 0.95,
    seed: int | None = None,
) -> list[AircraftFootprint]:
    """Simulated annealing over the *placement order* fed to the greedy
    first-fit placer. Placing larger aircraft first tends to pack better, but
    isn't always optimal given hangar shape/obstacles - annealing explores
    order permutations to escape that local optimum, using the greedy
    placer's built-in no-overlap/clearance guarantee for every candidate.
    """
    rng = random.Random(seed)

    current_order = sorted(
        aircraft, key=lambda a: a.wingspan_m * a.length_m, reverse=True
    )
    current_placed = greedy_place(current_order, hangar, clearance_m, grid_step_m)
    current_score = _objective(current_placed)

    best_placed = current_placed
    best_score = current_score

    temperature = initial_temperature

    for _ in range(iterations):
        if len(current_order) < 2:
            break

        candidate_order = list(current_order)
        i, j = rng.sample(range(len(candidate_order)), 2)
        candidate_order[i], candidate_order[j] = candidate_order[j], candidate_order[i]

        candidate_placed = greedy_place(candidate_order, hangar, clearance_m, grid_step_m)
        candidate_score = _objective(candidate_placed)

        delta = candidate_score - current_score
        accept = delta > 0 or (
            temperature > 1e-9 and rng.random() < math.exp(delta / max(temperature, 1e-9))
        )

        if accept:
            current_order = candidate_order
            current_placed = candidate_placed
            current_score = candidate_score

            if candidate_score > best_score:
                best_placed = candidate_placed
                best_score = candidate_score

        temperature *= cooling_rate

    return best_placed
