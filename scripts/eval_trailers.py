"""Offline evaluation of `find_trailer` over the golden set (RED stub)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from trailer_search import Candidate, FilmProfile, TrailerRetriever

Outcome = Literal["hit", "wrong", "miss"]

_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
BASELINE_PATH = _FIXTURES / "trailer_baseline.json"


class GoldenSetError(ValueError):
    """Golden set is corrupt and cannot be measured."""


@dataclass
class GoldenCase:
    film: FilmProfile
    correct: str | list[str] | None
    candidates: list[Candidate]
    note: str
    trap: list[str] = field(default_factory=list)


@dataclass
class BaselineEntry:
    i: int
    film: str
    outcome: Outcome


@dataclass
class BaselineReport:
    moved: list[tuple[str, Outcome, Outcome]]

    @property
    def ok(self) -> bool:
        raise NotImplementedError

    @property
    def text(self) -> str:
        raise NotImplementedError


class FrozenRetriever:
    def __init__(self, pool: list[Candidate]) -> None:
        self.pool = pool

    def search_candidates(self, _profile: FilmProfile) -> list[Candidate]:
        raise NotImplementedError


def classify(correct: str | list[str] | None, pick_id: str | None) -> Outcome:
    raise NotImplementedError


def score(outcomes: list[Outcome]) -> int:
    raise NotImplementedError


def load_golden_set(path: str | Path) -> list[GoldenCase]:
    raise NotImplementedError


def evaluate(
    cases: list[GoldenCase],
    retriever_for: Callable[[GoldenCase], TrailerRetriever] | None = None,
) -> tuple[list[tuple[GoldenCase, str | None, Outcome]], int]:
    raise NotImplementedError


def build_baseline(
    rows: list[tuple[GoldenCase, str | None, Outcome]],
) -> list[BaselineEntry]:
    raise NotImplementedError


def load_baseline(path: str | Path) -> list[BaselineEntry]:
    raise NotImplementedError


def compare_to_baseline(
    baseline: list[BaselineEntry], rows: list[tuple[GoldenCase, str | None, Outcome]]
) -> BaselineReport:
    raise NotImplementedError


def main(
    argv: list[str] | None = None,
    *,
    make_retriever: Callable[[str], TrailerRetriever] | None = None,
) -> int:
    raise NotImplementedError
