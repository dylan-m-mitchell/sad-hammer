from backend.engine.core.geometry import (
    Polygon,
    Rect,
    Vec2,
    clamp_point_within_board,
    distance_point_to_segment,
    point_at_range,
    segments_intersect,
)


def test_vec_distance_and_lerp():
    start = Vec2(0, 0)
    end = Vec2(3, 4)

    assert start.distance_to(end) == 5
    assert start.lerp(end, 0.5) == Vec2(1.5, 2.0)
    assert start.lerp(end, 2.0) == end


def test_rect_contains_and_intersects():
    first = Rect(0, 0, 10, 10)
    second = Rect(8, 8, 5, 5)
    outside = Rect(20, 20, 1, 1)

    assert first.contains(Vec2(5, 5))
    assert not first.contains(Vec2(-0.1, 5))
    assert first.intersects(second)
    assert not first.intersects(outside)
    assert first.contains_rect(Rect(1, 1, 2, 2))


def test_polygon_area_contains_and_segment():
    square = Polygon.rectangle(0, 0, 10, 10)

    assert square.area() == 100
    assert square.contains(Vec2(5, 5))
    assert square.contains(Vec2(0, 0))
    assert not square.contains(Vec2(11, 5))
    assert square.intersects_segment(Vec2(-1, 5), Vec2(11, 5))
    assert not square.intersects_segment(Vec2(11, 5), Vec2(12, 5))


def test_segment_intersection_and_distances():
    assert segments_intersect(Vec2(0, 0), Vec2(2, 2), Vec2(0, 2), Vec2(2, 0))
    assert not segments_intersect(Vec2(0, 0), Vec2(1, 0), Vec2(0, 1), Vec2(1, 1))
    assert distance_point_to_segment(Vec2(0, 2), Vec2(0, 0), Vec2(4, 0)) == 2


def test_board_clamping_and_range_limit():
    assert clamp_point_within_board(Vec2(-5, 40), 44, 30, 1) == Vec2(1, 29)
    assert point_at_range(Vec2(0, 0), Vec2(10, 0), 4) == Vec2(4, 0)
    assert point_at_range(Vec2(0, 0), Vec2(3, 0), 4) == Vec2(3, 0)


def test_polygon_intersection():
    first = Polygon.rectangle(0, 0, 4, 4)
    second = Polygon.rectangle(3, 3, 4, 4)
    separate = Polygon.rectangle(20, 20, 2, 2)

    assert first.intersects(second)
    assert not first.intersects(separate)
