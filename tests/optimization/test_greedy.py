from hangar_cv_optimizer.collision.checker import check_collisions
from hangar_cv_optimizer.geometry.models import HangarBoundary, Point
from hangar_cv_optimizer.optimization.greedy import greedy_place
from hangar_cv_optimizer.optimization.models import PlaceableAircraft


def make_hangar(width: float = 60.0, height: float = 60.0) -> HangarBoundary:
    return HangarBoundary(
        vertices=[
            Point(x=0, y=0),
            Point(x=width, y=0),
            Point(x=width, y=height),
            Point(x=0, y=height),
        ]
    )


def test_places_aircraft_that_fit():
    hangar = make_hangar()
    aircraft = [
        PlaceableAircraft(id="a1", wingspan_m=8, length_m=10),
        PlaceableAircraft(id="a2", wingspan_m=8, length_m=10),
    ]

    placed = greedy_place(aircraft, hangar, clearance_m=2.0)

    assert {a.id for a in placed} == {"a1", "a2"}


def test_skips_aircraft_that_cannot_fit():
    hangar = make_hangar(width=15, height=15)
    aircraft = [
        PlaceableAircraft(id="too_big", wingspan_m=50, length_m=50),
        PlaceableAircraft(id="fits", wingspan_m=5, length_m=5),
    ]

    placed = greedy_place(aircraft, hangar, clearance_m=1.0)

    placed_ids = {a.id for a in placed}
    assert "too_big" not in placed_ids


def test_empty_aircraft_list_places_nothing():
    hangar = make_hangar()
    assert greedy_place([], hangar, clearance_m=2.0) == []


def test_greedy_output_never_violates_collision_rules():
    """The placer's own output, fed back through the independent collision
    checker, must always report clear - this is the correctness guarantee
    the optimization endpoint relies on."""
    hangar = make_hangar(width=80, height=80)
    aircraft = [
        PlaceableAircraft(id=f"a{i}", wingspan_m=8, length_m=10) for i in range(10)
    ]

    placed = greedy_place(aircraft, hangar, clearance_m=3.0)

    report = check_collisions(placed, hangar, clearance_m=3.0)
    assert report.is_clear


def test_obstacle_leaving_only_a_too_small_gap_leaves_aircraft_unplaced():
    # Obstacle covers all but a 20x2 strip along the top edge - too narrow for a 5x5 footprint.
    hangar = HangarBoundary(
        vertices=[Point(x=0, y=0), Point(x=20, y=0), Point(x=20, y=20), Point(x=0, y=20)],
        obstacles=[[Point(x=0, y=0), Point(x=20, y=0), Point(x=20, y=18), Point(x=0, y=18)]],
    )
    aircraft = [PlaceableAircraft(id="a1", wingspan_m=5, length_m=5)]

    placed = greedy_place(aircraft, hangar, clearance_m=1.0, grid_step_m=1.0)

    assert placed == []
