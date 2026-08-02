"""Unit tests for search_utils.py."""
from utils.search_utils import fine_range_deck, fine_range_symmetric, grid_step


def test_grid_step_from_range():
    assert grid_step(range(0, 20, 5)) == 5


def test_grid_step_from_list():
    assert grid_step([10, 15, 20]) == 5


def test_fine_range_symmetric_clamps():
    assert list(fine_range_symmetric(50, 10, min_val=45, max_val=55)) == [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55]


def test_fine_range_deck_only_shorter():
    vals = list(fine_range_deck(100, 20, fine_step=5))
    assert vals == [80, 85, 90, 95]
    assert 100 not in vals


def test_fine_range_deck_empty_when_best_at_min():
    assert list(fine_range_deck(0, 20)) == []
