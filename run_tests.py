#!/usr/bin/env python3
"""Run unit tests and e2e baseline verification."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', 'tests/', '-v']
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    print('Running:', ' '.join(cmd))
    return subprocess.call(cmd)


if __name__ == '__main__':
    raise SystemExit(main())
