from __future__ import annotations

from pydantic import BaseModel, Field

from hangar_cv_optimizer.geometry.models import AircraftFootprint


class PlaceableAircraft(BaseModel):
    """An aircraft to be positioned, without a known location yet."""

    id: str
    label: str = ""
    wingspan_m: float = Field(gt=0)
    length_m: float = Field(gt=0)


class PlacementResult(BaseModel):
    placed: list[AircraftFootprint]
    unplaced_ids: list[str]
    utilization: float
    """Fraction of hangar usable area covered by placed aircraft footprints."""
