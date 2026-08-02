"""Capture numeric snapshots for refactor noop verification."""
import json

from utils.sim_snapshots import collect_snapshots, write_baseline


def main() -> None:
    data = collect_snapshots()
    print(json.dumps(data, default=str, indent=2))
    write_baseline()
    print('Wrote data/baseline_before.json', flush=True)


if __name__ == '__main__':
    main()
