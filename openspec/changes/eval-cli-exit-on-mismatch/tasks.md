## 0. Delivery start

- [x] 0.1 Spec correction on the PR #4 branch of `extract-trailer-search-library` (tracking issue 1).

## 1. Fix

- [x] 1.1 Return non-zero from `scripts/eval_trailers.py` on a baseline mismatch; verify: `python -m pytest tests/test_eval_baseline.py -k cli_exit`.

## Scenario → test map

| Spec | Scenario | Test |
|---|---|---|
| trailer-eval | Committed baseline matches | `tests/test_eval_baseline.py::test_committed_baseline_matches` |
| trailer-eval | Regressed selection is named | `tests/test_eval_baseline.py::test_regressed_selection_is_named` |
| trailer-eval | CLI exit status follows the baseline | `tests/test_eval_baseline.py::test_cli_exit_status_follows_baseline` (parametrized) |
