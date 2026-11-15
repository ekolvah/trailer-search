"""Candidate retrieval contract (RED stub)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from trailer_search.strategy import Candidate, FilmProfile

MAX_RESULTS = 5
MAX_DURATION_S = 240


class TrailerRetrievalError(RuntimeError):
    """No candidate pool could be retrieved."""


class TrailerRetriever(Protocol):
    def search_candidates(self, profile: FilmProfile) -> list[Candidate]: ...


def search_union(
    profile: FilmProfile,
    search_one: Callable[[str], list[Candidate]],
    *,
    max_workers: int,
    deadline_s: float | None = None,
) -> list[Candidate]:
    raise NotImplementedError
