"""Unit tests for ski_jump_geometry.py."""
import math

import pytest

from utils.ski_jump_geometry import (
    SKI_JUMP_REF_RADIUS_M,
    compute_ski_jump_arc,
    deck_angle_deg_at_s,
    deck_angle_rad_at_s,
    deck_cos_sin_at_s,
    deck_height_at_s,
    horizontal_at_s,
)


def test_ref_radius_arc_14deg():
    arc = compute_ski_jump_arc(14.0)
    assert arc.radius_m == pytest.approx(SKI_JUMP_REF_RADIUS_M)
    assert arc.lip_height_m == pytest.approx(SKI_JUMP_REF_RADIUS_M * (1 - math.cos(math.radians(14))))
    assert arc.arc_length_m == pytest.approx(SKI_JUMP_REF_RADIUS_M * math.radians(14))
    assert arc.horizontal_m == pytest.approx(SKI_JUMP_REF_RADIUS_M * math.sin(math.radians(14)))


def test_lip_height_sets_radius():
    arc = compute_ski_jump_arc(12.0, lip_height_m=5.099)
    expected_r = 5.099 / (1 - math.cos(math.radians(12)))
    assert arc.radius_m == pytest.approx(expected_r)
    assert arc.lip_height_m == pytest.approx(5.099)


def test_explicit_radius_overrides_height():
    arc = compute_ski_jump_arc(14.0, lip_height_m=5.0, radius_m=180.0)
    assert arc.radius_m == pytest.approx(180.0)
    assert arc.lip_height_m == pytest.approx(180.0 * (1 - math.cos(math.radians(14))))


def test_arc_length_input():
    angle_rad = math.radians(12.0)
    arc_len = 41.9
    arc = compute_ski_jump_arc(12.0, radius_m=arc_len / angle_rad)
    assert arc.arc_length_m == pytest.approx(arc_len)


def test_invalid_angle_raises():
    with pytest.raises(ValueError, match='滑跃角必须为正'):
        compute_ski_jump_arc(0.0)


def test_deck_angle_along_arc():
    arc = compute_ski_jump_arc(14.0)
    assert deck_angle_rad_at_s(0.0, arc) == 0.0
    assert deck_angle_deg_at_s(arc.arc_length_m, arc) == pytest.approx(14.0)
    assert deck_angle_rad_at_s(arc.arc_length_m * 2, arc) == pytest.approx(arc.angle_rad)


def test_deck_height_at_s_matches_cos_law():
    """deck_height_at_s 应满足 R(1-cos φ)。"""
    arc = compute_ski_jump_arc(14.0)
    mid_s = arc.arc_length_m / 2
    phi = deck_angle_rad_at_s(mid_s, arc)
    assert deck_height_at_s(mid_s, arc) == pytest.approx(arc.radius_m * (1 - math.cos(phi)))
    assert deck_height_at_s(0.0, arc) == pytest.approx(0.0)
    assert deck_height_at_s(arc.arc_length_m, arc) == pytest.approx(arc.lip_height_m)


def test_horizontal_at_s_matches_sin_law():
    arc = compute_ski_jump_arc(14.0)
    mid_s = arc.arc_length_m / 2
    assert horizontal_at_s(mid_s, arc) == pytest.approx(
        arc.radius_m * math.sin(deck_angle_rad_at_s(mid_s, arc))
    )


def test_deck_cos_sin_at_exit():
    arc = compute_ski_jump_arc(14.0)
    cos_v, sin_v = deck_cos_sin_at_s(arc.arc_length_m, arc)
    assert cos_v == pytest.approx(math.cos(arc.angle_rad))
    assert sin_v == pytest.approx(math.sin(arc.angle_rad))
