## ADDED Requirements

### Requirement: Film or series
`FilmProfile` SHALL accept an optional `series`, defaulting to None: True for a series, False for a film, None when
the type is unknown. A profile with a season SHALL count as a series, and a profile with a season and `series` False
SHALL raise `ValueError` at construction.
A title has a series marker when, case-insensitively, it names a season in a form listed under `Candidate ranking`,
contains a word beginning with `сериал`, or contains the word `series`.
For a film, a candidate whose title has a series marker SHALL NOT be relevant, unless the film's Russian or original
title has a series marker itself. For a series, a candidate without a marker SHALL stay relevant.
When the type is unknown, selection SHALL be unchanged.

#### Scenario: Film rejects series markers
- **WHEN** the profile is the film `Огонь` / `Fire` / 2025 and the only candidate is one of `Огонь 2 сезон трейлер`, `Огонь (2026) — сериал НТВ`, `Огонь — трейлер сериала`, `Fire | Russian Trailer | All About the Series`
- **THEN** the pick has `video_id` None

#### Scenario: Film rejects a season trailer
- **WHEN** the profile is the film `Хартленд` / `Heartland` / 2026 and the pool is `Хартленд, 20-й сезон | Официальный трейлер` then `Хартленд (2026) | Официальный трейлер | Нетфликс`
- **THEN** the second candidate is picked with confidence 0.9

#### Scenario: Film's own marker word is not a series marker
- **WHEN** the profile is the film `Лемони Сникет: 33 несчастья` / `A Series of Unfortunate Events` / 2004 with the only candidate `A Series of Unfortunate Events Official Trailer`, or the film `Сериальная мамочка` / empty original title / 1994 with the only candidate `Сериальная мамочка — трейлер`
- **THEN** that candidate is picked

#### Scenario: Series keeps an unmarked trailer
- **WHEN** the profile is the series `Мосгаз. Дело №12: Южный порт` / empty original title / 2025 and the only candidate is `Мосгаз. Дело №12: Южный порт | Официальный трейлер`
- **THEN** that candidate is picked with confidence 0.9

#### Scenario: Season contradicts a film
- **WHEN** a `FilmProfile` is built with season 2 and `series` False
- **THEN** `ValueError` is raised

#### Scenario: Unknown type is unchanged
- **WHEN** the committed golden set, none of whose profiles gives a type, is evaluated against its frozen pools
- **THEN** every selection matches the committed baseline

#### Scenario: Live series trailer for Огонь
- **WHEN** `find_trailer` runs with the yt-dlp retriever against live YouTube for the series `Огонь` / `Огонь` / 2025
- **THEN** the pick's title contains `Огонь` and has a series marker

#### Scenario: Live film trailer for Хартленд
- **WHEN** `find_trailer` runs with the yt-dlp retriever against live YouTube for the film `Хартленд` / `Heartland` / 2026
- **THEN** the pick's title contains Cyrillic and has no series marker

## MODIFIED Requirements

### Requirement: Candidate ranking
Relevant candidates SHALL be ranked by Cyrillic title first, then, for a series, by a series marker in the title
(`Film or series`), then by how many of the first two cast names occur in the description, then by trailer words
(`трейлер`, `trailer`, `дубляж`) minus teaser words (`тизер`, `teaser`).
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

#### Scenario: Series prefers a series-marked trailer
- **WHEN** the profile is the series `Огонь` / `Огонь` / 2025 and the pool is `Огонь - Финальный трейлер` then `Огонь (2026) — сериал НТВ`
- **THEN** `Огонь (2026) — сериал НТВ` is picked with confidence 0.9

#### Scenario: Series marker outranks cast
- **WHEN** the profile is the series `Огонь` / `Огонь` / 2025 with cast `Иван Янковский`, and the pool is `Огонь — трейлер` whose description names `Иван Янковский`, then `Огонь — трейлер сериала`
- **THEN** `Огонь — трейлер сериала` is picked with confidence 0.9

#### Scenario: Russian title outranks a series marker
- **WHEN** the profile is the series `Огонь` / `Fire` / 2025 and the pool is `Fire | Season 1 | Russian Trailer | 2026 | All About the Series` then `Огонь - Финальный трейлер`
- **THEN** `Огонь - Финальный трейлер` is picked with confidence 0.9

#### Scenario: Season profile counts as a series
- **WHEN** the profile is `Джентльмены` / `The Gentlemen` / 2024 with season 1 and no `series`, and the pool is `Джентльмены — Русский трейлер` then `Джентльмены (1 сезон) — Русский трейлер`
- **THEN** `Джентльмены (1 сезон) — Русский трейлер` is picked with confidence 0.9

### Requirement: Series season
`FilmProfile` SHALL accept an optional `season`, defaulting to None, and SHALL raise `ValueError` at construction
for a season below 1. When a season N is given and the picked candidate's title does not count as season N, the pick's
reason SHALL end with `; season N fallback`, and a WARNING SHALL name
the film and the season. Without a season, no season rule SHALL apply.

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
