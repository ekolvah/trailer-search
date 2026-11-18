## Context

See proposal.md — Why. `title_year_matches(title, film_year)` is the only year gate; `HeuristicStrategy._relevant`
calls it for a truthy profile year.

## Goals / Non-Goals

**Goals:** see proposal.md — What Changes.

**Non-Goals:** the year before (`film_year - 1`) — not observed; ranking an exact-year title above a
release-year title (they tie into the existing `ambiguous` 0.3 pick).

## Decisions

- **Accept `{film_year, film_year + 1}` in `title_year_matches`.** The profile year is the production year
  (kinozal, Kinopoisk), and a premiere is never earlier. Alternative: Emby's symmetric ±1 tolerance — rejected,
  no observed case needs `film_year - 1` and it widens false matches (§VII). A `film_year - 1` test pins this
  boundary.
- **Seed a golden entry from the observed pool.** The five candidates of the reproduction with their real
  YouTube ids, as `scripts/eval_trailers.py --record` re-checks a pinned `correct` id against a live pool;
  `correct` is the list of the Cyrillic trailer ids, because without cast they tie and the `ambiguous` pick is the
  first in pool order, which a `--record` pool from another retriever may reorder. Alternative: unit tests only — rejected, the scorecard is where a later
  ranking change would silently drop this case.

## Risks / Trade-offs

- [A same-title film released the next year (remake, namesake) becomes relevant] → impact measured before the
  proposal: the 32 golden entries give the same pick and confidence with the tolerance applied (monkeypatched
  run, no outcome changed).

## Migration Plan

None; rollback is a revert of the PR.
