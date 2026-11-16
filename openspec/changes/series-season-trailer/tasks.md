## 0. Delivery start

- [x] 0.1 Run `agent-process start_change series-season-trailer --planner Claude --implementer Claude` (tracking issue 5), then `EnterWorktree` into `.claude/worktrees/series-season-trailer`; verify: the script exits 0 and the issue is In Progress.

## 1. RED

- [x] 1.1 Add the new tests of the map below; verify: every map node id exists.
- [x] 1.2 Run `agent-process check_red` with every new map node id except the `live` one; verify: it exits 0 (all fail), then commit RED with the Group 1 ticks.

## 2. Selection

- [x] 2.1 `FilmProfile.season: int | None = None` with `__post_init__` raising `ValueError` below 1 (design 7); verify: `python -m pytest tests/test_strategy.py -k invalid_season`.
- [x] 2.2 `title_season` in `text.py` (design 3) and `season_hit` as the first `_rank` key (design 4); verify: `python -m pytest tests/test_strategy.py -k "season_beats or markers or season_1"`.
- [x] 2.3 `title_year_matches(..., at_least=)` and its use in `_relevant` when a season is given (design 2); verify: `python -m pytest tests/test_strategy.py -k year`.
- [x] 2.4 Fallback suffix `; season N fallback` and `logger.warning` naming the film and season (design 5); verify: `python -m pytest tests/test_strategy.py`; commit.

## 3. Retrieval

- [ ] 3.1 Season branch in `_queries`: `<ru> N сезон trailer` / `<orig> season N trailer` (design 6); verify: `python -m pytest tests/test_retrieval.py`; commit.

## 4. Release and live check

- [ ] 4.1 `pyproject.toml` version 0.2.0; `README.md` install tag `v0.2.0` and one line on `season` (design 8); verify: `python -X utf8 scripts/eval_trailers.py` prints `baseline: match`.
- [ ] 4.2 Run `python -m pytest -m live tests/test_live_ytdlp.py`; verify: both live tests pass, the Gentlemen pick and reason are recorded in the PR report; commit.

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits.
- [ ] 5.2 Run `openspec validate --strict --all`; verify: exit 0.
- [ ] 5.3 Run the declared test `pre-commit run --hook-stage manual --all-files --show-diff-on-failure`; verify: exit 0.

## 6. Deliver

- [ ] 6.1 Run `agent-process archive_change series-season-trailer`, then `gh pr create --title "feat: series-season-trailer" --body-file <report>` (report: `Refs #5`, scenario map, live-check result, deferral: passing `season` from lampa-mediacenter → ekolvah/lampa-mediacenter#64), then `gh pr merge <PR> --auto --squash`.
- [ ] 6.2 Run `agent-process wait_for_pr <PR>` after creation and after every corrective push; apply findings for at most three rounds.
- [ ] 6.3 After the person's approval merges the PR, with their consent create and push tag `v0.2.0` on the merge commit; verify: in a fresh venv `pip install "trailer-search[ytdlp] @ git+https://github.com/ekolvah/trailer-search@v0.2.0"` and `FilmProfile("Джентльмены", "The Gentlemen", 2024, season=2)` builds.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| trailer-selection | No relevant candidate | `tests/test_strategy.py::test_no_relevant_candidate` (unchanged) |
| trailer-selection | Other year excludes a candidate | `tests/test_strategy.py::test_other_year_excluded` (unchanged) |
| trailer-selection | Edition suffix of the original title is ignored | `tests/test_strategy.py::test_edition_suffix_ignored` (unchanged) |
| trailer-selection | Interspersed sequel number | `tests/test_strategy.py::test_sequel_number_skipped` (unchanged) |
| trailer-selection | A year is not skipped as a sequel number | `tests/test_strategy.py::test_year_not_skipped` (unchanged) |
| trailer-selection | Season candidate passes despite a later year | `tests/test_strategy.py::test_season_candidate_passes_later_year` |
| trailer-selection | Season keeps rejecting an earlier year | `tests/test_strategy.py::test_season_rejects_earlier_year` |
| trailer-selection | Russian trailer beats English | `tests/test_strategy.py::test_ru_beats_en` (unchanged) |
| trailer-selection | Trailer beats teaser within one language | `tests/test_strategy.py::test_trailer_beats_teaser` (unchanged) |
| trailer-selection | Tied top rank is marked ambiguous | `tests/test_strategy.py::test_tie_is_ambiguous` (unchanged) |
| trailer-selection | Requested season beats an earlier season | `tests/test_strategy.py::test_requested_season_beats_earlier` |
| trailer-selection | Season markers recognised | `tests/test_strategy.py::test_season_markers_recognised` (parametrized) |
| trailer-selection | Season 1 accepts an unmarked trailer | `tests/test_strategy.py::test_season_1_accepts_unmarked` |
| trailer-selection | Missing season falls back visibly | `tests/test_strategy.py::test_missing_season_falls_back_visibly` |
| trailer-selection | Invalid season rejected | `tests/test_strategy.py::test_invalid_season_rejected` (parametrized) |
| trailer-selection | Films without a season are unchanged | `tests/test_eval_baseline.py::test_committed_baseline_matches` (existing regression guard, passes before and after) |
| trailer-selection | Live season trailer for The Gentlemen | `tests/test_live_ytdlp.py::test_gentlemen_season_2` (marker `live`, task 4.2, not in CI) |
| trailer-retrieval | Durations logged | `tests/test_retrieval.py::test_query_durations_logged` (unchanged) |
| trailer-retrieval | Two titles, deduplicated pool | `tests/test_retrieval.py::test_union_order_and_dedup` (unchanged) |
| trailer-retrieval | Equal titles query once | `tests/test_retrieval.py::test_equal_titles_query_once` (unchanged) |
| trailer-retrieval | Season queries | `tests/test_retrieval.py::test_season_queries` |
| trailer-retrieval | Season query without an original title | `tests/test_retrieval.py::test_season_queries` (parametrized) |
