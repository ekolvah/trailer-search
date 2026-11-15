"""`YoutubeApiRetriever`, ported from kinozal_scraper `test_youtube.py` (40cd99d).

The googleapiclient resource is replaced by an in-memory double through `client_factory`
(§II); the HTTP errors are real `HttpError` objects with real YouTube response bodies.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from googleapiclient.errors import HttpError

from trailer_search import Candidate, FilmProfile, TrailerRetrievalError
from trailer_search.retrieval import MAX_RESULTS
from trailer_search.youtube_api import (
    YoutubeApiRetriever,
    YoutubeQuotaExhausted,
    _is_quota_error,
)

WOLF = FilmProfile(ru_title="Волк", original_title="The Wolf", year=2025)


def _video_item(video_id: str, title: str, **snippet: str) -> dict[str, Any]:
    return {
        "id": {"kind": "youtube#video", "videoId": video_id},
        "snippet": {"title": title, **snippet},
    }


class _FakeClient:
    """`.search().list(**p).execute()` double; the first needle found in `q` decides the reply."""

    def __init__(self, by_needle: list[tuple[str, Any]]) -> None:
        self.by_needle = by_needle
        self.params: list[dict[str, Any]] = []

    def search(self) -> _FakeClient:
        return self

    def list(self, **params: Any) -> _FakeExec:
        self.params.append(params)
        payload: Any = []
        for needle, items in self.by_needle:
            if needle in params["q"]:
                payload = items
                break
        return _FakeExec(payload)


class _FakeExec:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def execute(self) -> dict[str, Any]:
        if isinstance(self.payload, Exception):
            raise self.payload
        return {"items": self.payload}


def _retriever(client: _FakeClient) -> YoutubeApiRetriever:
    calls: list[tuple[Any, ...]] = []

    def factory(*args: Any, **kwargs: Any) -> _FakeClient:
        calls.append((args, kwargs))
        return client

    retriever = YoutubeApiRetriever(
        "test-key", client_factory=factory
    )  # pragma: allowlist secret
    assert calls == [
        (("youtube", "v3"), {"developerKey": "test-key"})
    ]  # pragma: allowlist secret
    return retriever


def test_maps_snippet_to_candidate_fields() -> None:
    client = _FakeClient(
        [
            (
                "Дюна",
                [
                    _video_item(
                        "v1",
                        "Дюна 2024 трейлер",
                        channelTitle="КиноПоиск",
                        description="официальный русский трейлер",
                        publishedAt="2024-01-10T00:00:00Z",
                    )
                ],
            )
        ]
    )
    profile = FilmProfile(ru_title="Дюна", original_title="Дюна", year=2024)
    assert _retriever(client).search_candidates(profile) == [
        Candidate(
            video_id="v1",
            title="Дюна 2024 трейлер",
            channel="КиноПоиск",
            description="официальный русский трейлер",
            published_at="2024-01-10T00:00:00Z",
        )
    ]


def test_requests_at_most_five_short_videos() -> None:
    client = _FakeClient([])
    _retriever(client).search_candidates(WOLF)
    assert len(client.params) == 2
    for params in client.params:
        assert params["maxResults"] == MAX_RESULTS == 5
        assert params["videoDuration"] == "short"
        assert params["type"] == "video"


def test_html_entities_decoded() -> None:
    client = _FakeClient(
        [
            (
                "Marvel",
                [
                    _video_item(
                        "v1",
                        "Deadpool &amp; Wolverine",
                        description="Marvel&#39;s &quot;Launch&quot;",
                        channelTitle="PlayStation &amp; Insomniac",
                    )
                ],
            )
        ]
    )
    profile = FilmProfile(
        ru_title="Marvel Человек-Паук 2", original_title="", year=2025
    )
    (candidate,) = _retriever(client).search_candidates(profile)
    assert candidate.title == "Deadpool & Wolverine"
    assert candidate.description == 'Marvel\'s "Launch"'
    assert candidate.channel == "PlayStation & Insomniac"


def test_skips_non_video_items() -> None:
    client = _FakeClient(
        [
            (
                "Дюна",
                [
                    {
                        "id": {"kind": "youtube#channel", "channelId": "c1"},
                        "snippet": {},
                    },
                    _video_item("v1", "Дюна 2024 трейлер"),
                ],
            )
        ]
    )
    profile = FilmProfile(ru_title="Дюна", original_title="Дюна", year=2024)
    assert [c.video_id for c in _retriever(client).search_candidates(profile)] == ["v1"]


def test_no_year_filter_in_retrieval() -> None:
    client = _FakeClient([("Дюна", [_video_item("v_old", "Дюна 2015 трейлер")])])
    profile = FilmProfile(ru_title="Дюна", original_title="Дюна", year=2024)
    assert [c.video_id for c in _retriever(client).search_candidates(profile)] == [
        "v_old"
    ]


class _Resp:
    """Status carrier for a real `HttpError`."""

    def __init__(self, status: int, reason: str = "") -> None:
        self.status = status
        self.reason = reason


def _http_error(status: int, body: dict[str, Any]) -> HttpError:
    return HttpError(_Resp(status), json.dumps(body).encode("utf-8"))


_RATE_LIMIT_429 = {
    "error": {
        "code": 429,
        "message": "Rate Limit Exceeded",
        "errors": [
            {
                "message": "Rate Limit Exceeded",
                "domain": "usageLimits",
                "reason": "rateLimitExceeded",
            }
        ],
    }
}
_QUOTA_403 = {
    "error": {
        "code": 403,
        "message": "The request cannot be completed because you have exceeded your quota.",
        "errors": [
            {
                "message": "The request cannot be completed because you have exceeded your quota.",
                "domain": "youtube.quota",
                "reason": "quotaExceeded",
            }
        ],
    }
}
_RATE_LIMIT_ERRORINFO_429 = {
    "error": {
        "code": 429,
        "message": "Quota exceeded for quota metric 'Queries'",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "RATE_LIMIT_EXCEEDED",
                "domain": "youtube.googleapis.com",
            }
        ],
    }
}
_BACKEND_500 = {
    "error": {
        "code": 500,
        "message": "Internal error encountered.",
        "errors": [
            {"message": "Internal error", "domain": "global", "reason": "backendError"}
        ],
    }
}
_FORBIDDEN_403 = {
    "error": {
        "code": 403,
        "message": "The caller does not have permission",
        "errors": [{"message": "Forbidden", "domain": "global", "reason": "forbidden"}],
    }
}


@pytest.mark.parametrize(
    ("body", "status"),
    [(_RATE_LIMIT_429, 429), (_QUOTA_403, 403), (_RATE_LIMIT_ERRORINFO_429, 429)],
)
def test_predicate_matches_real_httperror(body: dict[str, Any], status: int) -> None:
    assert _is_quota_error(_http_error(status, body)) is True


@pytest.mark.parametrize(
    ("body", "status"), [(_BACKEND_500, 500), (_FORBIDDEN_403, 403)]
)
def test_predicate_ignores_non_quota_httperror(
    body: dict[str, Any], status: int
) -> None:
    assert _is_quota_error(_http_error(status, body)) is False


def test_predicate_survives_body_without_machine_reason() -> None:
    assert _is_quota_error(_http_error(429, {"error": {"message": "boom"}})) is False


def test_all_branches_quota_failure_raises_quota_exhausted() -> None:
    err = _http_error(429, _RATE_LIMIT_429)
    client = _FakeClient([("Волк", err), ("The Wolf", err)])
    with pytest.raises(YoutubeQuotaExhausted):
        _retriever(client).search_candidates(WOLF)


def test_quota_in_any_failed_branch() -> None:
    client = _FakeClient(
        [
            ("Волк", TimeoutError("timed out")),
            ("The Wolf", _http_error(403, _QUOTA_403)),
        ]
    )
    with pytest.raises(YoutubeQuotaExhausted) as excinfo:
        _retriever(client).search_candidates(WOLF)
    assert isinstance(excinfo.value, TrailerRetrievalError)


def test_generic_failure_raises_plain_retrieval_error() -> None:
    client = _FakeClient(
        [("Волк", RuntimeError("boom")), ("The Wolf", RuntimeError("boom"))]
    )
    with pytest.raises(TrailerRetrievalError) as excinfo:
        _retriever(client).search_candidates(WOLF)
    assert not isinstance(excinfo.value, YoutubeQuotaExhausted)
