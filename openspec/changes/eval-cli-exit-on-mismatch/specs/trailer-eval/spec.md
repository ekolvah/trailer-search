## MODIFIED Requirements

### Requirement: Baseline gate
The test suite SHALL run `find_trailer` over every case's frozen candidate pool and fail, naming each changed
case, when any per-case outcome differs from `tests/fixtures/trailer_baseline.json`. The committed baseline SHALL
hold 29 hit, 2 miss and 1 wrong out of 32. `scripts/eval_trailers.py` without `--record` or `--update-baseline`
SHALL exit non-zero when the baseline comparison reports a mismatch, and zero when it matches.

#### Scenario: Committed baseline matches
- **WHEN** the test suite runs on the committed golden set and baseline
- **THEN** the gate passes and the baseline tallies 29 hit, 2 miss and 1 wrong

#### Scenario: Regressed selection is named
- **WHEN** the retriever used by the gate returns an empty pool for every case
- **THEN** the gate fails and names the cases whose outcome changed

#### Scenario: CLI exit status follows the baseline
- **WHEN** `scripts/eval_trailers.py` runs against a baseline whose outcome for one case differs from the current scorecard
- **THEN** it prints the mismatch and exits non-zero, and against a matching baseline it exits zero
