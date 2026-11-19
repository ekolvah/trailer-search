# trailer-search

Picks a Russian film trailer from YouTube search results.

## Install

```sh
pip install "trailer-search[ytdlp] @ git+https://github.com/ekolvah/trailer-search@v0.2.0"  # x-release-please-version
```

Extras: `ytdlp` for `YtDlpRetriever` (no API key), `youtube-api` for `YoutubeApiRetriever`
(YouTube Data API). The base package has no dependencies and imports neither.

## Use

```python
from trailer_search import FilmProfile, TrailerPick, TrailerRetrievalError, find_trailer
from trailer_search.ytdlp import YtDlpRetriever

pick: TrailerPick = find_trailer(FilmProfile(ru_title, original_title, year),
                                 YtDlpRetriever(socket_timeout=4))
# TrailerPick(video_id: str | None, title: str | None, confidence: float, reason: str)
```

`video_id=None` means no relevant candidate. `TrailerRetrievalError` means no search
query succeeded within the deadline (`YtDlpRetriever(deadline_s=10.0)` by default).
For a series, pass `FilmProfile(..., season=N)` with `year` of the first season: the pick is
season N's trailer, or the best other one with `; season N fallback` ending `reason`.

## Develop

```sh
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest                                  # offline suite
python -m pytest -m live tests/test_live_ytdlp.py # live yt-dlp search
python -X utf8 scripts/eval_trailers.py           # golden-set scorecard and baseline
```
