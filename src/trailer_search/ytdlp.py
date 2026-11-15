"""yt-dlp retriever: a flat YouTube search without an API key."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import yt_dlp

from trailer_search.retrieval import MAX_DURATION_S, MAX_RESULTS, search_union
from trailer_search.strategy import Candidate, FilmProfile

# Entries requested per query; duration filtering then keeps the first MAX_RESULTS.
_SEARCH_N = 10


class YtDlpRetriever:
    """Both queries run concurrently; branches not done by `deadline_s` are dropped.
    `socket_timeout` bounds each network read and retries are off, so a blocked branch
    fails fast instead of retrying past the deadline."""

    def __init__(
        self,
        socket_timeout: float = 4,
        *,
        deadline_s: float = 10.0,
        ydl_factory: Callable[[dict[str, Any]], Any] = yt_dlp.YoutubeDL,
    ) -> None:
        if socket_timeout <= 0 or deadline_s <= 0:
            raise ValueError(
                f"socket_timeout and deadline_s must be positive, got {socket_timeout}, {deadline_s}"
            )
        self.deadline_s = deadline_s
        self._ydl_factory = ydl_factory
        self._opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "socket_timeout": socket_timeout,
            "retries": 0,
            "extractor_retries": 0,
        }

    def search_candidates(self, profile: FilmProfile) -> list[Candidate]:
        return search_union(
            profile, self._search_one, max_workers=2, deadline_s=self.deadline_s
        )

    def _search_one(self, query: str) -> list[Candidate]:
        with self._ydl_factory(dict(self._opts)) as ydl:
            info = ydl.extract_info(
                f"ytsearch{_SEARCH_N}:{query}", download=False, ie_key="YoutubeSearch"
            )
        out: list[Candidate] = []
        for entry in info.get("entries") or []:
            duration = entry.get("duration")
            if duration is None or duration >= MAX_DURATION_S:
                continue
            out.append(
                Candidate(
                    video_id=entry["id"],
                    title=entry.get("title") or "",
                    channel=entry.get("channel") or "",
                    description=entry.get("description") or "",
                )
            )
            if len(out) == MAX_RESULTS:
                break
        return out
