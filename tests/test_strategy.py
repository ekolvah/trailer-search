"""`HeuristicStrategy`, ported from kinozal_scraper `test_trailer_strategy.py` (40cd99d).

Ranking: language is primary (RU > EN), cast in `description` breaks ties within one
language, trailer words minus teaser words come third. A shared top rank picks the first
in pool order with low confidence and an `ambiguous` reason.
"""

from __future__ import annotations

import logging

import pytest

from trailer_search.strategy import (
    Candidate,
    FilmProfile,
    HeuristicStrategy,
    TrailerPick,
)


def _pick(film: FilmProfile, cands: list[Candidate]) -> TrailerPick:
    return HeuristicStrategy().pick(film, cands)


# ── scenario tests ────────────────────────────────────────────────────────────


def test_no_relevant_candidate() -> None:
    film = FilmProfile(ru_title="Волк", original_title="The Wolf", year=2025)
    pick = _pick(
        film, [Candidate(video_id="x", title="Completely Different Movie 2025")]
    )
    assert pick == TrailerPick(None, None, 0.0, "no title+year match")


def test_other_year_excluded() -> None:
    film = FilmProfile(ru_title="Забвение", original_title="Oblivion", year=2026)
    assert (
        _pick(film, [Candidate(video_id="old", title="Oblivion 2019 Trailer")]).video_id
        is None
    )


def test_release_year_admitted() -> None:
    film = FilmProfile(ru_title="Коммерсант", original_title="Коммерсант", year=2025)
    cands = [Candidate(video_id="ru", title="Коммерсант - Трейлер 2026")]
    assert _pick(film, cands).video_id == "ru"


def test_edition_suffix_ignored() -> None:
    film = FilmProfile(
        ru_title="Marvel Человек-Паук 2",
        original_title="Marvel's Spider-Man 2 (Digital Deluxe Edition)",
        year=2025,
    )
    cands = [Candidate(video_id="ps5", title="Marvel's Spider-Man 2 Official Trailer")]
    assert _pick(film, cands).video_id == "ps5"


def test_sequel_number_skipped() -> None:
    film = FilmProfile(ru_title="Шрэк навсегда", original_title="", year=2010)
    cands = [Candidate(video_id="s", title="Шрэк 4 навсегда трейлер")]
    assert _pick(film, cands).video_id == "s"


def test_year_not_skipped() -> None:
    film = FilmProfile(ru_title="Шрэк навсегда", original_title="", year=2010)
    cands = [Candidate(video_id="s", title="Шрэк 2010 навсегда трейлер")]
    assert _pick(film, cands).video_id is None


def test_ru_beats_en() -> None:
    film = FilmProfile(ru_title="Волк", original_title="The Wolf", year=2025)
    cands = [
        Candidate(video_id="eng", title="The Wolf 2025 Official Trailer"),
        Candidate(video_id="ru", title="Волк 2025 трейлер на русском"),
    ]
    pick = _pick(film, cands)
    assert (pick.video_id, pick.title, pick.confidence) == (
        "ru",
        "Волк 2025 трейлер на русском",
        0.9,
    )


def test_trailer_beats_teaser() -> None:
    film = FilmProfile(ru_title="Ярость", original_title="", year=2026)
    cands = [
        Candidate(video_id="teaser", title="Ярость 2026 тизер"),
        Candidate(video_id="trailer", title="Ярость 2026 трейлер"),
    ]
    assert _pick(film, cands).video_id == "trailer"


def test_tie_is_ambiguous() -> None:
    film = FilmProfile(ru_title="Барби", original_title="Barbie", year=2023)
    cands = [
        Candidate(video_id="main", title="Barbie 2023 Official Trailer"),
        Candidate(video_id="second", title="Barbie 2023 Final Trailer"),
    ]
    pick = _pick(film, cands)
    assert (pick.video_id, pick.confidence) == ("main", 0.3)
    assert pick.reason.startswith("ambiguous")


