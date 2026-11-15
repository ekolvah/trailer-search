## Purpose

Один выбор русского трейлера фильма из пула кандидатов YouTube для всех потребителей (kinozal_scraper,
lampa-mediacenter): публичный контракт пакета, правила релевантности и ранжирования, точка входа `find_trailer`.

## ADDED Requirements

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
standalone sequel number that is not a year, and when its title names no year other than the film's year.

#### Scenario: No relevant candidate
- **WHEN** no candidate title contains either film title
- **THEN** the pick has `video_id` None, `title` None, `confidence` 0.0 and reason `no title+year match`

#### Scenario: Other year excludes a candidate
- **WHEN** a candidate title contains the film title but names a year other than the film's year
- **THEN** that candidate is not picked

#### Scenario: Edition suffix of the original title is ignored
- **WHEN** the original title is `Marvel's Spider-Man 2 (Digital Deluxe Edition)` and a candidate title is `Marvel's Spider-Man 2 Official Trailer`
- **THEN** the candidate is relevant

#### Scenario: Interspersed sequel number
- **WHEN** the Russian title is `Шрэк навсегда` and a candidate title is `Шрэк 4 навсегда трейлер`
- **THEN** the candidate is relevant

#### Scenario: A year is not skipped as a sequel number
- **WHEN** the Russian title is `Шрэк навсегда` and a candidate title is `Шрэк 2010 навсегда трейлер`
- **THEN** the candidate is not relevant

### Requirement: Candidate ranking
Relevant candidates SHALL be ranked by Cyrillic title first, then by how many of the first two cast names occur in
the description, then by trailer words (`трейлер`, `trailer`, `дубляж`) minus teaser words (`тизер`, `teaser`).
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
