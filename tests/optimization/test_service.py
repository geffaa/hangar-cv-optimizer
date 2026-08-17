from hangar_cv_optimizer.collision.checker import check_collisions
from hangar_cv_optimizer.geometry.models import HangarBoundary, Point
from hangar_cv_optimizer.optimization.models import PlaceableAircraft
from hangar_cv_optimizer.optimization.service import optimize_layout


def make_hangar(width: float = 80.0, height: float = 80.0) -> HangarBoundary:
    return HangarBoundary(
        vertices=[
            Point(x=0, y=0),
            Point(x=width, y=0),
            Point(x=width, y=height),
            Point(x=0, y=height),
        ]
    )


def test_optimize_layout_result_is_collision_free():
    hangar = make_hangar()
    aircraft = [PlaceableAircraft(id=f"a{i}", wingspan_m=8, length_m=10) for i in range(12)]

    result = optimize_layout(aircraft, hangar, clearance_m=3.0, iterations=30, seed=42)

    report = check_collisions(result.placed, hangar, clearance_m=3.0)
    assert report.is_clear
    assert set(a.id for a in result.placed) | set(result.unplaced_ids) == {a.id for a in aircraft}


def test_optimize_layout_utilization_between_zero_and_one():
    hangar = make_hangar()
    aircraft = [PlaceableAircraft(id=f"a{i}", wingspan_m=8, length_m=10) for i in range(6)]

    result = optimize_layout(aircraft, hangar, clearance_m=3.0, iterations=20, seed=1)

    assert 0.0 <= result.utilization <= 1.0


def test_optimize_layout_handles_empty_aircraft_list():
    hangar = make_hangar()

    result = optimize_layout([], hangar, clearance_m=3.0, iterations=10)

    assert result.placed == []
    assert result.unplaced_ids == []
    assert result.utilization == 0.0


def test_optimize_layout_is_deterministic_given_seed():
    hangar = make_hangar()
    aircraft = [PlaceableAircraft(id=f"a{i}", wingspan_m=8, length_m=10) for i in range(8)]

    result_a = optimize_layout(aircraft, hangar, clearance_m=3.0, iterations=25, seed=7)
    result_b = optimize_layout(aircraft, hangar, clearance_m=3.0, iterations=25, seed=7)

    assert [a.id for a in result_a.placed] == [a.id for a in result_b.placed]
