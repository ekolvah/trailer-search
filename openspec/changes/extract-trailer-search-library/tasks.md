## 0. Delivery start

- [x] 0.1 Run `agent-process start_change extract-trailer-search-library --planner Claude --implementer Claude` (tracking issue 1), then `EnterWorktree` into `.claude/worktrees/extract-trailer-search-library`; verify: the script exits 0 and the issue is In Progress.

## 1. RED

- [x] 1.1 Add `pyproject.toml` (PEP 621, setuptools, version 0.1.0, `requires-python = ">=3.12"`, extras `ytdlp` and `youtube-api`; pytest `pythonpath = ["src"]`, marker `live`, `addopts = "-m 'not live'"`; mypy `mypy_path = "src"` and `ignore_missing_imports` for `yt_dlp.*`, `googleapiclient.*`) `requirements.txt` pinning `yt-dlp==2026.10.26` and `google-api-python-client==2.195.0`, `requirements-dev.txt` (pytest), empty `scripts/__init__.py`, and `additional_dependencies: [pytest]` on the mypy hook in `.pre-commit-config.yaml` (design 11); verify: `pip install -r requirements.txt -r requirements-dev.txt` succeeds and `python -m pytest --collect-only` reads the config.
- [x] 1.2 Copy `tests/fixtures/trailer_golden.json` and `tests/fixtures/trailer_baseline.json` byte-for-byte from kinozal_scraper `40cd99d`; verify: `git diff --no-index` against the kinozal files is empty.
- [x] 1.3 Port `test_text_utils.py` → `tests/test_text.py`, `test_trailer_strategy.py` → `tests/test_strategy.py` (without `FirstResultStrategy` tests), `test_youtube.py` → `tests/test_youtube_api.py` and `tests/test_retrieval.py`, `test_eval_trailers.py` → `tests/test_eval_trailers.py` (without TMDB-evaluation and delivery tests), `test_eval_baseline.py` → `tests/test_eval_baseline.py` (over `find_trailer`), with imports from `trailer_search`; add the scenario tests of the map below that kinozal lacks, `tests/test_find_trailer.py`, `tests/test_ytdlp.py` and `tests/test_live_ytdlp.py`; the `threading.Event` fakes are released in a fixture finalizer and wait at most 5 s (design 12); verify: every map node id exists.
- [x] 1.4 Run `agent-process check_red` with every map node id except the `live` one; verify: it exits 0 (all fail), then commit RED with the Group 1 ticks.

## 2. Text and selection

- [x] 2.1 Port `has_cyrillic`, `normalize_title`, `title_year_matches` into `src/trailer_search/text.py`; verify: `python -m pytest tests/test_text.py`.
- [x] 2.2 Port the types, `TrailerStrategy` and `HeuristicStrategy` into `src/trailer_search/strategy.py`, adding `TrailerPick.title` filled from the picked candidate (design 2); verify: `python -m pytest tests/test_strategy.py`; commit.

## 3. Retrieval and entry point

- [x] 3.1 `src/trailer_search/retrieval.py`: `TrailerRetrievalError`, `TrailerRetriever` protocol, `MAX_RESULTS`/`MAX_DURATION_S`, `search_union` keeping pool order by query index, raising the first branch's `TrailerRetrievalError` subclass chained `from` that branch's exception (`test_all_branches_fail_raises` asserts `__cause__`), no pool for one query or `max_workers=1` without a deadline, `deadline_s` with dropped late branches and INFO durations (design 4, 5, 6, 12); verify: `python -m pytest tests/test_retrieval.py`.
- [x] 3.2 `src/trailer_search/youtube_api.py`: `YoutubeApiRetriever(api_key, *, client_factory)` whose branch raises `YoutubeQuotaExhausted` on a quota error (design 4, 5, 7); verify: `python -m pytest tests/test_youtube_api.py`.
- [x] 3.3 `src/trailer_search/ytdlp.py`: `YtDlpRetriever(socket_timeout=4, *, deadline_s=10.0, ydl_factory)` exposing `deadline_s` and rejecting non-positive values, `ytsearch10:` with `ie_key="YoutubeSearch"`, retries 0, first `MAX_RESULTS` entries under `MAX_DURATION_S`, 2 workers, `deadline_s` passed to `search_union` (design 5, 6, 12); `test_flat_search_bounded_options` compares the option keys with `yt_dlp.parse_options(...)` of the installed yt-dlp; verify: `python -m pytest tests/test_ytdlp.py`.
- [x] 3.4 `src/trailer_search/__init__.py` re-exports the contract and defines `find_trailer` (design 3); add `src/trailer_search/py.typed`; verify: `python -m pytest tests/test_find_trailer.py`; commit.

