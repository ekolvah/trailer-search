"""Baseline gate over `find_trailer`, ported from kinozal_scraper `test_eval_baseline.py` (40cd99d).

The committed baseline is kinozal's own (design 9): a green gate proves per-case parity
with kinozal, and any moved case — regression or improvement — turns it red.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.eval_trailers import (
    BASELINE_PATH,
    FrozenRetriever,
    GoldenCase,
    GoldenSetError,
    Outcome,
    build_baseline,
    classify,
    compare_to_baseline,
    evaluate,
    load_baseline,
    load_golden_set,
)

GOLDEN_PATH = Path(__file__).parent / "fixtures" / "trailer_golden.json"


@pytest.fixture
def write(tmp_path: Path) -> Any:
    counter = iter(range(100))

    def _write(data: Any) -> str:
        path = tmp_path / f"f{next(counter)}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)

    return _write


@pytest.fixture
def mini_rows(write: Any) -> list[tuple[GoldenCase, str | None, Outcome]]:
    """A two-case set: one hit and one miss."""
    cases = load_golden_set(
        write(
            [
                {
                    "film": {
                        "ru_title": "Гнев",
                        "original_title": "Man on Fire",
                        "year": 2026,
                    },
                    "correct": "ru01",
                    "candidates": [{"video_id": "ru01", "title": "Гнев 2026 трейлер"}],
                    "note": "",
                },
                {
                    "film": {
                        "ru_title": "Волк",
                        "original_title": "Wolf",
                        "year": 2026,
                    },
                    "correct": "ru02",
                    "candidates": [],
                    "note": "",
                },
            ]
        )
    )
    rows, _ = evaluate(cases)
    return rows


def test_match_reports_ok(
    mini_rows: list[tuple[GoldenCase, str | None, Outcome]],
) -> None:
    report = compare_to_baseline(build_baseline(mini_rows), mini_rows)
    assert report.ok, report.text


def test_improvement_also_not_ok(
    mini_rows: list[tuple[GoldenCase, str | None, Outcome]],
) -> None:
    improved: list[tuple[GoldenCase, str | None, Outcome]] = [
        (case, "ru01", "hit") for case, _, _ in mini_rows
    ]
    report = compare_to_baseline(build_baseline(mini_rows), improved)
    assert not report.ok
    assert "--update-baseline" in report.text


def test_desynced_length_fails_loud(
    mini_rows: list[tuple[GoldenCase, str | None, Outcome]],
) -> None:
    with pytest.raises(GoldenSetError):
        compare_to_baseline(build_baseline(mini_rows)[:1], mini_rows)


def test_desynced_film_name_fails_loud(
    mini_rows: list[tuple[GoldenCase, str | None, Outcome]],
) -> None:
    baseline = build_baseline(mini_rows)
    baseline[0].film = "Совсем другой фильм"
    with pytest.raises(GoldenSetError):
        compare_to_baseline(baseline, mini_rows)


@pytest.mark.parametrize(
    "entry", [{"i": 0, "film": "Гнев"}, {"i": 0, "film": "Гнев", "outcome": "maybe"}]
)
def test_load_baseline_rejects_malformed_entry(
    write: Any, entry: dict[str, Any]
) -> None:
    with pytest.raises(GoldenSetError):
        load_baseline(write([entry]))


def test_golden_set_keeps_verified_traps() -> None:
    marked = [c.film.ru_title for c in load_golden_set(GOLDEN_PATH) if c.trap]
    assert len(marked) >= 3, marked


def test_trap_pick_classifies_as_wrong() -> None:
    for case in (c for c in load_golden_set(GOLDEN_PATH) if c.trap):
        for trap_id in case.trap:
            assert classify(case.correct, trap_id) == "wrong", (
                case.film.ru_title,
                trap_id,
            )


def test_committed_baseline_matches() -> None:
    rows, _ = evaluate(load_golden_set(GOLDEN_PATH))
    baseline = load_baseline(BASELINE_PATH)
    report = compare_to_baseline(baseline, rows)
    assert report.ok, report.text
    outcomes = [e.outcome for e in baseline]
    assert (outcomes.count("hit"), outcomes.count("miss"), outcomes.count("wrong")) == (
        29,
        2,
        1,
    )


def test_regressed_selection_is_named() -> None:
    cases = load_golden_set(GOLDEN_PATH)
    rows, _ = evaluate(cases, retriever_for=lambda _case: FrozenRetriever([]))
    report = compare_to_baseline(load_baseline(BASELINE_PATH), rows)
    assert not report.ok
    assert "hit→miss" in report.text
    assert repr(cases[0].film.ru_title) in report.text
