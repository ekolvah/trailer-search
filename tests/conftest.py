"""Fixtures shared across test modules."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from itertools import count
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def release() -> Iterator[threading.Event]:
    """Blocks a fake branch; the finalizer frees it even after a failed assert."""
    event = threading.Event()
    yield event
    event.set()


@pytest.fixture
def write(tmp_path: Path) -> Callable[[Any], str]:
    """Writes JSON to a fresh file per call and returns its path."""
    numbers = count()

    def _write(data: Any) -> str:
        path = tmp_path / f"f{next(numbers)}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)

    return _write
