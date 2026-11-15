"""`YtDlpRetriever` against a `YoutubeDL` double injected through `ydl_factory` (design 6, 12)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
import yt_dlp

from trailer_search import FilmProfile, TrailerRetrievalError
from trailer_search.ytdlp import YtDlpRetriever

BEAST = FilmProfile(ru_title="Зверь", original_title="The Beast", year=2026)


def _entry(video_id: str, duration: float | None, title: str = "") -> dict[str, Any]:
    return {
        "_type": "url",
        "ie_key": "Youtube",
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title or video_id,
        "duration": duration,
        "channel": "ch",
        "description": "desc",
        "upload_date": None,
        "timestamp": None,
    }


class _FakeYDL:
    """`YoutubeDL` double; `on_search(url)` answers every `extract_info` call."""

    def __init__(
        self,
        opts: dict[str, Any],
        on_search: Callable[[str], list[dict[str, Any]]],
        calls: list[dict[str, Any]],
    ) -> None:
        self.opts = opts
        self.on_search = on_search
        self.calls = calls

    def __enter__(self) -> _FakeYDL:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def extract_info(
        self, url: str, download: bool = True, ie_key: str | None = None
    ) -> Any:
        self.calls.append(
            {"url": url, "download": download, "ie_key": ie_key, "opts": self.opts}
        )
        return {"_type": "playlist", "entries": self.on_search(url)}


def _factory(
    on_search: Callable[[str], list[dict[str, Any]]], calls: list[dict[str, Any]]
) -> Callable[[dict[str, Any]], _FakeYDL]:
    return lambda opts: _FakeYDL(opts, on_search, calls)


@pytest.fixture
def release() -> Iterator[threading.Event]:
    """Blocks a fake search; the finalizer frees it even after a failed assert."""
    event = threading.Event()
    yield event
    event.set()


def test_drops_long_and_unknown_duration() -> None:
    calls: list[dict[str, Any]] = []
    retriever = YtDlpRetriever(
        ydl_factory=_factory(
            lambda _url: [_entry("ok", 117), _entry("long", 600), _entry("live", None)],
            calls,
        )
    )
    profile = FilmProfile(ru_title="Зверь", original_title="", year=2026)
    assert [c.video_id for c in retriever.search_candidates(profile)] == ["ok"]


def test_keeps_first_five_short_entries() -> None:
    calls: list[dict[str, Any]] = []
    entries = [_entry(f"v{i}", 60) for i in range(10)]
    retriever = YtDlpRetriever(ydl_factory=_factory(lambda _url: entries, calls))
    profile = FilmProfile(ru_title="Зверь", original_title="", year=2026)
    assert [c.video_id for c in retriever.search_candidates(profile)] == [
        f"v{i}" for i in range(5)
    ]


def test_maps_entry_to_candidate() -> None:
    calls: list[dict[str, Any]] = []
    entry = _entry(
        "J2VS_OlUJtA", 117, "Зверь (2026)#трейлер в русской озвучке#The Beast"
    )
    retriever = YtDlpRetriever(ydl_factory=_factory(lambda _url: [entry], calls))
    profile = FilmProfile(ru_title="Зверь", original_title="", year=2026)
    (candidate,) = retriever.search_candidates(profile)
    assert candidate.video_id == "J2VS_OlUJtA"
    assert candidate.title == "Зверь (2026)#трейлер в русской озвучке#The Beast"
    assert (candidate.channel, candidate.description, candidate.published_at) == (
        "ch",
        "desc",
        "",
    )


def test_flat_search_bounded_options() -> None:
    calls: list[dict[str, Any]] = []
    YtDlpRetriever(
        socket_timeout=4, ydl_factory=_factory(lambda _url: [], calls)
    ).search_candidates(BEAST)
    parsed = yt_dlp.parse_options(
        [
            "--retries",
            "0",
            "--extractor-retries",
            "0",
            "--socket-timeout",
            "4",
            "--flat-playlist",
        ]
    ).ydl_opts
    defaults = yt_dlp.parse_options([]).ydl_opts
    expected = {k: v for k, v in parsed.items() if defaults.get(k) != v}
    assert set(expected) == {
        "retries",
        "extractor_retries",
        "socket_timeout",
        "extract_flat",
    }
    assert len(calls) == 2
    for call in calls:
        assert {k: call["opts"].get(k) for k in expected} == expected
        assert call["opts"]["skip_download"] is True
        assert call["download"] is False
        assert call["ie_key"] == "YoutubeSearch"
        assert call["url"].startswith("ytsearch10:")
    assert sorted(c["url"] for c in calls) == [
        "ytsearch10:The Beast 2026 trailer",
        "ytsearch10:Зверь 2026 trailer",
    ]


def test_queries_run_concurrently(release: threading.Event) -> None:
    calls: list[dict[str, Any]] = []
    second_started_first: list[bool] = []

    def on_search(url: str) -> list[dict[str, Any]]:
        if "Зверь" in url:
            second_started_first.append(release.wait(5))
        else:
            release.set()
        return []

    YtDlpRetriever(ydl_factory=_factory(on_search, calls)).search_candidates(BEAST)
    assert second_started_first == [True]


def test_blocked_search_hits_deadline(release: threading.Event) -> None:
    calls: list[dict[str, Any]] = []

    def blocked(_url: str) -> list[dict[str, Any]]:
        release.wait(5)
        return []

    retriever = YtDlpRetriever(deadline_s=0.2, ydl_factory=_factory(blocked, calls))
    started = time.monotonic()
    with pytest.raises(TrailerRetrievalError):
        retriever.search_candidates(BEAST)
    assert time.monotonic() - started < 0.7


def test_default_deadline_10s() -> None:
    assert YtDlpRetriever().deadline_s == 10.0


@pytest.mark.parametrize(
    "kwargs", [{"deadline_s": 0}, {"deadline_s": -1}, {"socket_timeout": 0}], ids=str
)
def test_invalid_timing_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        YtDlpRetriever(**kwargs)
