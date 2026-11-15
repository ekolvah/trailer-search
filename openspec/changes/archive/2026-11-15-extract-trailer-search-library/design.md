## Context

Репозиторий пуст, кроме agent-process. Источник переноса — kinozal_scraper `40cd99d`:
`src/kinozal_scraper/trailer_strategy.py` (210 строк), `youtube.py` (164), три функции `text_utils.py`
(`has_cyrillic`, `normalize_title`, `title_year_matches`), `scripts/eval_trailers.py` (628, из них ~200 —
TMDB- и delivery-прогоны kinozal), `tests/fixtures/trailer_golden.json`, `trailer_baseline.json` и тесты
`test_trailer_strategy.py`, `test_youtube.py`, `test_text_utils.py`, `test_eval_trailers.py`,
`test_eval_baseline.py`. Наблюдения — в proposal.md, «Why».

## Standard approach

- Встраивание yt-dlp: `YoutubeDL(opts).extract_info("ytsearchN:<query>", download=False)`, плоская выдача через
  `extract_flat` — https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp. Наблюдение `yt-dlp --help` 2026.10.26:
  `-R, --retries RETRIES  Number of retries (default is 10)`, `--extractor-retries RETRIES  Number of retries
  for known extractor errors (default is 3)`, `--socket-timeout SECONDS  Time to wait before giving up`.
  Выход плоского поиска — в proposal.md.
- YouTube Data API `search.list`, `videoDuration=short`: «Only include videos that are less than four minutes
  long» — https://developers.google.com/youtube/v3/docs/search/list.
- Пакет: `pyproject.toml` по PEP 621, extras в `[project.optional-dependencies]` —
  https://packaging.python.org/en/latest/guides/writing-pyproject-toml/; установка
  `name @ git+https://…@tag` — https://pip.pypa.io/en/stable/topics/vcs-support/.
- Время ответа: бюджет на весь запрос, делённый между зависимостями, и общий дедлайн операции поверх таймаута
  отдельной попытки — https://oneuptime.com/blog/post/2026-08-14-retry-timeout-deadline-budget/view,
  https://alivedise.github.io/backend-engineering-essentials/resilience/timeouts-and-deadlines; путь таймаута
  проверяется заглушкой, которая не отвечает —
  https://rithikpyne.com/blog/2024/building-reliable-python-apis-timeouts-retries-idempotency-and-observability/.
  CPU-бенчмарки на общих раннерах шумят: для 1% ложных срабатываний нужен порог около 7% —
  https://codspeed.io/blog/benchmarks-in-ci-without-noise.