# ── ported regression tests ───────────────────────────────────────────────────


def test_prefers_ru_among_multiple_eng() -> None:
    film = FilmProfile(ru_title="Хищник", original_title="Predator", year=2025)
    cands = [
        Candidate(video_id="eng1", title="Predator 2025 Official Trailer"),
        Candidate(video_id="eng2", title="Predator 2025 Final Trailer"),
        Candidate(video_id="ru", title="Хищник 2025 официальный трейлер"),
    ]
    assert _pick(film, cands).video_id == "ru"


def test_ru_beats_eng_even_when_eng_has_cast() -> None:
    film = FilmProfile(
        ru_title="Волк", original_title="The Wolf", year=2025, cast=["John Smith"]
    )
    cands = [
        Candidate(
            video_id="eng",
            title="The Wolf 2025 Reaction",
            description="John Smith reacts to the trailer",
        ),
        Candidate(video_id="ru", title="Волк 2025 трейлер", description=""),
    ]
    assert _pick(film, cands).video_id == "ru"


def test_cast_breaks_tie_within_same_language() -> None:
    film = FilmProfile(
        ru_title="Ярость", original_title="Ярость", year=2026, cast=["Иван Петров"]
    )
    cands = [
        Candidate(
            video_id="react", title="Ярость 2026 трейлер разбор", description="обзор"
        ),
        Candidate(
            video_id="cast",
            title="Ярость 2026 официальный трейлер",
            description="В главной роли Иван Петров",
        ),
    ]
    assert _pick(film, cands).video_id == "cast"


def test_single_match_is_confident() -> None:
    film = FilmProfile(ru_title="Оппенгеймер", original_title="Oppenheimer", year=2023)
    pick = _pick(
        film, [Candidate(video_id="o", title="Oppenheimer 2023 Official Trailer")]
    )
    assert pick.video_id == "o"
    assert pick.confidence >= 0.7


def test_numbered_sequel_relevance_match() -> None:
    film = FilmProfile(
        ru_title="Джокер: Безумие на двоих",
        original_title="Joker: Folie à Deux",
        year=2024,
    )
    cands = [
        Candidate(
            video_id="ru_trailer",
            title="Джокер 2: Безумие на двоих — Русский трейлер (2024)",
        )
    ]
    assert _pick(film, cands).video_id == "ru_trailer"


def test_base_title_does_not_crossmatch_sequel() -> None:
    film = FilmProfile(ru_title="Дюна", original_title="Dune", year=2021)
    cands = [
        Candidate(
            video_id="sequel", title="Дюна: Часть вторая — Русский трейлер (2024)"
        )
    ]
    assert _pick(film, cands).video_id is None


def test_tiebreak_prefers_trailer_over_news_clip() -> None:
    film = FilmProfile(
        ru_title="Джокер: Безумие на двоих",
        original_title="Joker: Folie à Deux",
        year=2024,
    )
    cands = [
        Candidate(
            video_id="news",
            title="🃏 Вышел тизер-трейлер фильма «Джокер: Безумие на двоих»",
        ),
        Candidate(
            video_id="trailer",
            title="Джокер: Безумие на двоих — Русский трейлер (Дубляж, 2024)",
        ),
    ]
    assert _pick(film, cands).video_id == "trailer"


def test_short_title_not_matched_inside_word() -> None:
    film = FilmProfile(ru_title="Дом", original_title="Home", year=2026)
    cands = [Candidate(video_id="x", title="Домашний питомец 2026 трейлер")]
    assert _pick(film, cands).video_id is None


def test_no_year_matches_by_title() -> None:
    film = FilmProfile(ru_title="Дюна", original_title="Dune", year=None)
    assert (
        _pick(film, [Candidate(video_id="d", title="Dune Official Trailer")]).video_id
        == "d"
    )


