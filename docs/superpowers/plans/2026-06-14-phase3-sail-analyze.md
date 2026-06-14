# Sailing System — Фаза 3: `/sail-analyze` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Анализатор GPS-трека как тренер-тактик: метрики скорости/курса/ветра/поворотов/ног + SVG-рендер трека, в заметку гонки.

**Architecture:** Чистый Python (stdlib), поверх `lib/sailtrack/gpx.py`. Модуль `lib/sailtrack/analyze.py` — пайплайн (resample 1 Гц → COG/SOG сглаживание → TWD из погоды или оценка из трека → TWA/курс → детект поворотов → сегментация ног → агрегаты). `lib/sailtrack/render.py` — SVG-рендер трека (раскраска по скорости), без matplotlib. SKILL.md дергает CLI-обёртку и пишет результаты в заметку.

**Tech Stack:** Python 3 stdlib (`math`), Bash. **Отклонение от спеки §6:** numpy/scipy/pandas/matplotlib НЕ используются (нет колёс под Python 3.14) — stdlib-реализация; рендер — SVG вместо PNG. Метрики и пайплайн соответствуют §6; %-of-polar, VMC к знакам и route-efficiency-разложение — будущее (нужны polar/координаты знаков, §9).

**Соглашения:** kt/nm/градусы; углы — циклическая арифметика.

---

### Task 1: `lib/sailtrack/analyze.py` + `render.py` + тест

**Files:**
- Create: `REPO/lib/sailtrack/analyze.py`, `REPO/lib/sailtrack/render.py`
- Create: `REPO/tests/test_analyze.py` (синтетический windward-leeward трек)

Покрытие теста: на синтетическом треке (лавировка ±45° от N + спуск на юг) — оценка TWD ≈ 0±25°, детект ≥2 поворотов, классификация курса (upwind/downwind присутствуют), upwind VMG>0, рендер SVG создаётся и содержит `<polyline`/`<path`.

Реализация — авторская (контроллер), затем code-quality ревью. Публичный API:
- `analyze_track(points, twd=None, boat=None) -> dict` (summary: speed, wind, maneuvers, legs, groove).
- `estimate_twd(samples) -> float` (axis-tensor + выбор «from» по меньшей upwind-скорости).
- `render_svg(points, out_path, by="speed")`.

- [ ] Steps: фикстура-генератор в тесте → падающий тест → реализация → `PASS test_analyze` → smoke на реальном треке (TWD/повороты правдоподобны) → commit.

---

### Task 2: CLI-обёртка `lib/sailtrack/cli.py` + Скилл `skills/sail-analyze/SKILL.md`

- `cli.py`: `python3 -m sailtrack.cli <track.gpx> [--twd N] [--boat-json ...]` → печатает JSON summary; опц. `--svg out.svg`.
- SKILL.md (контроллер-автор): резолв путей; взять `track.gpx` гонки; TWD из `weather_actual.wind_dir_deg` если есть, иначе оценка; запустить CLI → JSON; SVG в `files/track-render.svg`; **Edit tool** → таблица метрик между `<!-- sail:auto:start analysis -->` … `end` + `![[files/track-render.svg]]`; дописать `track:` (tacks/gybes/...); `status: analyzed`; (опц.) записать `track-derived` ветер для `/sail-weather actual`.

- [ ] Steps: написать cli.py + SKILL.md → `install.sh` → симлинк → commit.

---

### Task 3: README статус + проверка + push

- [ ] `/sail-analyze` → `ready`; добавить в README заметку про stdlib/SVG-отклонение.
- [ ] Проверка: `python3 tests/test_analyze.py`; все прочие тесты; CLI на реальном треке.
- [ ] Commit + push.

---

## Self-Review

**Spec coverage (§6, §7.3, §8 row 3):** пайплайн resample→COG/SOG→TWD→TWA→повороты→ноги→агрегаты ✓ · TWD из погоды или оценка из трека ✓ · повороты+углы+цена ✓ · ноги/groove ✓ · SVG-рендер ✓ · запись в заметку + `status: analyzed` ✓. **Отклонение** (stdlib/SVG, без %-polar/VMC/route-decomp) задокументировано выше и в §9.

**Placeholder scan:** реализация авторская (не плейсхолдер); SKILL.md — требования. TODO нет.

**Type consistency:** `analyze_track`/`estimate_twd`/`render_svg` — едины в тесте, cli.py и SKILL.md. Ключи `track:` (tacks/gybes/duration_min/...) совпадают с фазой 1 и §3.1.
