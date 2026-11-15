"""YouTube Data API retriever (RED stub)."""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from trailer_search.retrieval import TrailerRetrievalError
from trailer_search.strategy import Candidate, FilmProfile


class YoutubeQuotaExhausted(TrailerRetrievalError):
    """The Data API quota is exhausted."""


def _is_quota_error(exc: Exception) -> bool:
    raise NotImplementedError


class YoutubeApiRetriever:
    def __init__(self, api_key: str, *, client_factory: Any = build) -> None:
        raise NotImplementedError

    def search_candidates(self, profile: FilmProfile) -> list[Candidate]:
        raise NotImplementedError
