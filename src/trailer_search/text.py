"""Title text helpers, ported from kinozal_scraper `text_utils.py` (40cd99d)."""

from __future__ import annotations

import re


def title_year_matches(title: str, film_year: int) -> bool:
    """Return False if the video title explicitly mentions a year other than film_year."""
    title_years = {int(m) for m in re.findall(r"\b((?:19|20)\d{2})\b", title)}
    return not title_years or film_year in title_years


def normalize_title(s: str) -> str:
    """Lowercase and collapse non-alphanumeric runs to single spaces for substring
    title matching: `Dune: Part Two!` → `dune part two`."""
    return re.sub(r"[^0-9a-zа-яё]+", " ", s.lower()).strip()


def has_cyrillic(s: str) -> bool:
    """True if the string contains a Cyrillic letter: the cheap language signal that
    prefers a Russian trailer over an English one."""
    return bool(re.search(r"[а-яё]", s, re.IGNORECASE))
