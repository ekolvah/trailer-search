"""Public contract of the package and `find_trailer` (design 2, 3)."""

from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

from trailer_search import (
    Candidate,
    FilmProfile,
    TrailerPick,
    TrailerRetrievalError,
    find_trailer,
)

_SRC = Path(__file__).resolve().parent.parent / "src"


class _PoolRetriever:
    def __init__(self, pool: list[Candidate]) -> None:
        self.pool = pool

    def search_candidates(self, _profile: FilmProfile) -> list[Candidate]:
        return list(self.pool)


class _FailingRetriever:
    def search_candidates(self, _profile: FilmProfile) -> list[Candidate]:
        raise TrailerRetrievalError("all 2 retrieval branch(es) failed")


def test_public_contract_imports() -> None:
    from trailer_search.ytdlp import YtDlpRetriever  # noqa: PLC0415 — the import is the test

    assert callable(YtDlpRetriever)
    assert callable(find_trailer)
    assert issubclass(TrailerRetrievalError, Exception)
    assert [f.name for f in dataclasses.fields(TrailerPick)] == [
        "video_id",
        "title",
        "confidence",
        "reason",
    ]


def test_base_import_loads_no_extras() -> None:
    code = (
        "import sys, trailer_search; "
        "loaded = [m for m in ('yt_dlp', 'googleapiclient') if m in sys.modules]; "
        "assert not loaded, loaded"
    )
    env = {**os.environ, "PYTHONPATH": str(_SRC)}
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_pick_carries_candidate_title() -> None:
    title = "Зверь (2026)#трейлер в русской озвучке#The Beast"
    pool = [
        Candidate(video_id="en", title="The Beast 2026 Official Trailer"),
        Candidate(video_id="J2VS_OlUJtA", title=title),
    ]
    pick = find_trailer(FilmProfile("Зверь", "The Beast", 2026), _PoolRetriever(pool))
    assert (pick.video_id, pick.title) == ("J2VS_OlUJtA", title)


def test_retrieval_error_propagates() -> None:
    with pytest.raises(TrailerRetrievalError):
        find_trailer(FilmProfile("Зверь", "The Beast", 2026), _FailingRetriever())
