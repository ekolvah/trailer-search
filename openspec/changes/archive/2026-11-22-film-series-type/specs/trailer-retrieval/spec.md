## MODIFIED Requirements

### Requirement: Query union
A retriever SHALL query `<title> <year> trailer` (or `<title> trailer` without a year) for the Russian title and,
when it is non-empty and differs, for the original title. When the profile gives a season N, the same queries
SHALL instead read `<Russian title> N сезон trailer` and `<original title> season N trailer`, without a year.
When the profile gives no season and a known type, each query SHALL carry, after the year, `сериал` (Russian) or
`series` (original) for a series, and `фильм` or `movie` for a film.
The pool SHALL list the Russian query's results first, then the original query's, without repeating a video id.
It SHALL log each query with its duration, and the total search duration, at INFO.

#### Scenario: Durations logged
- **WHEN** a search of two queries completes
- **THEN** an INFO record names each query with its duration and another gives the total duration

#### Scenario: Two titles, deduplicated pool
- **WHEN** the Russian and original queries both return video `A` and the original query also returns `B`
- **THEN** the pool is `A`, `B` in that order

#### Scenario: Equal titles query once
- **WHEN** the Russian title equals the original title
- **THEN** exactly one query is issued

#### Scenario: Season queries
- **WHEN** the profile is `Джентльмены` / `The Gentlemen` / 2024 with season 2
- **THEN** the queries are `Джентльмены 2 сезон trailer` and `The Gentlemen season 2 trailer`

#### Scenario: Season query without an original title
- **WHEN** the profile is `Джентльмены` / empty original title / 2024 with season 2
- **THEN** exactly one query is issued, `Джентльмены 2 сезон trailer`

#### Scenario: Series queries
- **WHEN** the profile is the series `Монстры` / `Monster` / 2022 without a season
- **THEN** the queries are `Монстры 2022 сериал trailer` and `Monster 2022 series trailer`

#### Scenario: Film queries
- **WHEN** the profile is the film `Хартленд` / `Heartland` / 2026
- **THEN** the queries are `Хартленд 2026 фильм trailer` and `Heartland 2026 movie trailer`

