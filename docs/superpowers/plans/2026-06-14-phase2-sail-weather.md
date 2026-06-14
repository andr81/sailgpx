# Sailing System — Фаза 2: `/sail-weather` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Скилл `/sail-weather` (forecast / actual / ranking) на Open-Meteo мульти-модель, с агрегацией прогноза по окну гонки, каноническим ансамблевым средним, и накопительным логом точности источников.

**Architecture:** Чистые функции парсинга/агрегации/точности — в `lib/sailweather/` (stdlib; HTTP через `urllib`), тестируются на фикстуре-JSON без сети. SKILL.md дергает lib и редактирует frontmatter заметки. Лог точности — `VAULT/sailing/.weather-accuracy.json`.

**Tech Stack:** Python 3 stdlib (`urllib`, `json`, `math`, `datetime`), Bash. Тесты — assert-скрипт `python3 tests/test_weather.py` на встроенной фикстуре (сеть не нужна).

**Соглашения:** ветер в kt (запрос `wind_speed_unit=kn`), направления — градусы (0°=N); `wind_dir_card` — 8-румбовый; `wind_bucket` ∈ {0-5,5-10,10-15,15-20,20+}.

---

### Task 1: Библиотека `lib/sailweather/` + тесты

Чистые функции: компас/бакет/циклическое среднее, парсинг Open-Meteo мульти-модель, агрегация по окну, сбор forecast-sources + канонический ensemble-mean, обновление лога точности. Плюс тонкие `fetch_json` и сборка URL.

**Files:**
- Create: `REPO/lib/sailweather/__init__.py`, `REPO/lib/sailweather/core.py`
- Test: `REPO/tests/test_weather.py`

Полный код модуля и теста — в дисптач-промпте реализации (транскрипция + прогон). Ключевые сигнатуры:
- `wind_cardinal(deg) -> str` (8-румб), `wind_bucket(kt) -> str`
- `circular_mean_deg(list) -> float|None`, `circular_abs_diff(a,b) -> float`
- `parse_openmeteo(data, models) -> {model: {time,speed,gust,dir}}` (учитывает суффиксы `_<model>`)
- `aggregate_window(times,speed,gust,dir,start,end) -> {wind_speed_kt,wind_gust_kt,wind_dir_deg,wind_dir_card,wind_bucket}`
- `build_forecast(parsed,start,end) -> (canonical, sources[])`
- `accuracy_update(acc, sources, actual) -> acc` (running MAE скорости/направления/порывов, bias)
- `build_forecast_url/ build_archive_url`, `fetch_json(url)`, `ranking(acc) -> sorted list`

Тест покрывает: компас (270→W, 45→NE), бакет (11→"10-15"), циклическое среднее (350,10→0±), parse с суффиксами, aggregate по окну, canonical ensemble-mean из 2 моделей, accuracy_update (running mean, n растёт, dir циклическая ошибка).

- [ ] Steps: фикстура-JSON в тесте → падающий тест → реализация → `PASS test_weather` → commit `feat(sailweather): open-meteo multimodel parse/aggregate/accuracy with tests`.

---

### Task 2: Скилл `skills/sail-weather/SKILL.md`

Контроллер-автор. Режимы:
- **forecast** — определить окно времени гонки (дата + локальные часы старта/финиша; по умолчанию 11:00–14:00 или спросить); `lat/lon` из `venues/<venue>.md`; `build_forecast_url` (модели `ecmwf_ifs025,icon_eu,icon_d2,gfs_global,best_match`); `fetch_json`; `parse_openmeteo`+`build_forecast`; Edit tool → `weather_forecast` (канонический) + `weather_forecast_sources[]` (с `issued`,`lead_h`); кэш сырого JSON в `files/track.weather.json`; человекочитаемая сводка между `<!-- sail:auto:start forecast -->`…`end`; ссылки Windguru из `venue.windguru_spots`; проставить `races[slug].wind_dir_card/wind_bucket` в индексе.
- **actual** — выбрать эталон: `track-derived` (если есть метрики анализатора) → `era5` (archive, гонки старше ~5 дней) → `historical-forecast` (свежие); `build_archive_url`; агрегировать по окну; Edit → `weather_actual` (+`reference`); `accuracy_update` по `.weather-accuracy.json`; строка «прогноз vs факт».
- **ranking** — прочитать `.weather-accuracy.json`, вывести таблицу источников по `wind_speed_mae_kt`.

Правила: kt/градусы; не выдумывать; не трогать пользовательский текст и не-погодные auto-секции; обновлять `updated:`.

- [ ] Steps: написать SKILL.md → `bash tooling/install.sh` → симлинк есть → commit `feat(sail-weather): add /sail-weather skill (forecast/actual/ranking)`.

---

### Task 3: README статус + проверка

- [ ] `/sail-weather` → `ready` в README.
- [ ] Проверка: `python3 tests/test_weather.py`; `test -f skills/sail-weather/SKILL.md`.
- [ ] (Опц., при сети) реальный вызов forecast-URL для venue minskoe-more — убедиться, что JSON приходит и `build_forecast` даёт правдоподобный ветер.
- [ ] Commit + push.

---

## Self-Review

**Spec coverage (§4, §7.2, §8 row 2):** мульти-модель URL ✓ · canonical ensemble + sources[] ✓ · accuracy log (§4.4) ✓ · actual reference (station→track-derived→era5) ✓ · ranking ✓. **Заметка:** physical-station эталон и `track-derived` зависят от внешних данных/анализатора — в `actual` поддержан выбор reference, фактический track-derived подключит фаза 3.

**Placeholder scan:** Task 2 — SKILL.md требованиями (авторится контроллером); код Task 1 даётся целиком в дисптаче. Прочих TODO нет.

**Type consistency:** ключи агрегата (`wind_speed_kt/wind_gust_kt/wind_dir_deg/wind_dir_card/wind_bucket`) совпадают со спекой §3.1 и с `weather_forecast`/`weather_actual`. `accuracy` ключи совпадают со схемой §4.4 (`n/wind_speed_mae_kt/wind_dir_mae_deg/gust_mae_kt/bias_speed_kt`).
