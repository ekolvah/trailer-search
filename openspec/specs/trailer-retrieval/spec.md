# trailer-retrieval Specification

## Purpose
Пул кандидатов-трейлеров из YouTube по русскому и оригинальному названию фильма — через YouTube Data API
(с ключом и квотой) или через yt-dlp (без ключа) — и видимый отказ, когда поиск не состоялся.

## Requirements

### Requirement: Query union
A retriever SHALL query `<title> <year> trailer` (or `<title> trailer` without a year) for the Russian title and,
when it is non-empty and differs, for the original title. When the profile gives a season N, the same queries
SHALL instead read `<Russian title> N сезон trailer` and `<original title> season N trailer`, without a year.
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

### Requirement: Retrieval failure
When one query fails and another succeeds, the retriever SHALL log a WARNING naming the failed query and return
the surviving results. When every query fails, it SHALL raise `TrailerRetrievalError` chained to a failure.
Queries that succeed with no results SHALL yield an empty pool without an error.

#### Scenario: One branch fails
- **WHEN** the original-title query raises and the Russian query returns `A`
- **THEN** the pool is `A` and a WARNING names the failed query

#### Scenario: All branches fail
- **WHEN** every query raises
- **THEN** `TrailerRetrievalError` is raised with a branch's exception as its cause

#### Scenario: Empty results are not a failure
- **WHEN** every query succeeds with no results
- **THEN** the pool is empty and no error is raised

### Requirement: Search deadline
When a deadline is set, the search SHALL return within it: a query still running at the deadline SHALL be
dropped with a WARNING naming it, and when no query has succeeded by the deadline the search SHALL raise
`TrailerRetrievalError`. The yt-dlp retriever SHALL set a deadline of 10 seconds by default and SHALL reject a
non-positive deadline or socket timeout at construction with `ValueError`.

#### Scenario: Default deadline
- **WHEN** the yt-dlp retriever is built without a deadline
- **THEN** its deadline is 10 seconds

#### Scenario: Late query dropped
- **WHEN** the original-title query is still running at the deadline and the Russian query returned `A`
- **THEN** the pool `A` is returned within the deadline and a WARNING names the late query

#### Scenario: Blocked yt-dlp search hits the deadline
- **WHEN** every yt-dlp search blocks past the retriever's deadline
- **THEN** `TrailerRetrievalError` is raised within the deadline

#### Scenario: Invalid deadline or timeout rejected
- **WHEN** the yt-dlp retriever is built with `deadline_s` 0 or -1, or with `socket_timeout` 0
- **THEN** `ValueError` is raised

### Requirement: Data API retriever
The YouTube Data API retriever SHALL request at most 5 short videos per query, keep only `youtube#video` items,
and decode HTML entities in title, channel and description. When every query fails and any failure is a quota
error (HTTP 403 or 429 with a usage-limits reason), it SHALL raise `YoutubeQuotaExhausted`, a subclass of
`TrailerRetrievalError`.

#### Scenario: HTML entities decoded
- **WHEN** the API returns the title `Deadpool &amp; Wolverine`
- **THEN** the candidate title is `Deadpool & Wolverine`

#### Scenario: Quota in any failed branch
- **WHEN** the Russian query times out and the original query fails with HTTP 403 reason `quotaExceeded`
- **THEN** `YoutubeQuotaExhausted` is raised

### Requirement: yt-dlp retriever
The yt-dlp retriever SHALL read one flat search results page per query without fetching any video page, keep
at most the first 5 video entries shorter than 240 seconds, and drop entries of unknown duration. It SHALL run
the queries of one film concurrently and pass the caller's `socket_timeout` with bounded retries to yt-dlp.

#### Scenario: Long and unknown-duration entries dropped
- **WHEN** a search page returns entries of 117 s, 600 s and unknown duration
- **THEN** only the 117 s entry becomes a candidate

#### Scenario: Flat search with bounded network options
- **WHEN** the retriever is built with `socket_timeout=4` and searches a film
- **THEN** yt-dlp receives flat extraction, no download, socket timeout 4 and retry counts of 0

#### Scenario: Queries run concurrently
- **WHEN** a film has distinct Russian and original titles
- **THEN** the second query starts before the first query returns

#### Scenario: Live Russian trailer for The Beast
- **WHEN** `find_trailer` runs with the yt-dlp retriever against live YouTube for `Зверь` / `The Beast` / 2026
- **THEN** the pick's title contains Cyrillic and the word `Зверь` and the search finished within the deadline
  with no query dropped
