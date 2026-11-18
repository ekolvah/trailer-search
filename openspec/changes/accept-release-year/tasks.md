## 0. Delivery start

- [x] 0.1 Run `agent-process start_change accept-release-year --planner Claude --implementer Claude` (tracking issue 10); verify it exits 0 and prints the worktree path, then enter it with `EnterWorktree`.

## 1. RED

- [x] 1.1 Add `tests/test_strategy.py::test_release_year_admitted` and the guards `tests/test_text.py::test_title_with_year_before_does_not_match` and `tests/test_text.py::test_title_with_film_year_and_other_year_matches` (both pass before the fix); verify `agent-process check_red tests/test_strategy.py::test_release_year_admitted` reports it failing, then commit RED.

## 2. Release year

- [x] 2.1 Accept `film_year + 1` in `title_year_matches` (`src/trailer_search/text.py`) and update its docstring; verify `python -m pytest tests/test_text.py tests/test_strategy.py` passes.
- [x] 2.2 Add the Коммерсант golden entry (five observed candidates with their real YouTube ids) to `tests/fixtures/trailer_golden.json`, run `python -X utf8 scripts/eval_trailers.py --update-baseline`; verify `git diff tests/fixtures/trailer_baseline.json` adds one `hit` and changes no other outcome.

## 3. Verify

- [ ] 3.1 Run `/simplify` and commit its edits.
- [ ] 3.2 Run `openspec validate --strict --all`; verify exit 0.
- [ ] 3.3 Run `pre-commit run --hook-stage manual --all-files --show-diff-on-failure`; verify exit 0.

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change accept-release-year`, open the PR titled `fix: accept-release-year` with the report body, run `gh pr merge <PR> --auto --squash` and `agent-process wait_for_pr <PR>`; verify the head settles with no open P0/P1 thread.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| trailer-selection | No relevant candidate | `tests/test_strategy.py::test_no_relevant_candidate` |
| trailer-selection | Other year excludes a candidate | `tests/test_strategy.py::test_other_year_excluded`, `tests/test_text.py::test_title_with_other_year_does_not_match`, `tests/test_text.py::test_title_with_year_before_does_not_match` |
| trailer-selection | Film year among several years admits a candidate | `tests/test_text.py::test_title_with_film_year_and_other_year_matches` |
| trailer-selection | Release year admits a candidate | `tests/test_strategy.py::test_release_year_admitted` |
| trailer-selection | Edition suffix of the original title is ignored | `tests/test_strategy.py::test_edition_suffix_ignored` |
| trailer-selection | Interspersed sequel number | `tests/test_strategy.py::test_sequel_number_skipped` |
| trailer-selection | A year is not skipped as a sequel number | `tests/test_strategy.py::test_year_not_skipped` |
