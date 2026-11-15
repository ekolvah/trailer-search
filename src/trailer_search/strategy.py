"""Trailer selection over a candidate pool (RED stub)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FilmProfile:
    """What selection knows about a film."""

    ru_title: str
    original_title: str
    year: int | None
    cast: list[str] = field(default_factory=list)
    director: str = ""
    genre: str = ""
    description: str = ""


@dataclass
class Candidate:
    """One YouTube search result."""

    video_id: str
    title: str
    channel: str = ""
    description: str = ""
    published_at: str = ""


@dataclass
class TrailerPick:
    """Strategy decision; `video_id=None` means no pick."""

    video_id: str | None
    confidence: float
    reason: str


class HeuristicStrategy:
    """Title+year relevance, then ranking."""

    def pick(self, film: FilmProfile, candidates: list[Candidate]) -> TrailerPick:
        raise NotImplementedError
