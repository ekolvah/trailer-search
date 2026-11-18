## MODIFIED Requirements

### Requirement: Candidate relevance
A candidate SHALL be relevant only when its title contains the tokens of the Russian title, the original title,
or the original title without its parenthesised suffix, consecutively and in order, allowing one interspersed
standalone sequel number that is not a year, and, when its title names a year, one of the named years is the
film's year or the year after it.

#### Scenario: No relevant candidate
- **WHEN** no candidate title contains either film title
- **THEN** the pick has `video_id` None, `title` None, `confidence` 0.0 and reason `no title+year match`

#### Scenario: Other year excludes a candidate
- **WHEN** a candidate title contains the film title but none of its named years is the film's year or the year after it
- **THEN** that candidate is not picked

#### Scenario: Film year among several years admits a candidate
- **WHEN** the film year is 2021 and a candidate title is `Dune 2021 vs 1984`
- **THEN** the candidate's year check passes

#### Scenario: Release year admits a candidate
- **WHEN** the film year is 2025, the Russian title is `Коммерсант` and a candidate title is `Коммерсант - Трейлер 2026`
- **THEN** the candidate is picked

#### Scenario: Edition suffix of the original title is ignored
- **WHEN** the original title is `Marvel's Spider-Man 2 (Digital Deluxe Edition)` and a candidate title is `Marvel's Spider-Man 2 Official Trailer`
- **THEN** the candidate is relevant

#### Scenario: Interspersed sequel number
- **WHEN** the Russian title is `Шрэк навсегда` and a candidate title is `Шрэк 4 навсегда трейлер`
- **THEN** the candidate is relevant

#### Scenario: A year is not skipped as a sequel number
- **WHEN** the Russian title is `Шрэк навсегда` and a candidate title is `Шрэк 2010 навсегда трейлер`
- **THEN** the candidate is not relevant
