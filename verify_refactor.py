"""Compare refactor snapshots for noop verification."""
import sys

from utils.sim_snapshots import assert_matches_baseline, collect_snapshots, diff_snapshots, load_baseline


def main() -> None:
    try:
        assert_matches_baseline()
    except FileNotFoundError:
        print('Missing data/baseline_before.json — run verify_refactor_baseline.py first')
        sys.exit(1)
    except AssertionError as exc:
        before = load_baseline()
        after = collect_snapshots()
        print('MISMATCH detected')
        for key in diff_snapshots(before, after):
            print(f'  diff in {key}')
        print(exc)
        sys.exit(1)

    print('NOOP OK: refactor outputs match baseline')
    sys.exit(0)


if __name__ == '__main__':
    main()
