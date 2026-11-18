"""Evaluation harness, ported from kinozal_scraper `test_eval_trailers.py` (40cd99d).

TMDB evaluation and the kinozal delivery run stay in kinozal; `tmdb_videos` is read only
as a source of accepted ids (design 8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.eval_trailers import (
    GOLDEN_PATH,
    FrozenRetriever,
    GoldenSetError,
    classify,
    evaluate,
    load_golden_set,
    main,
    score,
)
from trailer_search import Candidate, FilmProfile, TrailerRetriever


def _valid_case() -> dict[str, Any]:
    return {
        "film": {"ru_title": "Гнев", "original_title": "Man on Fire", "year": 2026},
        "correct": "abc",
        "candidates": [{"video_id": "abc", "title": "Гнев 2026 трейлер"}],
        "note": "",
    }


def _tmdb_video(key: str) -> dict[str, Any]:
    return {
        "key": key,
        "iso_639_1": "ru",
        "type": "Trailer",
        "official": True,
        "site": "YouTube",
    }


# ── classify / score ──────────────────────────────────────────────────────────


def test_classify_single_reference() -> None:
    assert classify("abc", "abc") == "hit"
    assert classify("abc", "xyz") == "wrong"
    assert classify("abc", None) == "miss"


def test_classify_null_reference_and_no_pick_is_hit() -> None:
    assert classify(None, None) == "hit"


def test_null_correct_with_pick_is_wrong() -> None:
    assert classify(None, "abc") == "wrong"


def test_classify_accept_set() -> None:
    assert classify(["a", "b"], "b") == "hit"
    assert classify(["a", "b"], "c") == "wrong"
    assert classify(["a", "b"], None) == "miss"


def test_weighted_score() -> None:
    assert score(["hit", "hit", "miss", "wrong"]) == 0


# ── load_golden_set: fail-loud validation ─────────────────────────────────────


def test_loads_valid_set(write: Any) -> None:
    (case,) = load_golden_set(write([_valid_case()]))
    assert case.correct == "abc"
    assert case.film.original_title == "Man on Fire"
    assert case.candidates[0].video_id == "abc"


def test_null_correct_loads(write: Any) -> None:
    case = _valid_case()
    case["correct"] = None
    assert load_golden_set(write([case]))[0].correct is None


def test_empty_set_errors(write: Any) -> None:
    with pytest.raises(GoldenSetError):
        load_golden_set(write([]))


@pytest.mark.parametrize("field", ["film", "correct", "candidates"])
def test_missing_field_errors(write: Any, field: str) -> None:
    case = _valid_case()
    del case[field]
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_duplicate_candidate_id_errors(write: Any) -> None:
    case = _valid_case()
    case["candidates"] = [
        {"video_id": "dup", "title": "a"},
        {"video_id": "dup", "title": "b"},
    ]
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_correct_wrong_type_errors(write: Any) -> None:
    case = _valid_case()
    case["correct"] = 123
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_accepts_list_correct(write: Any) -> None:
    case = _valid_case()
    case["correct"] = ["abc", "def"]
    case["candidates"] = [
        {"video_id": "abc", "title": "t1"},
        {"video_id": "def", "title": "t2"},
    ]
    assert load_golden_set(write([case]))[0].correct == ["abc", "def"]


@pytest.mark.parametrize("correct", [[], ["abc", 123]])
def test_rejects_bad_accept_set(write: Any, correct: list[Any]) -> None:
    case = _valid_case()
    case["correct"] = correct
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_accept_set_may_reference_tmdb_key_not_in_candidates(write: Any) -> None:
    case = _valid_case()
    case["correct"] = ["tmdbOnly"]
    case["tmdb_videos"] = [_tmdb_video("tmdbOnly")]
    assert load_golden_set(write([case]))[0].correct == ["tmdbOnly"]


def test_accept_id_outside_both_pools_errors(write: Any) -> None:
    case = _valid_case()
    case["correct"] = ["ghost"]
    case["tmdb_videos"] = [_tmdb_video("real")]
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_rejects_tmdb_video_without_key(write: Any) -> None:
    case = _valid_case()
    case["tmdb_videos"] = [{"iso_639_1": "ru", "type": "Trailer", "site": "YouTube"}]
    with pytest.raises(GoldenSetError):
        load_golden_set(write([case]))


def test_carries_film_metadata(write: Any) -> None:
    case = _valid_case()
    case["film"].update(
        cast=["Дензел Вашингтон"],
        director="Тони Скотт",
        genre="боевик",
        description="Сюжет.",
    )
    film = load_golden_set(write([case]))[0].film
    assert (film.cast, film.director, film.genre, film.description) == (
        ["Дензел Вашингтон"],
        "Тони Скотт",
        "боевик",
        "Сюжет.",
    )


# ── trap ──────────────────────────────────────────────────────────────────────


def _trap_case(**over: Any) -> dict[str, Any]:
    case: dict[str, Any] = {
        "film": {"ru_title": "Леший", "original_title": "", "year": 2026},
        "correct": ["ours"],
        "candidates": [
            {"video_id": "ours", "title": "Леший 2026 трейлер сериала"},
            {"video_id": "alien", "title": "Леший трейлер 2026"},
        ],
        "trap": ["alien"],
        "note": "",
    }
    case.update(over)
    return case


def test_trap_loads(write: Any) -> None:
    assert load_golden_set(write([_trap_case()]))[0].trap == ["alien"]


def test_absent_trap_defaults_to_empty(write: Any) -> None:
    case = _trap_case()
    del case["trap"]
    assert load_golden_set(write([case]))[0].trap == []


@pytest.mark.parametrize("trap", [["typo"], ["ours"], "alien", [1]])
def test_invalid_trap_errors(write: Any, trap: Any) -> None:
    with pytest.raises(GoldenSetError):
        load_golden_set(write([_trap_case(trap=trap)]))


# ── evaluation over find_trailer ──────────────────────────────────────────────


def test_committed_golden_set_scorecard() -> None:
    rows = evaluate(load_golden_set(GOLDEN_PATH))
    outcomes = [o for _, _, o in rows]
    assert (outcomes.count("hit"), outcomes.count("miss"), outcomes.count("wrong")) == (
        30,
        2,
        1,
    )
    assert score(outcomes) == 28


def test_138_ru_selection_is_fixed() -> None:
    cases = [c for c in load_golden_set(GOLDEN_PATH) if c.note.startswith("seed: #138")]
    assert cases
    rows = evaluate(cases)
    assert [o for _, _, o in rows] == ["hit"] * len(cases)


# ── --record ──────────────────────────────────────────────────────────────────


def test_record_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)
    built: list[str] = []

    def make_retriever(key: str) -> TrailerRetriever:
        built.append(key)
        return FrozenRetriever([])

    with pytest.raises(SystemExit) as excinfo:
        main(["--record", "--golden", str(GOLDEN_PATH)], make_retriever=make_retriever)
    assert excinfo.value.code not in (0, None)
    assert built == []


def test_record_fails_before_write_when_pinned_id_gone(
    write: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write(
        [
            {
                "film": {"ru_title": "Леший", "original_title": "", "year": 2026},
                "correct": ["keep"],
                "candidates": [{"video_id": "keep", "title": "Леший 2026 трейлер"}],
                "note": "",
            }
        ]
    )
    before = Path(path).read_text(encoding="utf-8")
    monkeypatch.setenv("API_KEY", "test-key")  # pragma: allowlist secret
    drifted = [Candidate(video_id="fresh", title="Леший 2026 трейлер")]
    seen: list[FilmProfile] = []

    class _Drifted:
        def search_candidates(self, profile: FilmProfile) -> list[Candidate]:
            seen.append(profile)
            return list(drifted)

    with pytest.raises(GoldenSetError) as excinfo:
        main(["--record", "--golden", path], make_retriever=lambda _key: _Drifted())
    assert "keep" in str(excinfo.value)
    assert [p.ru_title for p in seen] == ["Леший"]
    assert Path(path).read_text(encoding="utf-8") == before
