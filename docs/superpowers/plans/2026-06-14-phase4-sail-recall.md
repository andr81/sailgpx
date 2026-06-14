# Sailing System — Фаза 4: `/sail-recall` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Скилл `/sail-recall` — найти похожие прошлые гонки (venue/ветер/дистанция/класс) по `.race-index.json` и синтезировать советы из их инсайтов и результатов.

**Architecture:** Чистая функция ранжирования — `lib/sailrecall/core.py` (по кэшу заголовков `races` из `.race-index.json`). SKILL.md читает индекс, ранжирует, открывает заметки-кандидаты, извлекает «Мысли и инсайты»/результаты и формирует брифинг.

**Tech Stack:** Python 3 stdlib. Тест — `python3 tests/test_recall.py` на синтетическом индексе.

---

### Task 1: `lib/sailrecall/core.py` + тест

`find_similar(index, query, exclude=None, min_score=3, limit=10)` — скоринг: venue (+3), wind_dir_card (точно +2 / соседний румб +1)×, wind_bucket (точно +2 / соседний +1), course_type (+1), class (+1), distance_nm в допуске (+1). Возвращает ранжированный список с `slug`/`score`.

- [ ] Steps: падающий тест (синтетический индекс из 3–4 гонок; запрос W/10-15 на minskoe-more → ближайшая первой) → реализация → `PASS test_recall` → commit.

---

### Task 2: Скилл `skills/sail-recall/SKILL.md`

Контроллер-автор. Workflow: собрать query (из текущей гонки/заметки или из аргументов: venue, wind_dir_card, wind_bucket, course_type, distance_nm, class); прочитать `.race-index.json`; `find_similar`; для топ-N открыть заметки гонок, извлечь секцию `## Мысли и инсайты`, `result`, метрики анализа; синтезировать брифинг (не список файлов): повторяющиеся инсайты, что работало при похожем ветре/акватории, типичные ошибки, советы на новую гонку. Может вызываться из `/sail-race new`.

- [ ] Steps: написать SKILL.md → `install.sh` → симлинк → commit.

---

### Task 3: README статус + проверка + push

- [ ] `/sail-recall` → `ready`.
- [ ] `python3 tests/test_recall.py`; все тесты; `test -f skills/sail-recall/SKILL.md`.
- [ ] Commit + push.

---

## Self-Review

**Spec coverage (§7.4, §8 row 4):** ранжирование по venue/wind_dir_card/wind_bucket/course_type/distance_nm/class ✓ · синтез инсайтов из похожих ✓ · вызов из new ✓.

**Placeholder scan:** lib даётся целиком; SKILL.md — требования. TODO нет.

**Type consistency:** ключи query/`races`-записи совпадают со схемой `.race-index.json` (фаза 1) и ключами поиска §3.1.
