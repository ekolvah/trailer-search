## Why

Для сериала `find_trailer` отдаёт трейлер 1-го сезона: `FilmProfile` знает только `year`, а у сериала это год
первого сезона (issue #5, ekolvah/lampa-mediacenter#64).

**Воспроизведение** (живой YouTube, `YtDlpRetriever`, 2026-11-16): `FilmProfile("Джентльмены", "The Gentlemen",
2024)` → пул из запросов `Джентльмены 2024 trailer` / `The Gentlemen 2024 trailer` содержит
`3xow3-n2VQM` «Джентльмены (2 сезон) - Русский трейлер (Дубляж, 2026) Гай Ричи», но выбран
`Tds2g0cUQpg` «Джентльмены (1 сезон) — Русский трейлер #2 (4К, 2024)», confidence 0.3,
`ambiguous: 4 candidates share top rank`.

**Причина**: два механизма. (1) `title_year_matches` отсекает кандидата 2-го сезона — в его названии 2026, а
`year=2024`. (2) В запросе нет сезона, и ранжирование не различает сезоны, поэтому побеждает первый из
русских роликов 1-го сезона. Запрос с номером сезона без года находит ролики нужного сезона (наблюдение — в
design.md, Standard approach), поэтому `season_year` из issue не вводим (решение владельца, 2026-11-16).

## What Changes

- `FilmProfile.season: int | None = None` — номер нужного сезона; `season < 1` даёт `ValueError` при создании.
- С сезоном N запросы — `<ru_title> N сезон trailer` и `<original_title> season N trailer`, без года.
- С сезоном `year` — нижняя граница: кандидат релевантен, если не называет год раньше `year`.
- Кандидат, в названии которого указан сезон N, стоит в ранжировании выше всех остальных; для N = 1 сезоном 1
  считается и ролик без пометки сезона.
- Если выбранный ролик не про сезон N, это замена: `reason` оканчивается на `; season N fallback`, в лог
  пишется WARNING (§IV).
- Без `season` запросы и выбор не меняются.
- Версия 0.2.0, тег `v0.2.0` для `tools/trailer-search.requirements.txt` lampa-mediacenter.

## Capabilities

### New Capabilities

### Modified Capabilities
- `trailer-selection`: в relevance год с сезоном становится нижней границей, в ranking — сезонный ключ, плюс
  новое требование `Series season` (замена, проверка входа, живой сценарий).
- `trailer-retrieval`: запросы Query union с сезоном.

## Impact

- Изменяются: `src/trailer_search/text.py`, `src/trailer_search/strategy.py`, `src/trailer_search/retrieval.py`,
  `tests/test_strategy.py`, `tests/test_retrieval.py`, `tests/test_live_ytdlp.py`, `pyproject.toml` (version), `README.md` (тег установки и
  `season`).
- Не добавляются и не удаляются файлы кода; новых зависимостей нет.
- Потребители: lampa-mediacenter начинает передавать `season` и пиннит `v0.2.0` (отдельно, в своём репозитории);
  kinozal_scraper `season` не передаёт, его поведение не меняется.
