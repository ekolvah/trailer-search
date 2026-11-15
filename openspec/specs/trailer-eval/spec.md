# trailer-eval Specification

## Purpose
Измерение качества выбора трейлера на замороженном эталонном наборе без сети и квоты, и ворота в CI, которые
не дают изменению выбора пройти незамеченным.

## Requirements

### Requirement: Golden set validation
Loading the golden set SHALL fail with `GoldenSetError` on an empty set, a missing `film`, `correct` or
`candidates` field, a duplicate candidate id, an empty or non-string accept set, an accepted id found neither in
`candidates` nor in `tmdb_videos`, or a `trap` id outside `candidates` or inside the accept set. The evaluation
command SHALL exit non-zero on such an error.

#### Scenario: Accepted id outside both pools
- **WHEN** a case accepts an id present in neither `candidates` nor `tmdb_videos`
- **THEN** loading raises `GoldenSetError`

#### Scenario: Duplicate candidate id
- **WHEN** a case lists the same candidate id twice
- **THEN** loading raises `GoldenSetError`

### Requirement: Outcome scoring
Each case SHALL be classified hit when the pick is in the accept set or when both the reference and the pick are
empty, miss when a reference exists and nothing is picked, and wrong otherwise. The score SHALL be hit +1,
miss 0, wrong −2.

#### Scenario: Empty reference and a pick
- **WHEN** `correct` is null and a video is picked
- **THEN** the outcome is wrong

#### Scenario: Weighted score
- **WHEN** outcomes are 2 hit, 1 miss and 1 wrong
- **THEN** the score is 0

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

### Requirement: Recording candidate pools
`scripts/eval_trailers.py --record` SHALL rebuild every case's candidate pool through the Data API retriever,
fail before any network call when `API_KEY` is unset, and validate the refreshed set before writing it, leaving
the file unchanged on a validation error.

#### Scenario: Missing API key
- **WHEN** `--record` runs without `API_KEY`
- **THEN** it exits non-zero without contacting YouTube

#### Scenario: Pinned id gone from the refreshed pool
- **WHEN** a refreshed pool no longer contains a case's accepted id and that id is not in the case's `tmdb_videos`
- **THEN** recording fails and the golden file is unchanged
