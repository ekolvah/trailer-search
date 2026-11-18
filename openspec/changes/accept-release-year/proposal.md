## Why

A film whose profile year is its production year loses every trailer titled with its release year.
Reproduction (live yt-dlp, 2026-11-18): `FilmProfile("Коммерсант", "Коммерсант", 2025)` →
`YtDlpRetriever().search_candidates` returns 5 candidates, among them `Коммерсант · Трейлер · Фильм 2026`,
`Коммерсант. Трейлер (2026)`, `Коммерсант - Трейлер 2026`; `HeuristicStrategy().pick` returns
`TrailerPick(None, None, 0.0, 'no title+year match')`. The film premiered on 23 April 2026, as the trailer
title `Коммерсант (2025) | Официальный трейлер (18+) | В кино с 23 апреля 2026` (8th result) states.

Root cause: `title_year_matches` (`src/trailer_search/text.py:9-12`) rejects a title naming any year other
than `film_year`, so the one-year gap between production and premiere excludes every Cyrillic trailer.

## Standard approach

- Emby's TMDB matching tolerates one year: "We handle the year ourselves to allow for a one year tolerance"
  — https://emby.media/community/topic/83645-incorrect-identification-not-using-year
- FileBot users report a film filed as 2019 or 2020 because TMDB release dates differ
  — https://www.filebot.net/forums/viewtopic.php?p=60031
- Radarr rejects a parsed year that mismatches (changelog "Don't match if movie year parsed but is mismatch")
  without documenting a tolerance — https://newreleases.io/project/github/Radarr/Radarr/release/v4.5.2.7388

## What Changes

- Candidate relevance also admits a title naming the year after the film's year (the release year).
- A golden-set entry records the Коммерсант case; the eval baseline grows by one hit.

Out of scope: `MAX_RESULTS` truncation of the yt-dlp pool and Latin transliteration (`Kommersant`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `trailer-selection`: Candidate relevance admits the year after the film's year.

## Impact

- Edited: `src/trailer_search/text.py`, `tests/test_text.py`, `tests/test_strategy.py`,
  `tests/fixtures/trailer_golden.json`, `tests/fixtures/trailer_baseline.json`.
- Added: none. Removed: none. Public API unchanged.
