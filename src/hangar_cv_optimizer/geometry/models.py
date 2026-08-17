from __future__ import annotations

from pydantic import BaseModel, Field
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate


class Point(BaseModel):
    x: float
    y: float


class AircraftFootprint(BaseModel):
    """Rectangular footprint approximation of an aircraft, anchored at its center."""

    id: str
    label: str = ""
    wingspan_m: float = Field(gt=0)
    length_m: float = Field(gt=0)
    center: Point
    rotation_deg: float = 0.0

    def to_polygon(self) -> Polygon:
        half_w = self.wingspan_m / 2
        half_l = self.length_m / 2
        base = Polygon(
            [
                (-half_l, -half_w),
                (half_l, -half_w),
                (half_l, half_w),
                (-half_l, half_w),
            ]
        )
        rotated = rotate(base, self.rotation_deg, origin=(0, 0), use_radians=False)
        return translate(rotated, xoff=self.center.x, yoff=self.center.y)


class HangarBoundary(BaseModel):
    """Hangar usable area as a polygon, with optional obstacle polygons cut out."""

    vertices: list[Point] = Field(min_length=3)
    obstacles: list[list[Point]] = Field(default_factory=list)

    def to_polygon(self) -> Polygon:
        shell = [(p.x, p.y) for p in self.vertices]
        holes = [[(p.x, p.y) for p in obs] for obs in self.obstacles]
        return Polygon(shell, holes=holes)