## 4. Evaluation

- [x] 4.1 Port `scripts/eval_trailers.py`: loader (`tmdb_videos` only as accepted-id source, design 8), `classify`, `score`, scorecard over `find_trailer` with a frozen retriever, baseline compare and `--update-baseline`, `--record` through `YoutubeApiRetriever` (design 7); drop TMDB and delivery runs and `--threshold`; verify: `python -m pytest tests/test_eval_trailers.py tests/test_eval_baseline.py` passes and `python -X utf8 scripts/eval_trailers.py` prints `hit=29 miss=2 wrong=1 (n=32)` and `baseline: match`; commit.

## 5. Package and live check

- [x] 5.1 Add `README.md` (install by git URL with extras, the issue #1 usage snippet, eval command) and `.gitignore` (`__pycache__/`, `*.egg-info/`, `build/`, `dist/`, `.venv/`); verify: in a fresh venv `pip install .` then `python -c "import trailer_search, sys; assert 'yt_dlp' not in sys.modules"`, and `pip install ".[ytdlp]"` then `python -c "from trailer_search.ytdlp import YtDlpRetriever"`.
- [x] 5.2 Run `python -m pytest -m live tests/test_live_ytdlp.py` in that venv; verify: it passes, asserts and prints the elapsed time under the deadline and no dropped-query WARNING, and the pick and time are recorded in the PR report; commit.

## 6. Verify

- [ ] 6.1 Run `/simplify` without an argument and commit its edits.
- [ ] 6.2 Run `openspec validate --strict --all`; verify: exit 0.
- [ ] 6.3 Run the declared test `pre-commit run --hook-stage manual --all-files --show-diff-on-failure`; verify: exit 0.

## 7. Deliver

- [ ] 7.1 Run `agent-process archive_change extract-trailer-search-library`, then `gh pr create --title "feat: extract-trailer-search-library" --body-file <report>` (report: `Refs #1`, scenario map, live-check result, deferrals: armv7 timing → lampa-mediacenter#48, kinozal TMDB/delivery gates → kinozal_scraper#647), then `gh pr merge <PR> --auto --squash`.
- [ ] 7.2 Run `agent-process wait_for_pr <PR>` after creation and after every corrective push; apply findings for at most three rounds.
- [ ] 7.3 After the person's approval merges the PR, with their consent create and push tag `v0.1.0` on the merge commit; verify: in a fresh venv `pip install "trailer-search[ytdlp] @ git+https://github.com/ekolvah/trailer-search@v0.1.0"` and the issue #1 snippet import succeeds.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| trailer-selection | Consumer imports the documented names | `tests/test_find_trailer.py::test_public_contract_imports` |
| trailer-selection | Base install has no third-party dependency | `tests/test_find_trailer.py::test_base_import_loads_no_extras` |
| trailer-selection | No relevant candidate | `tests/test_strategy.py::test_no_relevant_candidate` |
| trailer-selection | Other year excludes a candidate | `tests/test_strategy.py::test_other_year_excluded` |
| trailer-selection | Edition suffix of the original title is ignored | `tests/test_strategy.py::test_edition_suffix_ignored` |
| trailer-selection | Interspersed sequel number | `tests/test_strategy.py::test_sequel_number_skipped` |
| trailer-selection | A year is not skipped as a sequel number | `tests/test_strategy.py::test_year_not_skipped` |
| trailer-selection | Russian trailer beats English | `tests/test_strategy.py::test_ru_beats_en` |
| trailer-selection | Trailer beats teaser within one language | `tests/test_strategy.py::test_trailer_beats_teaser` |
| trailer-selection | Tied top rank is marked ambiguous | `tests/test_strategy.py::test_tie_is_ambiguous` |
| trailer-selection | Pick carries the candidate title | `tests/test_find_trailer.py::test_pick_carries_candidate_title` |
| trailer-selection | Retrieval failure propagates | `tests/test_find_trailer.py::test_retrieval_error_propagates` |
| trailer-retrieval | Durations logged | `tests/test_retrieval.py::test_query_durations_logged` |
| trailer-retrieval | Two titles, deduplicated pool | `tests/test_retrieval.py::test_union_order_and_dedup` |
| trailer-retrieval | Equal titles query once | `tests/test_retrieval.py::test_equal_titles_query_once` |
| trailer-retrieval | One branch fails | `tests/test_retrieval.py::test_one_branch_failure_warns` |
| trailer-retrieval | All branches fail | `tests/test_retrieval.py::test_all_branches_fail_raises` |
| trailer-retrieval | Empty results are not a failure | `tests/test_retrieval.py::test_empty_results_not_failure` |
| trailer-retrieval | Late query dropped | `tests/test_retrieval.py::test_late_query_dropped_at_deadline` |
| trailer-retrieval | Blocked yt-dlp search hits the deadline | `tests/test_ytdlp.py::test_blocked_search_hits_deadline` |
| trailer-retrieval | Default deadline | `tests/test_ytdlp.py::test_default_deadline_10s` |
| trailer-retrieval | Invalid deadline or timeout rejected | `tests/test_ytdlp.py::test_invalid_timing_rejected` (parametrized) |
| trailer-retrieval | HTML entities decoded | `tests/test_youtube_api.py::test_html_entities_decoded` |
| trailer-retrieval | Quota in any failed branch | `tests/test_youtube_api.py::test_quota_in_any_failed_branch` |
| trailer-retrieval | Long and unknown-duration entries dropped | `tests/test_ytdlp.py::test_drops_long_and_unknown_duration` |
| trailer-retrieval | Flat search with bounded network options | `tests/test_ytdlp.py::test_flat_search_bounded_options` |
| trailer-retrieval | Queries run concurrently | `tests/test_ytdlp.py::test_queries_run_concurrently` |
| trailer-retrieval | Live Russian trailer for The Beast | `tests/test_live_ytdlp.py::test_beast_russian_trailer` (marker `live`, task 5.2, not in CI) |
| trailer-eval | Accepted id outside both pools | `tests/test_eval_trailers.py::test_accept_id_outside_both_pools_errors` |
| trailer-eval | Duplicate candidate id | `tests/test_eval_trailers.py::test_duplicate_candidate_id_errors` |
| trailer-eval | Empty reference and a pick | `tests/test_eval_trailers.py::test_null_correct_with_pick_is_wrong` |
| trailer-eval | Weighted score | `tests/test_eval_trailers.py::test_weighted_score` |
| trailer-eval | Committed baseline matches | `tests/test_eval_baseline.py::test_committed_baseline_matches` |
| trailer-eval | Regressed selection is named | `tests/test_eval_baseline.py::test_regressed_selection_is_named` |
| trailer-eval | Missing API key | `tests/test_eval_trailers.py::test_record_missing_api_key_fails_fast` |
| trailer-eval | Pinned id gone from the refreshed pool | `tests/test_eval_trailers.py::test_record_fails_before_write_when_pinned_id_gone` |
