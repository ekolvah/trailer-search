# trailer-search

Picks a Russian film trailer from YouTube search results.

## Install

```sh
pip install "trailer-search[ytdlp] @ git+https://github.com/ekolvah/trailer-search@v0.1.0"
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

## Develop

```sh
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest                                  # offline suite
python -m pytest -m live tests/test_live_ytdlp.py # live yt-dlp search
python -X utf8 scripts/eval_trailers.py           # golden-set scorecard and baseline
```
