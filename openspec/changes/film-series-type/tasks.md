## 0. Delivery start

- [x] 0.1 Run `agent-process start_change film-series-type --planner Claude --implementer Claude` (tracking issue 16), then `EnterWorktree` into `.claude/worktrees/film-series-type`; verify: the script exits 0 and the issue is In Progress.

## 1. RED

- [x] 1.1 Add the new tests of the map below; verify: every map node id exists.
- [x] 1.2 Run `agent-process check_red` with every new map node id except the `live` ones; verify: it exits 0 (all fail), then commit RED with the Group 1 ticks.

## 2. Selection

- [x] 2.1 `FilmProfile.series: bool | None = None`; `__post_init__` sets `series=True` for a season and raises `ValueError` for a season with `series=False` (design 1, 2); verify: `python -m pytest tests/test_strategy.py -k contradicts_film`.
- [x] 2.2 `title_is_series` in `text.py` (design 3) and the film rejection in `_relevant`, with the own-title marker flag computed once in `pick` (design 4); verify: `python -m pytest tests/test_strategy.py -k "film or unmarked"`.
- [x] 2.3 `series_hit` rank key after `is_ru` for a series or a season profile (design 5); verify: `python -m pytest tests/test_strategy.py`; commit.

## 3. Retrieval

- [x] 3.1 Type word in `_queries`: `сериал`/`series` for a series without a season, `фильм`/`movie` for a film (design 6), with a `test_typed_queries` row for a profile without a year (no `None` in the query); verify: `python -m pytest tests/test_retrieval.py`; commit.

## 4. Docs and live check

- [x] 4.1 `README.md`: one line on `series` next to the `season` line; verify: `python -X utf8 scripts/eval_trailers.py` prints `baseline: match`.
- [x] 4.2 Run `python -m pytest -m live tests/test_live_ytdlp.py`; verify: all live tests pass, the Огонь and Хартленд picks and reasons are recorded in the PR report; commit.

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits.
- [ ] 5.2 Run `openspec validate --strict --all`; verify: exit 0.
- [ ] 5.3 Run the declared test `pre-commit run --hook-stage manual --all-files --show-diff-on-failure`; verify: exit 0.

## 6. Deliver

- [ ] 6.1 Run `agent-process archive_change film-series-type`, then `gh pr create --title "feat: film-series-type" --body-file <report>` (report: `Refs #16`, scenario map, live-check result, deferrals: passing the card type from lampa-mediacenter; year from description/upload date and the «Монстры» example), then `gh pr merge <PR> --auto --squash`.
- [ ] 6.2 Run `agent-process wait_for_pr <PR>` after creation and after every corrective push; apply findings for at most three rounds.
- [ ] 6.3 With the person's consent, open an issue in `ekolvah/lampa-mediacenter`: the service passes the card type as `series` once the release with this change is out; verify: the issue URL is in the final message.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| trailer-selection | Film rejects series markers | `tests/test_strategy.py::test_film_rejects_series_markers` (parametrized, 4 titles) |
| trailer-selection | Film rejects a season trailer | `tests/test_strategy.py::test_film_rejects_season_trailer` |
| trailer-selection | Film's own marker word is not a series marker | `tests/test_strategy.py::test_film_own_marker_word_kept` (parametrized: original, Russian) |
| trailer-selection | Series keeps an unmarked trailer | `tests/test_strategy.py::test_series_keeps_unmarked` |
| trailer-selection | Season contradicts a film | `tests/test_strategy.py::test_season_contradicts_film` |
| trailer-selection | Unknown type is unchanged | `tests/test_eval_baseline.py::test_committed_baseline_matches` (existing regression guard, passes before and after) |
| trailer-selection | Live series trailer for Огонь | `tests/test_live_ytdlp.py::test_ogon_series` (marker `live`, task 4.2, not in CI) |
| trailer-selection | Live film trailer for Хартленд | `tests/test_live_ytdlp.py::test_heartland_film` (marker `live`, task 4.2, not in CI) |
| trailer-selection | Russian trailer beats English | `tests/test_strategy.py::test_ru_beats_en` (unchanged) |
| trailer-selection | Trailer beats teaser within one language | `tests/test_strategy.py::test_trailer_beats_teaser` (unchanged) |
| trailer-selection | Tied top rank is marked ambiguous | `tests/test_strategy.py::test_tie_is_ambiguous` (unchanged) |
| trailer-selection | Requested season beats an earlier season | `tests/test_strategy.py::test_requested_season_beats_earlier` (unchanged) |
| trailer-selection | Season markers recognised | `tests/test_strategy.py::test_season_markers_recognised` (unchanged) |
| trailer-selection | Season 1 accepts an unmarked trailer | `tests/test_strategy.py::test_season_1_accepts_unmarked` (unchanged) |
| trailer-selection | Series prefers a series-marked trailer | `tests/test_strategy.py::test_series_prefers_marked` |
| trailer-selection | Series marker outranks cast | `tests/test_strategy.py::test_series_marker_outranks_cast` |
| trailer-selection | Russian title outranks a series marker | `tests/test_strategy.py::test_ru_outranks_series_marker` |
| trailer-selection | Season profile counts as a series | `tests/test_strategy.py::test_season_profile_counts_as_series` |
| trailer-selection | Missing season falls back visibly | `tests/test_strategy.py::test_missing_season_falls_back_visibly` (unchanged) |
| trailer-selection | Invalid season rejected | `tests/test_strategy.py::test_invalid_season_rejected` (unchanged) |
| trailer-selection | Films without a season are unchanged | `tests/test_eval_baseline.py::test_committed_baseline_matches` (unchanged) |
| trailer-selection | Live season trailer for The Gentlemen | `tests/test_live_ytdlp.py::test_gentlemen_season_2` (unchanged, marker `live`, task 4.2) |
| trailer-retrieval | Durations logged | `tests/test_retrieval.py::test_query_durations_logged` (unchanged) |
| trailer-retrieval | Two titles, deduplicated pool | `tests/test_retrieval.py::test_union_order_and_dedup` (unchanged) |
| trailer-retrieval | Equal titles query once | `tests/test_retrieval.py::test_equal_titles_query_once` (unchanged) |
| trailer-retrieval | Season queries | `tests/test_retrieval.py::test_season_queries` (unchanged) |
| trailer-retrieval | Season query without an original title | `tests/test_retrieval.py::test_season_queries` (unchanged, parametrized) |
| trailer-retrieval | Series queries | `tests/test_retrieval.py::test_typed_queries` (parametrized) |
| trailer-retrieval | Film queries | `tests/test_retrieval.py::test_typed_queries` (parametrized) |
