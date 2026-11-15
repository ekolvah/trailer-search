"""Live yt-dlp search on YouTube; excluded from CI by `addopts`, run with `-m live` (design 10)."""

from __future__ import annotations

import logging
import time

import pytest

from trailer_search import FilmProfile, find_trailer
from trailer_search.text import has_cyrillic
from trailer_search.ytdlp import YtDlpRetriever


@pytest.mark.live
def test_beast_russian_trailer(caplog: pytest.LogCaptureFixture) -> None:
    retriever = YtDlpRetriever(socket_timeout=4)
    started = time.monotonic()
    with caplog.at_level(logging.INFO, logger="trailer_search"):
        pick = find_trailer(FilmProfile("Зверь", "The Beast", 2026), retriever)
    elapsed = time.monotonic() - started
    print(f"pick={pick} elapsed={elapsed:.2f}s")
    assert (
        pick.title is not None and has_cyrillic(pick.title) and "Зверь" in pick.title
    ), pick
    assert elapsed < retriever.deadline_s, elapsed
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert not warnings, warnings
