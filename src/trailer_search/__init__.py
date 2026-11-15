"""Russian trailer selection for a film. Retrievers live in `trailer_search.ytdlp` and
`trailer_search.youtube_api`, so the base import loads neither extra."""

from __future__ import annotations

from trailer_search.retrieval import TrailerRetrievalError, TrailerRetriever
from trailer_search.strategy import (
    Candidate,
    FilmProfile,
    HeuristicStrategy,
    TrailerPick,
)

__all__ = [
    "Candidate",
    "FilmProfile",
    "TrailerPick",
    "TrailerRetrievalError",
    "TrailerRetriever",
    "find_trailer",
]


def find_trailer(profile: FilmProfile, retriever: TrailerRetriever) -> TrailerPick:
    """Retrieve candidates and pick one; a retrieval failure propagates as
    `TrailerRetrievalError`, distinct from a pick with `video_id=None`."""
    return HeuristicStrategy().pick(profile, retriever.search_candidates(profile))
