## Why

Выбор русского трейлера из выдачи YouTube нужен двум проектам: ekolvah/kinozal_scraper (там он уже есть,
`HeuristicStrategy` + YouTube Data API) и ekolvah/lampa-mediacenter#48 (приставка Ugoos, Debian 13 armhf,
Python 3.13, поиск через yt-dlp без ключа и квоты). Решение пользователя 2026-11-07: одна реализация в этой
библиотеке, а не две копии (issue #1). Переход kinozal_scraper — ekolvah/kinozal_scraper#647, он ждёт тег
`v0.1.0`. Решение пользователя 2026-11-15: сервис отвечает быстро независимо от устройства — время ответа
ограничено общим дедлайном вызова, а не только таймаутом сокета.

Наблюдения, на которые опирается план (2026-11-15):

- kinozal_scraper HEAD = `40cd99d`; `python scripts/eval_trailers.py` там печатает для `HeuristicStrategy`
  `score=27  hit=29 miss=2 wrong=1 (n=32)` и `baseline: match (score=27, n=32)`.
- yt-dlp 2026.10.26, `extract_info("ytsearch5:Зверь 2026 трейлер", download=False)` с
  `extract_flat="in_playlist"`, `socket_timeout=4`: 1,24 с на x86; в выдаче есть
  `{"id": "J2VS_OlUJtA", "title": "Зверь (2026)#трейлер в русской озвучке#The Beast", "duration": 117,
  "channel": "ElektroniKK.Трейлеры Кино.Новинки.", "description": "с 9 октября 2026 года в кино. …"}`;
  у плоских записей `upload_date` и `timestamp` = `null`, `duration` заполнен.
- В эталонном наборе 6 из 32 записей ссылаются в `correct` на id, которых нет в `candidates`, а есть только
  в `tmdb_videos` (например, `Носферату` → `dkv5KtVG4T0`): без этого поля валидатор набора отвергнет файл.

## What Changes

- Пакет `trailer_search` (src-layout, `pyproject.toml`, версия 0.1.0, Python ≥ 3.12), ставится по git-URL.
- Перенос из kinozal_scraper `40cd99d`: `FilmProfile`, `Candidate`, `TrailerPick`, `TrailerStrategy`,
  `HeuristicStrategy` и три функции `text_utils`, которые она использует; `TrailerPick` получает поле
  `title` из контракта issue #1. `FirstResultStrategy` не переносится: в kinozal она только для сравнения.
- `find_trailer(profile, retriever)` — публичная точка входа: поиск кандидатов + `HeuristicStrategy`.
- Общий для ретриверов поиск-объединение по русскому и оригинальному названию с дедупликацией и
  `TrailerRetrievalError`, когда упали все запросы.
- `YoutubeApiRetriever` (перенос `youtube.py`, extra `youtube-api`) с `YoutubeQuotaExhausted`.
- `YtDlpRetriever` (новый, extra `ytdlp`): плоская выдача, параллельные запросы, ограниченные таймаут и повторы,
  общий дедлайн вызова (по умолчанию 10 с) и время каждого запроса в логе.
- Эталонный набор `tests/fixtures/trailer_golden.json` (копия без изменений), `scripts/eval_trailers.py`
  (оценка стратегии, `--record`, базовая линия) и тест-ворота по базовой линии в CI.
- Тег `v0.1.0` после слияния.

## Capabilities

### New Capabilities
- `trailer-selection`: публичный контракт пакета, выбор трейлера `HeuristicStrategy`, `find_trailer`, установка.
- `trailer-retrieval`: пул кандидатов из YouTube через Data API или yt-dlp и отказ поиска.
- `trailer-eval`: эталонный набор, скоркарта и ворота по базовой линии.

### Modified Capabilities

## Impact

Добавляются:

- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `README.md`
- `src/trailer_search/__init__.py`, `py.typed`, `text.py`, `strategy.py`, `retrieval.py`, `youtube_api.py`,
  `ytdlp.py`
- `scripts/__init__.py`, `scripts/eval_trailers.py`
- `tests/fixtures/trailer_golden.json`, `tests/fixtures/trailer_baseline.json`
- `tests/test_text.py`, `tests/test_strategy.py`, `tests/test_find_trailer.py`, `tests/test_retrieval.py`,
  `tests/test_youtube_api.py`, `tests/test_ytdlp.py`, `tests/test_eval_trailers.py`,
  `tests/test_eval_baseline.py`, `tests/test_live_ytdlp.py`

Правится: `.pre-commit-config.yaml` — хуку mypy `additional_dependencies: [pytest]`. Удаляется: ничего.
`.github/agent-process-quality.json` уже ставит `requirements*.txt` и запускает pytest через `pre-commit`.

Зависимости (решение пользователя в issue #1): `yt-dlp` и `google-api-python-client` — только extras;
базовая установка без зависимостей. Внешние потребители: kinozal_scraper#647 и lampa-mediacenter#48.
