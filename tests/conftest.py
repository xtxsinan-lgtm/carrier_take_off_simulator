"""Shared fixtures."""
from __future__ import annotations

import json

import pytest

from utils.paths import BASELINE_JSON, ROOT


@pytest.fixture(scope='session')
def baseline() -> dict:
    return json.loads(BASELINE_JSON.read_text(encoding='utf-8'))
