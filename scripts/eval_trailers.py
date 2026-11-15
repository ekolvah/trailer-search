#!/usr/bin/env python3
"""Trailer-selection evaluation, ported from kinozal_scraper `scripts/eval_trailers.py`
(40cd99d) without the TMDB and delivery runs.

Runs `find_trailer` over the FROZEN candidate pools of the golden set
(`tests/fixtures/trailer_golden.json`, no network), classifies each film hit/wrong/miss
against `correct`, prints a weighted scorecard and compares per-case outcomes with
`tests/fixtures/trailer_baseline.json`; the gate is `tests/test_eval_baseline.py`.

`correct` is one id, an accept set (`list[str]` of equivalent RU dubs) or null. A corrupt
record raises `GoldenSetError`, never degrades to a miss. `--record` (dev-only, live)
rebuilds the pools through `YoutubeApiRetriever`; a missing `API_KEY` fails fast.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

# Standalone-run bootstrap: mirror pytest's pythonpath=["src"] without an install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trailer_search import (  # noqa: E402
    Candidate,
    FilmProfile,
    TrailerRetriever,
    find_trailer,
)

Outcome = Literal["hit", "wrong", "miss"]
Row = tuple["GoldenCase", str | None, Outcome]

_SCORE: dict[Outcome, int] = {"hit": 1, "miss": 0, "wrong": -2}
_OUTCOMES: tuple[Outcome, ...] = ("hit", "wrong", "miss")

_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
_DEFAULT_GOLDEN = _FIXTURES / "trailer_golden.json"
BASELINE_PATH = _FIXTURES / "trailer_baseline.json"


class GoldenSetError(ValueError):
    """Golden set or baseline is corrupt and cannot be measured."""


@dataclass
class GoldenCase:
    film: FilmProfile
    correct: str | list[str] | None
    candidates: list[Candidate]
    note: str
    # Pool candidates verified as another work; `classify` marks picking one wrong.
    trap: list[str] = field(default_factory=list)


def classify(correct: str | list[str] | None, pick_id: str | None) -> Outcome:
    """Null `correct` with no pick is a hit and any pick is wrong; otherwise a hit
    means the pick is in the accept set."""
    if correct is None:
        return "hit" if pick_id is None else "wrong"
    if pick_id is None:
        return "miss"
    accept = {correct} if isinstance(correct, str) else set(correct)
    return "hit" if pick_id in accept else "wrong"


def score(outcomes: list[Outcome]) -> int:
    """Hit +1 / miss 0 / wrong −2: an unrelated trailer is worse than an honest miss."""
    return sum(_SCORE[o] for o in outcomes)


# ── golden-set loading (fail-loud) ────────────────────────────────────────────


def _require(entry: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    for key in keys:
        if key not in entry:
            raise GoldenSetError(f"{where}: missing required field {key!r}")


def _parse_film(raw: Any, where: str) -> FilmProfile:
    if not isinstance(raw, dict):
        raise GoldenSetError(
            f"{where}: 'film' must be an object, got {type(raw).__name__}"
        )
    _require(raw, ("ru_title", "original_title", "year"), f"{where}.film")
    year = raw["year"]
    if year is not None and not isinstance(year, int):
        raise GoldenSetError(
            f"{where}.film: 'year' must be int or null, got {type(year).__name__}"
        )
    cast = raw.get("cast", [])
    if not isinstance(cast, list):
        raise GoldenSetError(
            f"{where}.film: 'cast' must be a list, got {type(cast).__name__}"
        )
    return FilmProfile(
        ru_title=raw["ru_title"],
        original_title=raw["original_title"],
        year=year,
        cast=cast,
        director=raw.get("director", ""),
        genre=raw.get("genre", ""),
        description=raw.get("description", ""),
    )


def _parse_candidates(raw: Any, where: str) -> list[Candidate]:
    if not isinstance(raw, list):
        raise GoldenSetError(
            f"{where}: 'candidates' must be a list, got {type(raw).__name__}"
        )
    seen: set[str] = set()
    out: list[Candidate] = []
    for j, cand in enumerate(raw):
        spot = f"{where}.candidates[{j}]"
        if not isinstance(cand, dict):
            raise GoldenSetError(
                f"{spot}: candidate must be an object, got {type(cand).__name__}"
            )
        _require(cand, ("video_id", "title"), spot)
        vid = cand["video_id"]
        if vid in seen:
            raise GoldenSetError(f"{spot}: duplicate candidate video_id {vid!r}")
        seen.add(vid)
        out.append(
            Candidate(
                video_id=vid,
                title=cand["title"],
                channel=cand.get("channel", ""),
                description=cand.get("description", ""),
                published_at=cand.get("published_at", ""),
            )
        )
    return out


def _parse_tmdb_keys(raw: Any, where: str) -> set[str]:
    """`tmdb_videos` is read only as a source of accepted ids for `correct`."""
    if not isinstance(raw, list):
        raise GoldenSetError(
            f"{where}: 'tmdb_videos' must be a list, got {type(raw).__name__}"
        )
    keys: set[str] = set()
    for j, vid in enumerate(raw):
        spot = f"{where}.tmdb_videos[{j}]"
        if not isinstance(vid, dict) or not isinstance(vid.get("key"), str):
            raise GoldenSetError(f"{spot}: video must be an object with a str 'key'")
        keys.add(vid["key"])
    return keys


def _parse_correct(raw: Any, valid_ids: set[str], where: str) -> str | list[str] | None:
    """str | non-empty accept set of ids found among candidates or TMDB keys | null."""
    if raw is None or isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        if not raw:
            raise GoldenSetError(
                f"{where}: 'correct' accept-set must be non-empty (use null for 'no trailer')"
            )
        for k, el in enumerate(raw):
            if not isinstance(el, str):
                raise GoldenSetError(
                    f"{where}: 'correct'[{k}] must be str, got {type(el).__name__}"
                )
            if el not in valid_ids:
                raise GoldenSetError(
                    f"{where}: 'correct' id {el!r} not among candidate/tmdb video_ids"
                )
        return raw
    raise GoldenSetError(
        f"{where}: 'correct' must be str, list[str] or null, got {type(raw).__name__}"
    )


def _parse_trap(
    raw: Any, pool_ids: set[str], correct: str | list[str] | None, where: str
) -> list[str]:
    """Trap ids must be in the candidate pool and outside the accept set."""
    if not isinstance(raw, list):
        raise GoldenSetError(
            f"{where}: 'trap' must be a list, got {type(raw).__name__}"
        )
    accept: set[str] = set()
    if isinstance(correct, str):
        accept = {correct}
    elif isinstance(correct, list):
        accept = set(correct)
    out: list[str] = []
    for j, vid in enumerate(raw):
        if not isinstance(vid, str):
            raise GoldenSetError(
                f"{where}: 'trap'[{j}] must be str, got {type(vid).__name__}"
            )
        if vid not in pool_ids:
            raise GoldenSetError(
                f"{where}: 'trap' id {vid!r} not among candidate video_ids"
            )
        if vid in accept:
            raise GoldenSetError(
                f"{where}: 'trap' id {vid!r} is also in the accept-set"
            )
        out.append(vid)
    return out


def _parse_case(raw: Any, where: str) -> GoldenCase:
    if not isinstance(raw, dict):
        raise GoldenSetError(
            f"{where}: case must be an object, got {type(raw).__name__}"
        )
    _require(raw, ("film", "correct", "candidates"), where)
    candidates = _parse_candidates(raw["candidates"], where)
    pool_ids = {c.video_id for c in candidates}
    valid_ids = pool_ids | _parse_tmdb_keys(raw.get("tmdb_videos", []), where)
    correct = _parse_correct(raw["correct"], valid_ids, where)
    return GoldenCase(
        film=_parse_film(raw["film"], where),
        correct=correct,
        candidates=candidates,
        note=raw.get("note", ""),
        trap=_parse_trap(raw.get("trap", []), pool_ids, correct, where),
    )


def load_golden_set(path: str | Path) -> list[GoldenCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        kind = type(raw).__name__ if not isinstance(raw, list) else "empty list"
        raise GoldenSetError(
            f"{path}: golden set must be a non-empty list (got {kind})"
        )
    return [_parse_case(entry, f"{path}[{i}]") for i, entry in enumerate(raw)]


# ── evaluation over find_trailer ──────────────────────────────────────────────


class FrozenRetriever:
    """Returns a recorded pool: the network boundary is replaced, `find_trailer` is real."""

    def __init__(self, pool: list[Candidate]) -> None:
        self._pool = pool

    def search_candidates(self, _profile: FilmProfile) -> list[Candidate]:
        return list(self._pool)


def _frozen(case: GoldenCase) -> TrailerRetriever:
    return FrozenRetriever(case.candidates)


def evaluate(
    cases: list[GoldenCase],
    retriever_for: Callable[[GoldenCase], TrailerRetriever] = _frozen,
) -> tuple[list[Row], int]:
    rows: list[Row] = []
    for case in cases:
        pick = find_trailer(case.film, retriever_for(case))
        rows.append((case, pick.video_id, classify(case.correct, pick.video_id)))
    return rows, score([o for _, _, o in rows])


# ── baseline ratchet ──────────────────────────────────────────────────────────


@dataclass
class BaselineEntry:
    """Pinned outcome of one case; `i` accompanies `film` because titles repeat."""

    i: int
    film: str
    outcome: Outcome


@dataclass
class BaselineReport:
    """Comparison verdict shared by the gate test and the CLI."""

    moved: list[tuple[str, Outcome, Outcome]]
    baseline_score: int
    current_score: int
    n: int

    @property
    def ok(self) -> bool:
        return not self.moved

    @property
    def text(self) -> str:
        if self.ok:
            return f"baseline: match (score={self.current_score}, n={self.n})"
        delta = self.current_score - self.baseline_score
        lines = [
            f"baseline: MISMATCH (score {self.baseline_score} → {self.current_score}, "
            f"Δ{delta:+d}), moved cases: {len(self.moved)}"
        ]
        lines += [f"  {film!r} {was}→{now}" for film, was, now in self.moved]
        lines.append(
            "if the change is intended, update the fixture: "
            "python scripts/eval_trailers.py --update-baseline (the diff goes into the PR)"
        )
        return "\n".join(lines)


def build_baseline(rows: list[Row]) -> list[BaselineEntry]:
    return [
        BaselineEntry(i, case.film.ru_title, o) for i, (case, _, o) in enumerate(rows)
    ]


def load_baseline(path: str | Path) -> list[BaselineEntry]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise GoldenSetError(f"{path}: baseline must be a non-empty list")
    out: list[BaselineEntry] = []
    for j, entry in enumerate(raw):
        where = f"{path}[{j}]"
        if not isinstance(entry, dict):
            raise GoldenSetError(f"{where}: entry must be an object")
        _require(entry, ("i", "film", "outcome"), where)
        outcome = next((o for o in _OUTCOMES if o == entry["outcome"]), None)
        if outcome is None:
            raise GoldenSetError(f"{where}: unknown outcome {entry['outcome']!r}")
        out.append(BaselineEntry(i=entry["i"], film=entry["film"], outcome=outcome))
    return out


def save_baseline(path: str | Path, entries: list[BaselineEntry]) -> None:
    payload = [{"i": e.i, "film": e.film, "outcome": e.outcome} for e in entries]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def compare_to_baseline(
    baseline: list[BaselineEntry], rows: list[Row]
) -> BaselineReport:
    """Any moved case is red, an improvement included; a desynced baseline raises
    instead of comparing different films."""
    if len(baseline) != len(rows):
        raise GoldenSetError(
            f"baseline out of sync: {len(baseline)} entries vs {len(rows)} cases — "
            "regenerate with --update-baseline"
        )
    moved: list[tuple[str, Outcome, Outcome]] = []
    for i, (entry, (case, _, outcome)) in enumerate(zip(baseline, rows, strict=True)):
        if entry.i != i or entry.film != case.film.ru_title:
            raise GoldenSetError(
                f"baseline out of sync at position {i}: expected {case.film.ru_title!r} "
                f"(i={i}), baseline has {entry.film!r} (i={entry.i})"
            )
        if entry.outcome != outcome:
            moved.append((case.film.ru_title, entry.outcome, outcome))
    return BaselineReport(
        moved=moved,
        baseline_score=score([e.outcome for e in baseline]),
        current_score=score([o for _, _, o in rows]),
        n=len(rows),
    )


def _print_scorecard(rows: list[Row], total: int) -> None:
    tally: dict[Outcome, int] = {"hit": 0, "wrong": 0, "miss": 0}
    for case, pick_id, outcome in rows:
        tally[outcome] += 1
        trap = " TRAP" if pick_id is not None and pick_id in case.trap else ""
        print(
            f"  {outcome.upper():5}{trap} {case.film.ru_title!r} → "
            f"pick={pick_id!r} correct={case.correct!r}"
        )
    print(
        f"score={total}  hit={tally['hit']} miss={tally['miss']} wrong={tally['wrong']} "
        f"(n={len(rows)})"
    )


# ── --record (dev-only, live) ─────────────────────────────────────────────────


def _require_api_key() -> str:
    key = os.environ.get("API_KEY")
    if not key:
        raise SystemExit(
            "--record requires API_KEY (dev-only live mode); refusing to run"
        )
    return key


def _youtube_api_retriever(key: str) -> TrailerRetriever:
    from trailer_search.youtube_api import YoutubeApiRetriever  # noqa: PLC0415 — the extra loads only for --record

    return YoutubeApiRetriever(key)


def _record(
    golden_path: str | Path, make_retriever: Callable[[str], TrailerRetriever]
) -> int:
    """Rebuild the candidate pools. A retrieval failure propagates, so a quota failure is
    never recorded as an empty pool; the fresh payload is revalidated before the single
    write, so a drifted pool that drops a pinned id fails without touching the file."""
    key = _require_api_key()
    cases = load_golden_set(golden_path)
    retriever = make_retriever(key)
    raw = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    for entry, case in zip(raw, cases, strict=True):
        entry["candidates"] = [
            asdict(c) for c in retriever.search_candidates(case.film)
        ]
    for i, entry in enumerate(raw):
        _parse_case(entry, f"{golden_path}[{i}] (fresh pool)")
    Path(golden_path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"recorded candidates for {len(cases)} films → {golden_path}")
    return 0


def _ensure_utf8_stdout() -> None:
    """The scorecard prints Cyrillic; a cp1252 Windows console would raise otherwise."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(
    argv: list[str] | None = None,
    *,
    make_retriever: Callable[[str], TrailerRetriever] = _youtube_api_retriever,
) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Trailer-selection evaluation harness."
    )
    parser.add_argument(
        "--golden", default=str(_DEFAULT_GOLDEN), help="golden-set JSON path"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="dev-only: rebuild candidate pools from YouTube",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="overwrite trailer_baseline.json with the current scorecard",
    )
    args = parser.parse_args(argv)

    if args.record:
        return _record(args.golden, make_retriever)

    rows, total = evaluate(load_golden_set(args.golden))
    print("── find_trailer (frozen pools) ──")
    _print_scorecard(rows, total)
    if args.update_baseline:
        save_baseline(BASELINE_PATH, build_baseline(rows))
        print(f"baseline updated → {BASELINE_PATH}")
        return 0
    print(compare_to_baseline(load_baseline(BASELINE_PATH), rows).text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
