import pytest

from maidenhead.core import to_bbox
from maidenhead.vector import (
    azimuth_many,
    contains_many,
    contains_point_many,
    initial_bearing_many,
    intersects_bbox_many,
    intersects_polygon_many,
)


def test_azimuth_many_length_mismatch():
    with pytest.raises(ValueError):
        azimuth_many(["IO83ri", "JO22db"], ["IO83ri"])


def test_initial_bearing_many_length_mismatch():
    with pytest.raises(ValueError):
        initial_bearing_many(["IO83ri", "JO22db"], ["IO83ri"])


def test_intersects_bbox_many_length_mismatch():
    bboxes = [to_bbox("IO83ri")]
    with pytest.raises(ValueError):
        intersects_bbox_many(["IO83ri", "JO22db"], bboxes)


def test_intersects_polygon_many_length_mismatch():
    polygons = [[(0.0, 0.0), (0.0, 1.0), (1.0, 0.0)]]
    with pytest.raises(ValueError):
        intersects_polygon_many(["IO83ri", "JO22db"], polygons)


def test_contains_point_many_length_mismatch():
    with pytest.raises(ValueError):
        contains_point_many(["IO83ri", "JO22db"], [0.0], [0.0, 1.0])


def test_contains_many_length_mismatch():
    with pytest.raises(ValueError):
        contains_many(["IO83ri", "JO22db"], ["IO83ri"])
