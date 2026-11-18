# trailer-selection Specification

## Purpose
Один выбор русского трейлера фильма из пула кандидатов YouTube для всех потребителей (kinozal_scraper,
lampa-mediacenter): публичный контракт пакета, правила релевантности и ранжирования, точка входа `find_trailer`.

## Requirements

### Requirement: Public contract
The package SHALL expose `FilmProfile`, `Candidate`, `TrailerPick`, `TrailerRetrievalError` and `find_trailer`
at its top level and `YtDlpRetriever` in its `ytdlp` module. `TrailerPick` SHALL carry `video_id`, `title`,
`confidence` and `reason`. The base installation SHALL import without yt-dlp or the Google API client installed.

#### Scenario: Consumer imports the documented names
- **WHEN** a consumer runs `from trailer_search import FilmProfile, TrailerPick, TrailerRetrievalError, find_trailer` and `from trailer_search.ytdlp import YtDlpRetriever` with the `ytdlp` extra installed
- **THEN** both imports succeed and `TrailerPick` has the fields `video_id`, `title`, `confidence`, `reason`

#### Scenario: Base install has no third-party dependency
- **WHEN** the package is installed without extras and `trailer_search` is imported
- **THEN** the import succeeds and neither `yt_dlp` nor `googleapiclient` is loaded

### Requirement: Candidate relevance
A candidate SHALL be relevant only when its title contains the tokens of the Russian title, the original title,
or the original title without its parenthesised suffix, consecutively and in order, allowing one interspersed
standalone sequel number that is not a year, and, when its title names a year, one of the named years is the
film's year or the year after it.
When the profile gives a season, the year condition SHALL instead be that the title names no year earlier than the
film's year.

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

#### Scenario: Season candidate passes despite a later year
- **WHEN** the profile is `Джентльмены` / `The Gentlemen` / 2024 with season 2 and the only candidate is `Джентльмены (2 сезон) - Русский трейлер (Дубляж, 2026) Гай Ричи`
- **THEN** that candidate is picked

#### Scenario: Season keeps rejecting an earlier year
- **WHEN** the profile is `Джентльмены` / `The Gentlemen` / 2024 with season 2 and the only candidate is `The Gentlemen 2019 Official Trailer`
- **THEN** the pick has `video_id` None

### Requirement: Candidate ranking
Relevant candidates SHALL be ranked by Cyrillic title first, then by how many of the first two cast names occur in
the description, then by trailer words (`трейлер`, `trailer`, `дубляж`) minus teaser words (`тизер`, `teaser`).
When the profile gives a season N, candidates whose title counts as season N SHALL rank above all others before
those keys apply. A title counts as season N when it names season N as `N сезон`, `N-й сезон`, `сезон N`,
`season N` or `sNN`, case-insensitively, or, for N = 1, when it names no season.
A unique top rank SHALL give confidence 0.9; a shared top rank SHALL give the first such candidate in pool order
with confidence 0.3 and a reason starting with `ambiguous`.

#### Scenario: Russian trailer beats English
- **WHEN** a relevant English-titled and a relevant Cyrillic-titled candidate are in the pool
- **THEN** the Cyrillic-titled candidate is picked with confidence 0.9

#### Scenario: Trailer beats teaser within one language
- **WHEN** two relevant Cyrillic-titled candidates differ only in that one says `трейлер` and the other `тизер`
- **THEN** the `трейлер` candidate is picked

#### Scenario: Tied top rank is marked ambiguous
- **WHEN** two relevant candidates share the top rank
- **THEN** the first of them in pool order is picked with confidence 0.3 and a reason starting with `ambiguous`

#### Scenario: Requested season beats an earlier season
- **WHEN** the profile has season 2 and the pool is `Джентльмены (1 сезон) — Русский трейлер (4К, 2024)` then `The Gentlemen: Season 2 | Official Trailer | Netflix`
- **THEN** the season 2 candidate is picked with confidence 0.9

#### Scenario: Season markers recognised
- **WHEN** the profile has season 2 and a candidate title names it as `2 СЕЗОН`, `2-й сезон`, `Сезон 2`, `Season 2` or `S02`, competing with `Джентльмены (1 сезон) — Русский трейлер`
- **THEN** the candidate naming season 2 is picked

#### Scenario: Season 1 accepts an unmarked trailer
- **WHEN** the profile has season 1 and the pool is `Джентльмены (2 сезон) — Русский трейлер` then `Джентльмены — Русский трейлер`
- **THEN** the unmarked candidate is picked and the reason does not mention a fallback

### Requirement: Find trailer
`find_trailer` SHALL obtain the candidate pool for a film from the given retriever, select one candidate by the
ranking above, and return a pick whose `title` is the selected candidate's title, or None when nothing is picked.
A retrieval failure SHALL reach the caller as `TrailerRetrievalError`, never as an empty pick.

#### Scenario: Pick carries the candidate title
- **WHEN** the retriever returns a pool whose relevant Cyrillic-titled candidate is `J2VS_OlUJtA` titled `Зверь (2026)#трейлер в русской озвучке#The Beast`
- **THEN** the pick has `video_id` `J2VS_OlUJtA` and that `title`

#### Scenario: Retrieval failure propagates
- **WHEN** the retriever raises `TrailerRetrievalError`
- **THEN** `find_trailer` raises `TrailerRetrievalError`

### Requirement: Series season
`FilmProfile` SHALL accept an optional `season`, defaulting to None, and SHALL raise `ValueError` at construction
for a season below 1. When a season N is given and the picked candidate's title does not count as season N, the pick's
reason SHALL end with `; season N fallback`, and a WARNING SHALL name
the film and the season. Without a season, selection SHALL be unchanged.

#### Scenario: Missing season falls back visibly
- **WHEN** the profile has season 3 and the only relevant candidate is `Джентльмены (2 сезон) — Русский трейлер`
- **THEN** that candidate is picked, its reason ends with `; season 3 fallback` and a WARNING names `Джентльмены` and season 3

#### Scenario: Invalid season rejected
- **WHEN** a `FilmProfile` is built with season 0 or -1
- **THEN** `ValueError` is raised

#### Scenario: Films without a season are unchanged
- **WHEN** the committed golden set, none of whose profiles gives a season, is evaluated against its frozen pools
- **THEN** every selection matches the committed baseline

#### Scenario: Live season trailer for The Gentlemen
- **WHEN** `find_trailer` runs with the yt-dlp retriever against live YouTube for `Джентльмены` / `The Gentlemen` / 2024 with season 2
- **THEN** the pick's title names season 2 and contains Cyrillic, and the reason does not mention a fallback