def test_bracket_in_ru_title_not_collapsed_to_franchise() -> None:
    film = FilmProfile(
        ru_title="Дюна (Часть вторая)", original_title="Dune: Part Two", year=None
    )
    cands = [
        Candidate(video_id="right", title="Dune: Part Two | Official Trailer"),
        Candidate(video_id="wrong", title="Дюна 2 — русский трейлер"),
    ]
    assert _pick(film, cands).video_id == "right"


def test_edition_in_candidate_title_does_not_win_over_trailer() -> None:
    film = FilmProfile(
        ru_title="Marvel Человек-Паук 2",
        original_title="Marvel's Spider-Man 2 (Digital Deluxe Edition)",
        year=2025,
    )
    cands = [
        Candidate(
            video_id="suits",
            title="All Marvel's Spider-Man 2 Digital Deluxe Edition Suits",
        ),
        Candidate(
            video_id="real", title="Marvel's Spider-Man 2 - Launch Trailer | PC Games"
        ),
    ]
    assert _pick(film, cands).video_id == "real"


# ── series season (series-season-trailer) ─────────────────────────────────────


def _gentlemen(season: int) -> FilmProfile:
    return FilmProfile(
        ru_title="Джентльмены",
        original_title="The Gentlemen",
        year=2024,
        season=season,
    )


def test_season_candidate_passes_later_year() -> None:
    title = "Джентльмены (2 сезон) - Русский трейлер (Дубляж, 2026) Гай Ричи"
    pick = _pick(_gentlemen(2), [Candidate(video_id="s2", title=title)])
    assert pick.video_id == "s2"


def test_season_rejects_earlier_year() -> None:
    cands = [Candidate(video_id="old", title="The Gentlemen 2019 Official Trailer")]
    assert _pick(_gentlemen(2), cands).video_id is None


def test_requested_season_beats_earlier() -> None:
    cands = [
        Candidate(
            video_id="s1", title="Джентльмены (1 сезон) — Русский трейлер (4К, 2024)"
        ),
        Candidate(
            video_id="s2", title="The Gentlemen: Season 2 | Official Trailer | Netflix"
        ),
    ]
    pick = _pick(_gentlemen(2), cands)
    assert (pick.video_id, pick.confidence) == ("s2", 0.9)


@pytest.mark.parametrize(
    "title",
    [
        "ДЖЕНТЛЬМЕНЫ 2 СЕЗОН | Трейлер",
        "Джентльмены · 2-й сезон · Трейлер",
        "Джентльмены. Сезон 2 — трейлер",
        "The Gentlemen Season 2 Trailer",
        "The Gentlemen S02 Trailer",
    ],
)
def test_season_markers_recognised(title: str) -> None:
    cands = [
        Candidate(video_id="s1", title="Джентльмены (1 сезон) — Русский трейлер"),
        Candidate(video_id="s2", title=title),
    ]
    assert _pick(_gentlemen(2), cands).video_id == "s2"


def test_season_1_accepts_unmarked() -> None:
    cands = [
        Candidate(video_id="s2", title="Джентльмены (2 сезон) — Русский трейлер"),
        Candidate(video_id="plain", title="Джентльмены — Русский трейлер"),
    ]
    pick = _pick(_gentlemen(1), cands)
    assert pick.video_id == "plain"
    assert "fallback" not in pick.reason


def test_missing_season_falls_back_visibly(caplog: pytest.LogCaptureFixture) -> None:
    cands = [Candidate(video_id="s2", title="Джентльмены (2 сезон) — Русский трейлер")]
    with caplog.at_level(logging.WARNING, logger="trailer_search"):
        pick = _pick(_gentlemen(3), cands)
    assert pick.video_id == "s2"
    assert pick.reason.endswith("; season 3 fallback")
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Джентльмены" in w and "3" in w for w in warnings), warnings


@pytest.mark.parametrize("season", [0, -1])
def test_invalid_season_rejected(season: int) -> None:
    with pytest.raises(ValueError):
        _gentlemen(season)
