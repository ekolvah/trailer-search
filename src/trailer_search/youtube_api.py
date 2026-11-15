"""YouTube Data API retriever, ported from kinozal_scraper `youtube.py` (40cd99d)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from googleapiclient.discovery import build

from trailer_search.retrieval import MAX_RESULTS, TrailerRetrievalError, search_union
from trailer_search.strategy import Candidate, FilmProfile


class YoutubeQuotaExhausted(TrailerRetrievalError):
    """The Data API quota is exhausted: further calls are pointless for the run."""


# Google usageLimits-family reasons; at our call volume rate and daily limits coincide.
_QUOTA_REASONS = frozenset(
    {
        "quotaexceeded",
        "dailylimitexceeded",
        "ratelimitexceeded",
        "userratelimitexceeded",
    }
)


def _is_quota_error(exc: BaseException) -> bool:
    """Whether an `HttpError` means exhausted quota. Reads the machine reason in
    `error_details` (legacy `errors[].reason` or ErrorInfo `details[].reason`), not the
    human `.reason` text; Google returns these as 403 as well as 429."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status not in (403, 429):
        return False
    details = getattr(exc, "error_details", None)
    if not isinstance(details, list):
        return False
    for detail in details:
        reason = detail.get("reason") if isinstance(detail, dict) else None
        if (
            isinstance(reason, str)
            and reason.replace("_", "").lower() in _QUOTA_REASONS
        ):
            return True
    return False


class YoutubeApiRetriever:
    """Candidate pool through `search.list`, one query at a time to spare the quota."""

    def __init__(
        self, api_key: str, *, client_factory: Callable[..., Any] = build
    ) -> None:
        self._client = client_factory("youtube", "v3", developerKey=api_key)

    def search_candidates(self, profile: FilmProfile) -> list[Candidate]:
        return search_union(profile, self._search_one, max_workers=1)

    def _search_one(self, query: str) -> list[Candidate]:
        """One query → `youtube#video` candidates. Snippet text is HTML-escaped
        (`Marvel&#39;s`) and is decoded here, at the protocol boundary."""
        try:
            response = (
                self._client.search()
                .list(
                    q=query,
                    part="id,snippet",
                    maxResults=MAX_RESULTS,
                    type="video",
                    videoDuration="short",
                )
                .execute()
            )
        except Exception as exc:
            if _is_quota_error(exc):
                raise YoutubeQuotaExhausted(
                    f"YouTube quota exhausted on {query!r}"
                ) from exc
            raise
        out: list[Candidate] = []
        for item in response.get("items", []):
            if item.get("id", {}).get("kind") != "youtube#video":
                continue
            snippet = item.get("snippet", {})
            out.append(
                Candidate(
                    video_id=item["id"]["videoId"],
                    title=html.unescape(snippet.get("title", "")),
                    channel=html.unescape(snippet.get("channelTitle", "")),
                    description=html.unescape(snippet.get("description", "")),
                    published_at=snippet.get("publishedAt", ""),
                )
            )
        return out
