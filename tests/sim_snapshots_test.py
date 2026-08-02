"""E2E regression: full simulator snapshots match baseline_before.json."""
import pytest

from utils.sim_snapshots import assert_matches_baseline, collect_snapshots, diff_snapshots, load_baseline


@pytest.mark.e2e
def test_refactor_snapshots_match_baseline():
    """Equivalent to running verify_refactor.py."""
    assert_matches_baseline()


@pytest.mark.e2e
def test_collect_snapshots_has_all_modules():
    snap = collect_snapshots()
    assert set(snap.keys()) == {'flat', 'ski_stovl', 'ski_conv'}
    before = load_baseline()
    assert diff_snapshots(before, snap) == []
