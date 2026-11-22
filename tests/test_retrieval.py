"""`search_union`: the query union shared by both retrievers (design 4, 5, 12)."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable

import pytest

from trailer_search import Candidate, FilmProfile, TrailerRetrievalError
from trailer_search.retrieval import search_union

WOLF = FilmProfile(ru_title="Волк", original_title="The Wolf", year=2025)
RU_Q = "Волк 2025 trailer"
ORIG_Q = "The Wolf 2025 trailer"


def _c(video_id: str) -> Candidate:
    return Candidate(video_id=video_id, title=video_id)


class _Branches:
    """`search_one` double: query → candidates | exception | blocking callable."""

    def __init__(
        self, by_query: dict[str, list[Candidate] | Exception | Callable[[], object]]
    ):
        self.by_query = by_query
        self.queries: list[str] = []

    def __call__(self, query: str) -> list[Candidate]:
        self.queries.append(query)
        out = self.by_query.get(query, [])
        if isinstance(out, Exception):
            raise out
        if callable(out):
            out()
            return []
        return out


def test_query_durations_logged(caplog: pytest.LogCaptureFixture) -> None:
    search = _Branches({RU_Q: [_c("A")], ORIG_Q: [_c("B")]})
    with caplog.at_level(logging.INFO, logger="trailer_search"):
        search_union(WOLF, search, max_workers=2)
    infos = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    duration = re.compile(r"\d+\.\d+s")
    for query in (RU_Q, ORIG_Q):
        assert any(query in m and duration.search(m) for m in infos), infos
    assert any("total" in m and duration.search(m) for m in infos), infos


@pytest.mark.parametrize("max_workers", [1, 2])
def test_union_order_and_dedup(max_workers: int) -> None:
    # With two workers the Russian branch finishes last; the pool still keeps query order.
    orig_done = threading.Event()

    def ru_after_orig() -> list[Candidate]:
        orig_done.wait(5)
        return [_c("A")]

    def search(query: str) -> list[Candidate]:
        if query == RU_Q:
            return ru_after_orig() if max_workers > 1 else [_c("A")]
        orig_done.set()
        return [_c("A"), _c("B")]

    pool = search_union(WOLF, search, max_workers=max_workers)
    assert [c.video_id for c in pool] == ["A", "B"]


@pytest.mark.parametrize("original_title", ["Дюна", ""])
def test_equal_titles_query_once(original_title: str) -> None:
    search = _Branches({})
    search_union(
        FilmProfile(ru_title="Дюна", original_title=original_title, year=2024),
        search,
        max_workers=2,
    )
    assert search.queries == ["Дюна 2024 trailer"]


def test_query_without_year() -> None:
    search = _Branches({})
    search_union(
        FilmProfile(ru_title="Дюна", original_title="", year=None),
        search,
        max_workers=1,
    )
    assert search.queries == ["Дюна trailer"]


@pytest.mark.parametrize(
    ("original_title", "expected"),
    [
        (
            "The Gentlemen",
            ["Джентльмены 2 сезон trailer", "The Gentlemen season 2 trailer"],
        ),
        ("", ["Джентльмены 2 сезон trailer"]),
    ],
)
def test_season_queries(original_title: str, expected: list[str]) -> None:
    search = _Branches({})
    search_union(
        FilmProfile(
            ru_title="Джентльмены",
            original_title=original_title,
            year=2024,
            season=2,
        ),
        search,
        max_workers=1,
    )
    assert search.queries == expected


@pytest.mark.parametrize(
    ("ru_title", "original_title", "year", "series", "expected"),
    [
        (
            "Монстры",
            "Monster",
            2022,
            True,
            ["Монстры 2022 сериал trailer", "Monster 2022 series trailer"],
        ),
        (
            "Хартленд",
            "Heartland",
            2026,
            False,
            ["Хартленд 2026 фильм trailer", "Heartland 2026 movie trailer"],
        ),
        (
            "Монстры",
            "Monster",
            None,
            True,
            ["Монстры сериал trailer", "Monster series trailer"],
        ),
    ],
)
def test_typed_queries(
    ru_title: str,
    original_title: str,
    year: int | None,
    series: bool,
    expected: list[str],
) -> None:
    search = _Branches({})
    profile = FilmProfile(ru_title, original_title, year, series=series)
    search_union(profile, search, max_workers=1)
    assert search.queries == expected


def test_one_branch_failure_warns(caplog: pytest.LogCaptureFixture) -> None:
    search = _Branches({RU_Q: [_c("A")], ORIG_Q: RuntimeError("YouTube 500")})
    with caplog.at_level(logging.WARNING, logger="trailer_search"):
        pool = search_union(WOLF, search, max_workers=2)
    assert [c.video_id for c in pool] == ["A"]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(ORIG_Q in m for m in warnings), warnings


class _QuotaLike(TrailerRetrievalError):
    """Stands in for a retriever's own subclass, such as `YoutubeQuotaExhausted`."""


def test_all_branches_fail_raises() -> None:
    first = RuntimeError("timeout")
    search = _Branches({RU_Q: first, ORIG_Q: RuntimeError("reset")})
    with pytest.raises(TrailerRetrievalError) as excinfo:
        search_union(WOLF, search, max_workers=2)
    assert type(excinfo.value) is TrailerRetrievalError
    assert excinfo.value.__cause__ is first


def test_all_branches_fail_keeps_branch_subclass() -> None:
    quota = _QuotaLike("quota")
    search = _Branches({RU_Q: RuntimeError("timeout"), ORIG_Q: quota})
    with pytest.raises(_QuotaLike) as excinfo:
        search_union(WOLF, search, max_workers=1)
    assert excinfo.value.__cause__ is quota


def test_empty_results_not_failure() -> None:
    assert search_union(WOLF, _Branches({}), max_workers=2) == []


def test_late_query_dropped_at_deadline(
    release: threading.Event, caplog: pytest.LogCaptureFixture
) -> None:
    search = _Branches({RU_Q: [_c("A")], ORIG_Q: lambda: release.wait(5)})
    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger="trailer_search"):
        pool = search_union(WOLF, search, max_workers=2, deadline_s=0.2)
    elapsed = time.monotonic() - started
    assert [c.video_id for c in pool] == ["A"]
    assert elapsed < 0.7, elapsed
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(ORIG_Q in m for m in warnings), warnings
