"""Trailer selection over a candidate pool, ported from kinozal_scraper
`trailer_strategy.py` (40cd99d) without `FirstResultStrategy`."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

from trailer_search.text import (
    YEAR_PATTERN,
    has_cyrillic,
    normalize_title,
    title_season,
    title_year_matches,
)

logger = logging.getLogger(__name__)


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Word-boundary containment of an already normalized phrase."""
    return bool(re.search(rf"\b{re.escape(phrase)}\b", haystack))


def _is_sequel_number(token: str) -> bool:
    """A standalone sequel number, not a four-digit year (years discriminate in
    `title_year_matches` and must not be skipped)."""
    return token.isdigit() and not re.fullmatch(YEAR_PATTERN, token)


def _title_tokens_in(film_tokens: list[str], cand_tokens: list[str]) -> bool:
    """`film_tokens` occur consecutively and in order in `cand_tokens`, allowing one
    interspersed numeric sequel token between title tokens."""
    if not film_tokens:
        return False

    def aligns(start: int) -> bool:
        fi, ci, skipped = 0, start, False
        while fi < len(film_tokens) and ci < len(cand_tokens):
            if cand_tokens[ci] == film_tokens[fi]:
                fi += 1
                ci += 1
            elif fi > 0 and not skipped and _is_sequel_number(cand_tokens[ci]):
                skipped = True
                ci += 1
            else:
                break
        return fi == len(film_tokens)

    return any(aligns(s) for s in range(len(cand_tokens)))


@dataclass
class FilmProfile:
    """What selection knows about a film; `cast`/`director`/`genre`/`description`
    are optional metadata (cast in a candidate description breaks ties). `season`
    asks a series for that season's trailer; `year` is then the first season's year."""

    ru_title: str
    original_title: str
    year: int | None
    cast: list[str] = field(default_factory=list)
    director: str = ""
    genre: str = ""
    description: str = ""
    season: int | None = None

    def __post_init__(self) -> None:
        if self.season is not None and self.season < 1:
            raise ValueError(f"season must be >= 1, got {self.season}")


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
    """Strategy decision. `video_id=None` means no pick; `title` is the picked
    candidate's title; `reason` attributes the decision."""

    video_id: str | None
    title: str | None
    confidence: float
    reason: str


class TrailerStrategy(Protocol):
    def pick(
        self, film_profile: FilmProfile, candidates: list[Candidate]
    ) -> TrailerPick: ...


class HeuristicStrategy:
    """Deterministic language-aware selection.

    1. **relevance**: the candidate title contains `ru_title` or `original_title`
       (or `original_title` without its parenthesized edition suffix) tokens in order,
       allowing one numeric sequel token, and its year matches a truthy profile year
       (with a season: names no year earlier than the profile year).
    2. **ranking** by `(season_hit, is_ru, cast_hits, trailer_signal)`, descending
       and stable; a pick that misses the requested season gets a `season N fallback`
       reason suffix and a WARNING.

    A unique top rank is a confident pick (0.9); equal top ranks give the first in
    order with 0.3 and an `ambiguous` reason; no relevant candidate gives no pick."""

    _MAX_CAST = 2
    _TRAILER_WORDS = ("трейлер", "trailer", "дубляж")
    _TEASER_WORDS = ("тизер", "teaser")

    def pick(
        self, film_profile: FilmProfile, candidates: list[Candidate]
    ) -> TrailerPick:
        film_titles = self._film_titles(film_profile)
        relevant = [
            c for c in candidates if self._relevant(film_profile, film_titles, c)
        ]
        if not relevant:
            return TrailerPick(None, None, 0.0, "no title+year match")
        cast = [
            n
            for n in (normalize_title(x) for x in film_profile.cast[: self._MAX_CAST])
            if n
        ]
        season = film_profile.season
        keys = [self._rank(c, cast, season) for c in relevant]
        best_key = max(keys)  # first of the top rank, as a stable descending sort
        best = relevant[keys.index(best_key)]
        tied = keys.count(best_key)
        season_hit, is_ru, cast_hits, _trailer = best_key
        if tied > 1:
            confidence = 0.3
            reason = f"ambiguous: {tied} candidates share top rank"
        else:
            confidence = 0.9
            reason = (
                "cast tie-break"
                if cast_hits
                else ("ru language" if is_ru else "sole match")
            )
        if season is not None and not season_hit:
            logger.warning(
                "no season %d trailer for %r; falling back to %r",
                season,
                film_profile.ru_title,
                best.title,
            )
            reason += f"; season {season} fallback"
        return TrailerPick(best.video_id, best.title, confidence, reason)

    @staticmethod
    def _film_titles(profile: FilmProfile) -> list[list[str]]:
        """Title token variants. The edition-less `original_title` variant is an equal
        alternative, not a fallback; only `original_title` is trimmed at `(` because a
        Russian parenthesis may qualify a part or season."""
        titles = [
            profile.ru_title,
            profile.original_title,
            profile.original_title.split("(")[0],
        ]
        return [normalize_title(t).split() for t in titles]

    def _relevant(
        self, profile: FilmProfile, film_titles: list[list[str]], candidate: Candidate
    ) -> bool:
        """Title-and-year match against the `_film_titles` variants."""
        cand_tokens = normalize_title(candidate.title).split()
        if not any(_title_tokens_in(t, cand_tokens) for t in film_titles):
            return False
        return not profile.year or title_year_matches(
            candidate.title, profile.year, at_least=profile.season is not None
        )

    def _rank(
        self, candidate: Candidate, cast: list[str], season: int | None
    ) -> tuple[int, int, int, int]:
        description = normalize_title(candidate.description)
        cast_hits = sum(1 for name in cast if _contains_phrase(description, name))
        named = title_season(candidate.title) if season is not None else None
        season_hit = season is not None and (
            named == season or (named is None and season == 1)
        )
        return (
            int(season_hit),
            int(has_cyrillic(candidate.title)),
            cast_hits,
            self._trailer_signal(candidate),
        )

    def _trailer_signal(self, candidate: Candidate) -> int:
        """Trailer/dub words +1 each, teaser words −1 each."""
        title = normalize_title(candidate.title)
        return sum(w in title for w in self._TRAILER_WORDS) - sum(
            w in title for w in self._TEASER_WORDS
        )
