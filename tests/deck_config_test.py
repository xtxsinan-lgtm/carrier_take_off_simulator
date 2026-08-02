"""Unit tests for deck_config.py."""
import pytest

from utils.deck_config import assign_ski_jump_globals, total_takeoff_distance_m
from utils.ski_jump_geometry import compute_ski_jump_arc


def test_total_takeoff_distance():
    arc = compute_ski_jump_arc(14.0)
    assert total_takeoff_distance_m(100.0, arc.horizontal_m) == pytest.approx(100.0 + arc.horizontal_m)


def test_assign_ski_jump_globals_writes_expected_keys():
    g: dict = {}
    assign_ski_jump_globals(g, 12.0, lip_height_m=5.099)
    arc = compute_ski_jump_arc(12.0, lip_height_m=5.099)
    assert g['SKI_JUMP_ANGLE_DEG'] == 12.0
    assert g['SKI_JUMP_HORIZONTAL_M'] == pytest.approx(arc.horizontal_m)
    assert g['SKI_JUMP_LIP_HEIGHT_M'] == pytest.approx(arc.lip_height_m)
    assert g['SKI_JUMP_COS'] == pytest.approx(arc.cos_exit)
    assert g['SKI_JUMP_SIN'] == pytest.approx(arc.sin_exit)
