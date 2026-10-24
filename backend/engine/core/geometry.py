"""Two-dimensional geometry used by the shared engine.

All distances are in inches and all points use a top-left origin: x grows to
the right and y grows down.  The digital twin stores terrain as polygons and
units as points with a base radius.  That is deliberately simple enough to be
serialized, rendered and validated, while still supporting line-of-sight and
deployment-zone checks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple

_EPSILON = 1e-9


def _as_float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class Vec2:
    """A point or vector in inches."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _as_float(self.x, "x"))
        object.__setattr__(self, "y", _as_float(self.y, "y"))

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Vec2":
        if abs(scalar) < _EPSILON:
            raise ZeroDivisionError("cannot divide a vector by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def distance_to(self, other: "Vec2") -> float:
        return (self - other).length()

    def lerp(self, other: "Vec2", fraction: float) -> "Vec2":
        fraction = max(0.0, min(1.0, float(fraction)))
        return Vec2(
            self.x + (other.x - self.x) * fraction,
            self.y + (other.y - self.y) * fraction,
        )

    def rounded(self, places: int = 6) -> "Vec2":
        return Vec2(round(self.x, places), round(self.y, places))

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Vec2":
        try:
            return cls(float(payload["x"]), float(payload["y"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid point: {exc}") from exc


def distance_point_to_segment(point: Vec2, start: Vec2, end: Vec2) -> float:
    """Shortest distance from ``point`` to the segment ``start-end``."""

    dx = end.x - start.x
    dy = end.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared < _EPSILON:
        return point.distance_to(start)
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    projection = Vec2(start.x + t * dx, start.y + t * dy)
    return point.distance_to(projection)


def _cross(a: Vec2, b: Vec2, c: Vec2) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _on_segment(a: Vec2, b: Vec2, p: Vec2) -> bool:
    return (
        min(a.x, b.x) - _EPSILON <= p.x <= max(a.x, b.x) + _EPSILON
        and min(a.y, b.y) - _EPSILON <= p.y <= max(a.y, b.y) + _EPSILON
    )


def segments_intersect(a: Vec2, b: Vec2, c: Vec2, d: Vec2) -> bool:
    """Return whether two closed line segments intersect."""

    ab_c = _cross(a, b, c)
    ab_d = _cross(a, b, d)
    cd_a = _cross(c, d, a)
    cd_b = _cross(c, d, b)

    if ((ab_c > _EPSILON and ab_d < -_EPSILON) or (ab_c < -_EPSILON and ab_d > _EPSILON)) and (
        (cd_a > _EPSILON and cd_b < -_EPSILON) or (cd_a < -_EPSILON and cd_b > _EPSILON)
    ):
        return True

    if abs(ab_c) <= _EPSILON and _on_segment(a, b, c):
        return True
    if abs(ab_d) <= _EPSILON and _on_segment(a, b, d):
        return True
    if abs(cd_a) <= _EPSILON and _on_segment(c, d, a):
        return True
    if abs(cd_b) <= _EPSILON and _on_segment(c, d, b):
        return True
    return False


def polygons_intersect(first: "Polygon", second: "Polygon") -> bool:
    """Return whether two polygons intersect (including containment)."""

    if any(first.contains(point) for point in second.points):
        return True
    if any(second.contains(point) for point in first.points):
        return True
    for a, b in first.edges():
        for c, d in second.edges():
            if segments_intersect(a, b, c, d):
                return True
    return False


@dataclass(frozen=True)
class Polygon:
    """A closed polygon with at least three vertices."""

    points: Tuple[Vec2, ...]

    def __post_init__(self) -> None:
        points = tuple(self.points)
        if len(points) < 3:
            raise ValueError("a polygon needs at least three points")
        object.__setattr__(self, "points", points)

    @classmethod
    def rectangle(cls, x: float, y: float, width: float, height: float) -> "Polygon":
        if width <= 0 or height <= 0:
            raise ValueError("rectangle dimensions must be positive")
        return cls(
            (
                Vec2(x, y),
                Vec2(x + width, y),
                Vec2(x + width, y + height),
                Vec2(x, y + height),
            )
        )

    @property
    def bounds(self) -> "Rect":
        xs = [point.x for point in self.points]
        ys = [point.y for point in self.points]
        return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    @property
    def center(self) -> Vec2:
        count = len(self.points)
        return Vec2(
            sum(point.x for point in self.points) / count,
            sum(point.y for point in self.points) / count,
        )

    def area(self) -> float:
        total = 0.0
        points = self.points
        for index, point in enumerate(points):
            nxt = points[(index + 1) % len(points)]
            total += point.x * nxt.y - nxt.x * point.y
        return abs(total) / 2.0

    def edges(self) -> List[Tuple[Vec2, Vec2]]:
        return [
            (self.points[index], self.points[(index + 1) % len(self.points)])
            for index in range(len(self.points))
        ]

    def contains(self, point: Vec2) -> bool:
        """Ray-casting point-in-polygon test with boundary inclusion."""

        inside = False
        points = self.points
        for index, current in enumerate(points):
            previous = points[index - 1]
            if distance_point_to_segment(point, previous, current) <= _EPSILON:
                return True
            if (current.y > point.y) != (previous.y > point.y):
                x_intersection = (previous.x - current.x) * (point.y - current.y) / (
                    previous.y - current.y
                ) + current.x
                if point.x < x_intersection:
                    inside = not inside
        return inside

    def intersects_segment(self, start: Vec2, end: Vec2) -> bool:
        if self.contains(start) or self.contains(end):
            return True
        return any(segments_intersect(start, end, a, b) for a, b in self.edges())

    def intersects(self, other: "Polygon") -> bool:
        return polygons_intersect(self, other)

    def to_dict(self) -> Dict[str, Any]:
        return {"points": [point.to_dict() for point in self.points]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Polygon":
        try:
            points = tuple(Vec2.from_dict(item) for item in payload["points"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid polygon: {exc}") from exc
        return cls(points)


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle with a top-left origin."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _as_float(self.x, "x"))
        object.__setattr__(self, "y", _as_float(self.y, "y"))
        object.__setattr__(self, "width", _as_float(self.width, "width"))
        object.__setattr__(self, "height", _as_float(self.height, "height"))
        if self.width <= 0 or self.height <= 0:
            raise ValueError("rectangle dimensions must be positive")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Vec2:
        return Vec2(self.x + self.width / 2.0, self.y + self.height / 2.0)

    def contains(self, point: Vec2) -> bool:
        return (
            self.x - _EPSILON <= point.x <= self.right + _EPSILON
            and self.y - _EPSILON <= point.y <= self.bottom + _EPSILON
        )

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.right < other.x - _EPSILON
            or other.right < self.x - _EPSILON
            or self.bottom < other.y - _EPSILON
            or other.bottom < self.y - _EPSILON
        )

    def contains_rect(self, other: "Rect") -> bool:
        return (
            self.x <= other.x + _EPSILON
            and self.y <= other.y + _EPSILON
            and self.right + _EPSILON >= other.right
            and self.bottom + _EPSILON >= other.bottom
        )

    def expanded(self, amount: float) -> "Rect":
        if amount < 0:
            raise ValueError("expansion amount must not be negative")
        return Rect(
            self.x - amount,
            self.y - amount,
            self.width + 2 * amount,
            self.height + 2 * amount,
        )

    def to_polygon(self) -> Polygon:
        return Polygon.rectangle(self.x, self.y, self.width, self.height)

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Rect":
        try:
            return cls(
                float(payload["x"]),
                float(payload["y"]),
                float(payload["width"]),
                float(payload["height"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid rectangle: {exc}") from exc


def clamp_point_within_board(point: Vec2, width: float, height: float, margin: float = 0.0) -> Vec2:
    """Clamp a point to the board, keeping a margin from every edge."""

    if width <= 0 or height <= 0:
        raise ValueError("board dimensions must be positive")
    margin = max(0.0, min(float(margin), min(width, height) / 2.0))
    return Vec2(
        min(max(point.x, margin), width - margin),
        min(max(point.y, margin), height - margin),
    )


def point_at_range(origin: Vec2, target: Vec2, maximum: float) -> Vec2:
    """Return ``target``, or the closest point toward it within ``maximum``."""

    distance = origin.distance_to(target)
    if distance <= maximum + _EPSILON or distance < _EPSILON:
        return target
    return origin.lerp(target, maximum / distance)


def rectangle_vertices(x: float, y: float, width: float, height: float) -> Tuple[Vec2, ...]:
    return Rect(x, y, width, height).to_polygon().points


def convex_hull(points: Iterable[Vec2]) -> Tuple[Vec2, ...]:
    """Return the convex hull of points (useful for future model footprints)."""

    unique = sorted({(point.x, point.y) for point in points})
    if len(unique) < 3:
        return tuple(Vec2(x, y) for x, y in unique)
    lower: List[Tuple[float, float]] = []
    for point in unique:
        while (
            len(lower) >= 2 and _cross(Vec2(*lower[-2]), Vec2(*lower[-1]), Vec2(*point)) <= _EPSILON
        ):
            lower.pop()
        lower.append(point)
    upper: List[Tuple[float, float]] = []
    for point in reversed(unique):
        while (
            len(upper) >= 2 and _cross(Vec2(*upper[-2]), Vec2(*upper[-1]), Vec2(*point)) <= _EPSILON
        ):
            upper.pop()
        upper.append(point)
    return tuple(Vec2(x, y) for x, y in lower[:-1] + upper[:-1])
