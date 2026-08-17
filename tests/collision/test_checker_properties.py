from hypothesis import given, settings
from hypothesis import strategies as st

from hangar_cv_optimizer.collision.checker import check_collisions
from hangar_cv_optimizer.geometry.models import AircraftFootprint, HangarBoundary, Point

HANGAR = HangarBoundary(
    vertices=[Point(x=0, y=0), Point(x=200, y=0), Point(x=200, y=200), Point(x=0, y=200)]
)


def aircraft_strategy(id_: str) -> st.SearchStrategy[AircraftFootprint]:
    return st.builds(
        AircraftFootprint,
        id=st.just(id_),
        label=st.just(""),
        wingspan_m=st.floats(min_value=2.0, max_value=15.0),
        length_m=st.floats(min_value=2.0, max_value=20.0),
        center=st.builds(Point, x=st.floats(min_value=20, max_value=180), y=st.floats(min_value=20, max_value=180)),
        rotation_deg=st.floats(min_value=0.0, max_value=359.0),
    )


@given(a1=aircraft_strategy("a1"), a2=aircraft_strategy("a2"))
@settings(max_examples=200)
def test_clear_report_implies_no_geometric_overlap(a1: AircraftFootprint, a2: AircraftFootprint):
    """Invariant: if check_collisions reports no AIRCRAFT_OVERLAP violation between
    two aircraft, their polygons must not actually intersect. This is the guarantee
    the optimization solver relies on when it treats a clear report as ground truth."""
    report = check_collisions([a1, a2], HANGAR, clearance_m=0.0)

    overlap_flagged = any(v.aircraft_ids == ["a1", "a2"] or v.aircraft_ids == ["a2", "a1"] for v in report.violations)
    actually_intersects = a1.to_polygon().intersects(a2.to_polygon())

    assert overlap_flagged == actually_intersects
