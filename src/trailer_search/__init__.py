"""Russian trailer selection (RED stub: eager re-export of every retriever)."""

from __future__ import annotations

from trailer_search.retrieval import TrailerRetrievalError, TrailerRetriever
from trailer_search.strategy import Candidate, FilmProfile, TrailerPick
from trailer_search.youtube_api import YoutubeApiRetriever
from trailer_search.ytdlp import YtDlpRetriever

__all__ = [
    "Candidate",
    "FilmProfile",
    "TrailerPick",
    "TrailerRetrievalError",
    "TrailerRetriever",
    "YoutubeApiRetriever",
    "YtDlpRetriever",
    "find_trailer",
]


def find_trailer(profile: FilmProfile, retriever: TrailerRetriever) -> TrailerPick:
    raise NotImplementedError
