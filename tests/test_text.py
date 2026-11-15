"""Title helpers ported from kinozal_scraper `text_utils` (40cd99d)."""

from __future__ import annotations

from trailer_search.text import has_cyrillic, normalize_title, title_year_matches


def test_normalize_strips_punctuation_and_lowercases() -> None:
    assert normalize_title("Dune: Part Two!") == "dune part two"


def test_normalize_keeps_cyrillic() -> None:
    assert "волк" in normalize_title("Волк, 2025")


def test_has_cyrillic_true_for_russian() -> None:
    assert has_cyrillic("Волк трейлер")


def test_has_cyrillic_false_for_latin() -> None:
    assert not has_cyrillic("The Wolf trailer")


def test_title_without_year_matches_any_year() -> None:
    assert title_year_matches("Dune Official Trailer", 2021)


def test_title_with_film_year_matches() -> None:
    assert title_year_matches("Dune 2021 Trailer", 2021)


def test_title_with_other_year_does_not_match() -> None:
    assert not title_year_matches("Dune 2024 Trailer", 2021)
