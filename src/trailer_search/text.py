"""Title text helpers, ported from kinozal_scraper `text_utils.py` (40cd99d)."""

from __future__ import annotations

import re

YEAR_PATTERN = r"(?:19|20)\d{2}"


# Season markers on a `normalize_title` string: `2 сезон`, `2 й сезон`, `сезон 2`,
# `season 2`, `s02`.
_SEASON_RE = re.compile(
    r"\b(?:(\d{1,2}) (?:й )?сезон|(?:сезон|season) (\d{1,2})|s(\d{2}))\b"
)
# Series markers (design 3): a season marker, a word beginning with `сериал`, the word `series`.
_SERIES_RE = re.compile(rf"{_SEASON_RE.pattern}|\bсериал|\bseries\b")


def title_year_matches(title: str, film_year: int, *, at_least: bool = False) -> bool:
    """Return False if the video title names years but neither film_year nor the year
    after it (the release year of a film profiled by production year), or, with
    `at_least`, a year earlier than film_year."""
    title_years = {int(m) for m in re.findall(rf"\b({YEAR_PATTERN})\b", title)}
    if at_least:
        return all(y >= film_year for y in title_years)
    return not title_years or bool(title_years & {film_year, film_year + 1})


def title_season(title: str) -> int | None:
    """The season number a video title names, or None when it names none."""
    m = _SEASON_RE.search(normalize_title(title))
    return int(next(g for g in m.groups() if g)) if m else None


def title_is_series(title: str) -> bool:
    """True when a video title carries a series marker."""
    return bool(_SERIES_RE.search(normalize_title(title)))


def normalize_title(s: str) -> str:
    """Lowercase and collapse non-alphanumeric runs to single spaces for substring
    title matching: `Dune: Part Two!` → `dune part two`."""
    return re.sub(r"[^0-9a-zа-яё]+", " ", s.lower()).strip()


def has_cyrillic(s: str) -> bool:
    """True if the string contains a Cyrillic letter: the cheap language signal that
    prefers a Russian trailer over an English one."""
    return bool(re.search(r"[а-яё]", s, re.IGNORECASE))