- Выбор трейлера: none found: веб-поиск «python library find movie trailer youtube by title year select best
  result» (2026-11-15) дал только поисковые обёртки (https://pypi.org/project/youtube-search-python/1.4.5,
  «intended for personal and non-commercial usage only») и загрузчики с выбором по рейтингу/качеству
  (https://github.com/KBlixt/Trailer-Downloader/blob/master/README.md, TMDB-ключ в
  https://libraries.io/pypi/trailerdl), без выбора по языку. Прецедент — `HeuristicStrategy` kinozal_scraper,
  измеренная на эталонном наборе.

## Goals / Non-Goals

**Goals:** перенос без изменения поведения выбора (та же скоркарта 29/2/1); второй источник кандидатов — yt-dlp;
контракт issue #1.

**Non-Goals:** TMDB-подбор и delivery-прогон kinozal (`select_trailer`, маркеры ответа) — они остаются в
kinozal_scraper; `FirstResultStrategy`; LLM/эмбеддинг-пикеры kinozal; публикация на PyPI; замер 10 с на armv7
(его проверяет lampa-mediacenter#48 на приставке).

## Decisions

1. **Модули.** `text.py` (3 функции), `strategy.py` (типы, `TrailerStrategy`, `HeuristicStrategy`),
   `retrieval.py` (`TrailerRetrievalError`, протокол `TrailerRetriever`, `search_union`), `youtube_api.py`,
   `ytdlp.py`; `__init__.py` реэкспортирует контракт и определяет `find_trailer`. Альтернатива — один модуль:
   отвергнута, extras требуют, чтобы `yt_dlp` и `googleapiclient` импортировались только в своих модулях.
2. **`TrailerPick.title`.** Новое поле обязательно и идёт вторым, как в контракте issue #1;
   `HeuristicStrategy` заполняет его из выбранного кандидата, без выбора — `None`. Альтернатива — заполнять
   только в `find_trailer`: отвергнута, у стратегии и `find_trailer` был бы разный смысл одного типа.
3. **`find_trailer(profile, retriever)`** вызывает `HeuristicStrategy` напрямую — как в контракте issue #1;
   параметра стратегии нет: других реализаций нет. Протокол `TrailerStrategy` переносится в `strategy.py`
   (его реализуют пикеры kinozal), но в контракт пакета не входит. Ошибку поиска не ловит (§III): kinozal
   превращает её в свой маркер, Lampa — в свой ответ.
4. **Общий `search_union(profile, search_one, *, max_workers)`.** Построение запросов, порядок пула, дедупликация,
   WARNING на упавшую ветку и отказ при падении всех веток — один код для обоих ретриверов. Доменная ошибка
   рождается там, где известна: `search_one` Data API сам поднимает `YoutubeQuotaExhausted` на квотной ошибке.
   Когда упали все ветки, `search_union` поднимает класс первой ветки, упавшей подклассом
   `TrailerRetrievalError`, иначе базовый `TrailerRetrievalError`, с `from` на исключение этой ветки. Так
   квота остаётся знанием Data API, а перехвата с повторным выбросом и поля `causes` нет. Порядок пула не
   зависит от порядка завершения: результаты собираются по индексу запроса (ранжирование стабильно, порядок
   решает ничьи).
5. **Data API последовательно (`max_workers=1`), yt-dlp параллельно (`max_workers=2`).** Data API — без
   изменения поведения kinozal; клиент `googleapiclient` на `httplib2` многопоточность не гарантирует
   (https://googleapis.github.io/google-api-python-client/docs/thread_safety.html). При одном запросе или
   `max_workers=1` без дедлайна запросы идут прямо в вызывающем потоке, без пула (с дедлайном — решение 12). У yt-dlp каждый запрос получает свой
   `YoutubeDL`.
6. **yt-dlp за протоколом (§II).** `YtDlpRetriever(socket_timeout=4, *, deadline_s=10.0,
   ydl_factory=yt_dlp.YoutubeDL)` (дедлайн — решение 12);
   тесты подставляют фабрику-двойник. Опции: `extract_flat="in_playlist"`, `skip_download=True`, `quiet=True`,
   `socket_timeout`, `retries=0`, `extractor_retries=0`; вызов `extract_info(url, download=False,
   ie_key="YoutubeSearch")` — без перебора экстракторов. Повторов нет: две параллельные ветки страхуют друг
   друга, а один повтор при таймауте 4 с уже даёт 8 с из бюджета 10 с. Запрос `ytsearch10:`, затем первые
   `MAX_RESULTS` видео с `duration < MAX_DURATION_S`. Обе константы (5 и 240) — политика пула библиотеки в
   `retrieval.py` (не полные фильмы и не длинные ролики): Data API выражает её параметрами
   `maxResults`/`videoDuration=short` (сверка — тест), yt-dlp — фильтром на клиенте. Запись без `duration`
   (трансляция) отбрасывается. Плоская выдача — одна страница поиска YouTube, 10 вместо 5 запросов не добавляет.
   Имена ключей сверены с yt-dlp 2026.10.26 (2026-11-15): `yt_dlp.parse_options(['--retries','0',
   '--extractor-retries','0','--socket-timeout','4','--flat-playlist']).ydl_opts` даёт `{'retries': 0,
   'extractor_retries': 0, 'socket_timeout': 4.0, 'extract_flat': 'in_playlist'}`;
   `yt_dlp.extractor.youtube.YoutubeSearchIE.ie_key()` → `YoutubeSearch`. `YoutubeDL` молча принимает
   неизвестный ключ, поэтому `test_flat_search_bounded_options` сверяет опции ретривера с выводом
   `parse_options` установленного yt-dlp — опечатка или переименование при бампе пина валит тест.
7. **`YoutubeApiRetriever(api_key, *, client_factory=googleapiclient.discovery.build)`** — клиент за
   фабрикой, как у yt-dlp (§II); библиотека не читает окружение. `--record` берёт `API_KEY` и пишет пулы через
   этот ретривер по протоколу `TrailerRetriever`; модульной `search_candidates(client, profile)` нет.
8. **Эталонный набор — копия файла без правок.** `tmdb_videos` загрузчик читает только как источник
   допустимых id для `correct` (6 из 32 записей ссылаются туда); TMDB-оценки нет. Альтернатива — удалить поле:
   отвергнута, 6 записей перестанут проходить валидацию или потеряют проверку опечаток в `correct`.
9. **Ворота — по `find_trailer`.** `tests/test_eval_baseline.py` гонит `find_trailer` с замороженным
   ретривером и сравнивает исходы по случаям с `tests/fixtures/trailer_baseline.json`. Файл — копия
   базовой линии kinozal `40cd99d`, не перезапись: так зелёные ворота доказывают паритет с kinozal по каждому
   случаю. В kinozal ворота стояли на delivery-слое, которого здесь нет; публичная точка входа библиотеки —
   `find_trailer`, она и измеряется. Скоркарты kinozal для стратегии и delivery совпадают (29/2/1).
   `--update-baseline` переносится для будущих осознанных изменений выбора; `--threshold` — нет (его не
   требует ни одна спецификация, ворота — базовая линия).
10. **Живой тест «Зверь»** — `tests/test_live_ytdlp.py` с маркером `live`; `addopts = "-m 'not live'"` в
    `pyproject.toml` исключает его из CI явно (сеть YouTube в CI нестабильна и не про регрессию кода).
    Запускается задачей `python -m pytest -m live`, проверяет кириллицу и слово `Зверь`, а не id: id дрейфуют.
11. **Сборка — setuptools**, `pythonpath = ["src"]` для pytest и `mypy_path = "src"`; `yt_dlp` и
    `googleapiclient` без типов — `[[tool.mypy.overrides]] ignore_missing_imports`. `requirements.txt` пинует
    `yt-dlp==2026.10.26` и `google-api-python-client==2.195.0` для CI и pip-audit; extras в `pyproject.toml`
    задают нижние границы этих же версий. `requires-python = ">=3.12"` (kinozal 3.12, Lampa 3.13).
    Хук mypy в `.pre-commit-config.yaml` работает в своём окружении с `args: []`: `import pytest` в тестах там
    не разрешится, поэтому хуку добавляется `additional_dependencies: [pytest]`; `scripts/__init__.py` (как в
    kinozal `40cd99d`) убирает двойное имя модуля `eval_trailers`/`scripts.eval_trailers`. Проверка — прогон
    объявленного `test` в задаче 6.3.
12. **Дедлайн поиска.** `socket_timeout` ограничивает одно сетевое ожидание, а не вызов: несколько запросов
    yt-dlp или медленная отдача по частям могут выйти за 10 с из issue #1. Поэтому
    `search_union(..., deadline_s: float | None)`: `None` — ждать все ветки (Data API: пакетный прогон kinozal
    без бюджета, поведение не меняется); у yt-dlp `deadline_s=10.0` по умолчанию, вызывающий может уменьшить.
    Отсчёт — `time.monotonic()` от входа в `search_union`. С дедлайном ветки всегда идут в пуле, даже одна:
    запрос в вызывающем потоке нельзя бросить. Ожидание — `concurrent.futures.wait(futures, timeout=остаток)`,
    затем `executor.shutdown(wait=False, cancel_futures=True)`; блок `with` не годится — его выход ждёт потоки.
    Работающий поток остановить нельзя: он идёт, пока yt-dlp не вернёт управление, а результат отбрасывается.
    Документация `Executor.shutdown`: `with` завершает пул «as if Executor.shutdown() were called with wait set
    to True», и «Regardless of the value of wait, the entire Python program will not exit until all pending
    futures are done executing» —
    https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor.shutdown. Прогон
    архитектора на Python 3.12.8: `wait(timeout=0.2)` и `shutdown(wait=False, cancel_futures=True)` вернули
    управление через 0,22 с, а процесс с заблокированным потоком не завершился, пока его не убил `timeout 6`. Не успевшая ветка — WARNING с её запросом; ни одна не успела успешно — `TrailerRetrievalError`.
    Время каждой ветки и всего поиска — INFO, чтобы p95 был виден в логах потребителей. Неположительные
    `deadline_s` или `socket_timeout` — `ValueError` в конструкторе (§VI). Тесты ждут заглушку на
    `threading.Event`, а не на `sleep`: дедлайн около 0,2 с, допуск проверки 0,5 с. Событие освобождает
    финализатор фикстуры, в том числе после упавшего assert, а `Event.wait` заглушки ограничен страховочными 5 с.
    Иначе упавший тест (и `test_queries_run_concurrently` против последовательной реализации) повесит pytest
    по той же причине. Data API вызывает `search_union` с `deadline_s=None`. Альтернатива — CPU-бенчмарк (CodSpeed, pytest-benchmark): отвергнута, выбор из 5 кандидатов
    почти не тратит процессор, время уходит на сеть, шум раннеров требует порога ~7%, и это новая зависимость.

## Risks / Trade-offs

- [yt-dlp сломается при смене вёрстки YouTube] → все запросы падают → `TrailerRetrievalError`, а не пустой пул;
  потребитель видит отказ. Обновление — бамп пина и тег.
- [Сколько поисков успевает за 10 с на armv7, здесь не измерить] → дедлайн гарантирует время ответа на любом
  устройстве; долю успевших ответов на приставке меряет lampa-mediacenter#48 по логам длительности.
- [YouTube завис] → каждый вызов оставляет в фоне до 2 потоков, пока yt-dlp не вернёт управление; медленная
  отдача по частям может длиться дольше `socket_timeout`. Число потоков ограничено частотой вызовов потребителя,
  и они задерживают завершение его процесса (решение 12).
- [Пулы yt-dlp отличаются от пулов Data API] → эталонный набор меряет выбор, не поиск; живой тест покрывает
  поиск yt-dlp на одном фильме.
- [kinozal_scraper#647 удаляет свой эталонный набор, а его TMDB- и delivery-прогоны на нём стоят] → отметить в
  #647 при переходе; эта библиотека их не переносит.

## Migration Plan

Слияние PR, затем тег `v0.1.0` на коммите слияния (с согласия человека). Откат — удалить тег до перехода
потребителей; после — новый тег с исправлением. Потребители переходят в своих issue.
