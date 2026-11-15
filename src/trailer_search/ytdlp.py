"""yt-dlp retriever (RED stub)."""

from __future__ import annotations

from typing import Any

import yt_dlp

from trailer_search.strategy import Candidate, FilmProfile


class YtDlpRetriever:
    deadline_s: float

    def __init__(
        self,
        socket_timeout: float = 4,
        *,
        deadline_s: float = 10.0,
        ydl_factory: Any = yt_dlp.YoutubeDL,
    ) -> None:
        raise NotImplementedError

    def search_candidates(self, profile: FilmProfile) -> list[Candidate]:
        raise NotImplementedError
