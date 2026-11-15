## Why

Review of PR #4 (https://github.com/ekolvah/trailer-search/pull/4#discussion_r4579235753):
`scripts/eval_trailers.py` printed `baseline: MISMATCH` and still exited 0, so a CLI run reported success on a
drifted selection (§IV). Reproduced by `tests/test_eval_baseline.py::test_cli_exit_status_follows_baseline[mismatch]`
failing before the fix.

## What Changes

- `main` returns 1 when `compare_to_baseline(...).ok` is false.

## Impact

- Edited: `scripts/eval_trailers.py`, `tests/test_eval_baseline.py`, `openspec/specs/trailer-eval/spec.md` (via archive).

## Standard approach

A CLI check reports failure through its exit status (POSIX convention); none found beyond that.
