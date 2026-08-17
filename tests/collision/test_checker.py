from hangar_cv_optimizer.collision.checker import ViolationType, check_collisions
from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary, Point


def make_hangar(width: float = 100.0, height: float = 60.0) -> HangarBoundary:
    return HangarBoundary(
        vertices=[
            Point(x=0, y=0),
            Point(x=width, y=0),
            Point(x=width, y=height),
            Point(x=0, y=height),
        ]
    )


def make_aircraft(id_: str, x: float, y: float, wingspan: float = 10.0, length: float = 12.0, rotation: float = 0.0) -> AircraftFootprint:
    return AircraftFootprint(
        id=id_,
        wingspan_m=wingspan,
        length_m=length,
        center=Point(x=x, y=y),
        rotation_deg=rotation,
    )


def test_no_violations_when_well_separated():
    hangar = make_hangar()
    aircraft = [
        make_aircraft("a1", x=20, y=20),
        make_aircraft("a2", x=70, y=20),
    ]

    report = check_collisions(aircraft, hangar, clearance_m=3.0)

    assert report.is_clear
    assert report.violations == []


def test_detects_direct_overlap():
    hangar = make_hangar()
    aircraft = [
        make_aircraft("a1", x=30, y=30),
        make_aircraft("a2", x=32, y=30),
    ]

    report = check_collisions(aircraft, hangar, clearance_m=3.0)

    assert not report.is_clear
    assert any(v.type == ViolationType.AIRCRAFT_OVERLAP for v in report.violations)


def test_detects_clearance_breach_without_overlap():
    hangar = make_hangar()
    # length 12 -> half-length 6 each side along x; gap between edges = 34-6-(20+6) = 2m < 3m clearance
    aircraft = [
        make_aircraft("a1", x=20, y=20),
        make_aircraft("a2", x=34, y=20),
    ]

    report = check_collisions(aircraft, hangar, clearance_m=3.0)

    assert not report.is_clear
    breach = next(v for v in report.violations if v.type == ViolationType.CLEARANCE_BREACH)
    assert breach.distance_m is not None
    assert breach.distance_m < 3.0


def test_detects_aircraft_outside_boundary():
    hangar = make_hangar(width=20, height=20)
    aircraft = [make_aircraft("a1", x=100, y=100)]

    report = check_collisions(aircraft, hangar)

    assert not report.is_clear
    assert report.violations[0].type == ViolationType.OUTSIDE_BOUNDARY


def test_detects_obstacle_overlap():
    hangar = HangarBoundary(
        vertices=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=60), Point(x=0, y=60)],
        obstacles=[[Point(x=40, y=0), Point(x=50, y=0), Point(x=50, y=60), Point(x=40, y=60)]],
    )
    aircraft = [make_aircraft("a1", x=45, y=30)]

    report = check_collisions(aircraft, hangar)

    assert not report.is_clear
    assert any(v.type == ViolationType.OBSTACLE_OVERLAP for v in report.violations)


def test_empty_aircraft_list_is_clear():
    hangar = make_hangar()

    report = check_collisions([], hangar)

    assert report.is_clear
    assert report.violations == []


def test_rotation_changes_effective_footprint():
    hangar = make_hangar()
    # a1 spans x:[10,30] y:[18,22]. a2 unrotated (length along x) spans x:[24,44] -> overlaps a1.
    # Rotating a2 90deg swaps which dimension faces a1, removing the overlap.
    a1 = make_aircraft("a1", x=20, y=20, wingspan=4.0, length=20.0, rotation=0.0)
    a2 = make_aircraft("a2", x=34, y=20, wingspan=4.0, length=20.0, rotation=0.0)

    report_unrotated = check_collisions([a1, a2], hangar, clearance_m=3.0)
    assert any(v.type == ViolationType.AIRCRAFT_OVERLAP for v in report_unrotated.violations)

    a2_rotated = a2.model_copy(update={"rotation_deg": 90.0})
    report_rotated = check_collisions([a1, a2_rotated], hangar, clearance_m=3.0)
    assert not any(v.type == ViolationType.AIRCRAFT_OVERLAP for v in report_rotated.violations)
