"""Candidate retrieval contract and the query union shared by the retrievers."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from typing import NoReturn, Protocol

from trailer_search.strategy import Candidate, FilmProfile

logger = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_DURATION_S = 240

# A branch's outcome: its candidates, its exception, or None when it missed the deadline.
_Outcome = list[Candidate] | Exception | None


class TrailerRetrievalError(RuntimeError):
    """No union branch succeeded, so there is no candidate pool to select from."""


class TrailerRetriever(Protocol):
    def search_candidates(self, profile: FilmProfile) -> list[Candidate]: ...


def _queries(profile: FilmProfile) -> list[str]:
    titles = [profile.ru_title]
    if profile.original_title and profile.original_title != profile.ru_title:
        titles.append(profile.original_title)
    season = profile.season
    if season is not None:
        return [f"{titles[0]} {season} сезон trailer"] + [
            f"{t} season {season} trailer" for t in titles[1:]
        ]
    year = f" {profile.year}" if profile.year else ""
    # Type word per language, Russian query first (design 6).
    words = {None: ("", ""), True: (" сериал", " series"), False: (" фильм", " movie")}
    return [
        f"{t}{year}{w} trailer"
        for t, w in zip(titles, words[profile.series], strict=False)
    ]


def _branch(
    search_one: Callable[[str], list[Candidate]], query: str
) -> list[Candidate] | Exception:
    started = time.monotonic()
    try:
        candidates = search_one(query)
    except Exception as exc:  # noqa: BLE001 — one failed branch must not sink the pool (§IV); search_union raises when none succeeded
        logger.warning(
            "trailer retrieval branch %r failed after %.2fs: %s",
            query,
            time.monotonic() - started,
            exc,
        )
        return exc
    logger.info(
        "trailer retrieval branch %r: %d candidate(s) in %.2fs",
        query,
        len(candidates),
        time.monotonic() - started,
    )
    return candidates


def _run_pooled(
    search_one: Callable[[str], list[Candidate]],
    queries: list[str],
    max_workers: int,
    deadline_s: float | None,
) -> list[_Outcome]:
    # Not a `with` block: its exit joins the workers, which would wait out a blocked branch.
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = [executor.submit(_branch, search_one, q) for q in queries]
    try:
        done, _ = wait(futures, timeout=deadline_s)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    outcomes: list[_Outcome] = []
    for query, future in zip(queries, futures, strict=True):
        if future in done:
            outcomes.append(future.result())
        else:
            logger.warning(
                "trailer retrieval branch %r dropped: no result within %.2fs deadline",
                query,
                deadline_s,
            )
            outcomes.append(None)
    return outcomes


def _raise_union_error(profile: FilmProfile, outcomes: list[_Outcome]) -> NoReturn:
    """The first branch's own `TrailerRetrievalError` subclass decides the class (a quota
    signal must survive a mixed failure); otherwise the base class from the first failure."""
    errors = [o for o in outcomes if isinstance(o, Exception)]
    typed = next((e for e in errors if isinstance(e, TrailerRetrievalError)), None)
    cause = typed if typed is not None else (errors[0] if errors else None)
    error_cls = type(typed) if typed is not None else TrailerRetrievalError
    raise error_cls(
        f"all {len(outcomes)} retrieval branch(es) failed for {profile.ru_title!r}: "
        f"{len(errors)} raised, {len(outcomes) - len(errors)} missed the deadline"
    ) from cause


def search_union(
    profile: FilmProfile,
    search_one: Callable[[str], list[Candidate]],
    *,
    max_workers: int,
    deadline_s: float | None = None,
) -> list[Candidate]:
    """Union of the Russian-title and original-title queries, deduplicated by `video_id`
    in query order. One failed or late branch logs WARNING and the rest survive; no
    surviving branch raises `TrailerRetrievalError`. An empty list means the queries
    succeeded and found nothing. With `deadline_s` the branches always run in a pool and
    those not done by then are dropped."""
    started = time.monotonic()
    queries = _queries(profile)
    outcomes: list[_Outcome]
    if deadline_s is None and (len(queries) == 1 or max_workers == 1):
        outcomes = [_branch(search_one, q) for q in queries]
    else:
        outcomes = _run_pooled(search_one, queries, max_workers, deadline_s)
    seen: set[str] = set()
    pool: list[Candidate] = []
    succeeded = 0
    for outcome in outcomes:
        if outcome is None or isinstance(outcome, Exception):
            continue
        succeeded += 1
        for candidate in outcome:
            if candidate.video_id not in seen:
                seen.add(candidate.video_id)
                pool.append(candidate)
    logger.info(
        "trailer retrieval for %r: %d candidate(s) from %d/%d branch(es), %.2fs total",
        profile.ru_title,
        len(pool),
        succeeded,
        len(queries),
        time.monotonic() - started,
    )
    if not succeeded:
        _raise_union_error(profile, outcomes)
    return pool
