# Sailing System — Фаза 0: Scaffold + docs-каркас — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать автономный каркас системы `sailing/` в Obsidian-хранилище: разрешение путей через `.env`, scaffolding папок/хабов/справочников, шаблоны заметок, подключение будущих `sail-*` скиллов к `install.sh`, и docs-каркас (`CLAUDE.md` + заготовка `README.md`).

**Architecture:** Все артефакты живут в `<vault>/sailing/` и `<vault>/tooling/`. Путь к трекам резолвится shell-функцией `tooling/sailenv.sh` (читает `sailing/.env`, дефолт — `sailing/tracks`). Скиллы (фазы 1+) симлинкуются в `~/.claude/skills/` через `tooling/install.sh`. Это фундамент; функциональные скиллы — отдельные планы.

**Tech Stack:** Bash (POSIX/zsh-совместимый), Markdown + YAML frontmatter, Python 3 (только для валидации YAML в тестах). Git отсутствует и в хранилище, и в `projects/sailgpx` → вместо `git commit` используем verification-чекпоинты (команда проверки в конце каждой задачи). Git-инициализацию не делаем.

**Соглашения путей в плане:**
- `VAULT` = `/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`
- Все пути ниже — абсолютные, чтобы исполнялись из любого cwd.

---

### Task 1: Резолвер путей `tooling/sailenv.sh`

Общий sourcing-скрипт: вычисляет корень хранилища от `$HOME`, читает `sailing/.env`, экспортирует `SAILING_VAULT`, `SAILING_DIR`, `SAILING_TRACKS_DIR`. Не лежит под `skills/`, поэтому `install.sh` его не симлинкует. Позволяет переопределить `SAILING_VAULT` извне (для тестов).

**Files:**
- Create: `/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/sailenv.sh`
- Test: `/Users/vita/projects/sailgpx/tests/test_sailenv.sh`

- [ ] **Step 1: Написать падающий тест**

Create `/Users/vita/projects/sailgpx/tests/test_sailenv.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
LIB="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/sailenv.sh"
fail=0

# Case 1: .env задаёт SAILING_TRACKS_DIR → используется он
tmp1="$(mktemp -d)"; mkdir -p "$tmp1/sailing"
printf 'SAILING_TRACKS_DIR=%s\n' "$tmp1/custom-tracks" > "$tmp1/sailing/.env"
got="$(SAILING_VAULT="$tmp1" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got" == "$tmp1/custom-tracks" ]] || { echo "FAIL case1: got=$got"; fail=1; }

# Case 2: нет .env → дефолт <vault>/sailing/tracks
tmp2="$(mktemp -d)"; mkdir -p "$tmp2/sailing"
got2="$(SAILING_VAULT="$tmp2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got2" == "$tmp2/sailing/tracks" ]] || { echo "FAIL case2: got=$got2"; fail=1; }

# Case 3: экспортирован SAILING_DIR
got3="$(SAILING_VAULT="$tmp2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_DIR\"")"
[[ "$got3" == "$tmp2/sailing" ]] || { echo "FAIL case3: got=$got3"; fail=1; }

rm -rf "$tmp1" "$tmp2"
[[ $fail -eq 0 ]] && echo "PASS test_sailenv" || { echo "TESTS FAILED"; exit 1; }
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `bash /Users/vita/projects/sailgpx/tests/test_sailenv.sh`
Expected: FAIL (файл `sailenv.sh` не существует → `source` ошибётся, ненулевой код выхода).

- [ ] **Step 3: Написать `sailenv.sh`**

Create `/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/sailenv.sh`:

```bash
#!/usr/bin/env bash
# Резолвер путей парусной системы. Использование: source этот файл.
# Экспортирует: SAILING_VAULT, SAILING_DIR, SAILING_TRACKS_DIR.
# SAILING_VAULT можно переопределить извне (тесты); иначе вычисляется от $HOME.

SAILING_VAULT="${SAILING_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian}"
SAILING_DIR="$SAILING_VAULT/sailing"

if [[ -f "$SAILING_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SAILING_DIR/.env"
  set +a
fi

SAILING_TRACKS_DIR="${SAILING_TRACKS_DIR:-$SAILING_DIR/tracks}"
export SAILING_VAULT SAILING_DIR SAILING_TRACKS_DIR
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `bash /Users/vita/projects/sailgpx/tests/test_sailenv.sh`
Expected: `PASS test_sailenv`

- [ ] **Step 5: Чекпоинт**

Run: `test -f "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/sailenv.sh" && echo OK`
Expected: `OK`

---

### Task 2: `install.sh` — добавить глоб `sail-*`

Текущий цикл симлинкует только `life-*`. Добавляем `sail-*` в тот же цикл и обновляем финальное сообщение. Guard `[[ -d "$src" ]] || continue` уже корректно пропускает несуществующий glob.

**Files:**
- Modify: `/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/install.sh`
- Test: `/Users/vita/projects/sailgpx/tests/test_install.sh`

- [ ] **Step 1: Написать падающий тест**

Create `/Users/vita/projects/sailgpx/tests/test_install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
INSTALL="$VAULT/tooling/install.sh"
fail=0

# Тестовое окружение: фейковый SRC с dummy sail-foo и life-bar, отдельный DST
work="$(mktemp -d)"
src="$work/skills"; dst="$work/dst"
mkdir -p "$src/sail-foo" "$src/life-bar" "$dst"
echo "x" > "$src/sail-foo/SKILL.md"
echo "x" > "$src/life-bar/SKILL.md"

# install.sh резолвит SRC относительно своего расположения, поэтому копируем его в work
cp "$INSTALL" "$work/install.sh"
mkdir -p "$work/skills"   # уже есть
CLAUDE_SKILLS_DIR="$dst" bash "$work/install.sh" >/dev/null

[[ -L "$dst/sail-foo" ]] || { echo "FAIL: sail-foo not symlinked"; fail=1; }
[[ -L "$dst/life-bar" ]] || { echo "FAIL: life-bar not symlinked"; fail=1; }

rm -rf "$work"
[[ $fail -eq 0 ]] && echo "PASS test_install" || { echo "TESTS FAILED"; exit 1; }
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `bash /Users/vita/projects/sailgpx/tests/test_install.sh`
Expected: FAIL с `sail-foo not symlinked` (текущий цикл глобит только `life-*`).

- [ ] **Step 3: Изменить цикл и сообщение в `install.sh`**

В `/Users/vita/.../tooling/install.sh` заменить строку цикла:

```bash
for src in "$SRC_DIR"/life-*/; do
```

на:

```bash
for src in "$SRC_DIR"/life-*/ "$SRC_DIR"/sail-*/; do
```

И заменить финальное сообщение:

```bash
echo "life-* skills installed into $DST_DIR"
```

на:

```bash
echo "life-* / sail-* skills installed into $DST_DIR"
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `bash /Users/vita/projects/sailgpx/tests/test_install.sh`
Expected: `PASS test_install`

- [ ] **Step 5: Чекпоинт — реальный прогон не ломает life-* симлинки**

Run: `bash "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/install.sh"`
Expected: вывод содержит `life-* / sail-* skills installed`; строки `✓ life-ingest already linked` и т.п. (sail-* пока нет — это нормально).

---

### Task 3: Scaffolding папок, `.env`, индексы

Создать дерево `sailing/`, файл `.env`, и пустые JSON-индексы.

**Files:**
- Create: `<vault>/sailing/.env`
- Create: `<vault>/sailing/.race-index.json`
- Create: `<vault>/sailing/.weather-accuracy.json`
- Create: каталоги `<vault>/sailing/{boats,venues,tracks,.templates}`

- [ ] **Step 1: Создать каталоги**

Run:
```bash
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
mkdir -p "$VAULT/sailing/boats" "$VAULT/sailing/venues" "$VAULT/sailing/tracks" "$VAULT/sailing/.templates"
```
Expected: без вывода (успех).

- [ ] **Step 2: Создать `.env` с дефолтным путём треков**

Create `<vault>/sailing/.env`:

```
# Корень папок гонок. По умолчанию <vault>/sailing/tracks.
# Можно указать иной путь (напр. на внешнем диске).
SAILING_TRACKS_DIR=/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/tracks
```

- [ ] **Step 3: Инициализировать JSON-индексы**

Create `<vault>/sailing/.race-index.json`:

```json
{}
```

Create `<vault>/sailing/.weather-accuracy.json`:

```json
{}
```

- [ ] **Step 4: Чекпоинт — .env резолвится через sailenv.sh**

Run:
```bash
source "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/tooling/sailenv.sh"
echo "$SAILING_TRACKS_DIR"
python3 -c "import json; json.load(open('$SAILING_DIR/.race-index.json')); json.load(open('$SAILING_DIR/.weather-accuracy.json')); print('json ok')"
```
Expected: путь к `.../sailing/tracks` и `json ok`.

---

### Task 4: Хабы и справочники (`_index`, venue, пример лодки)

Markdown-файлы с валидным frontmatter по схемам спеки §3.

**Files:**
- Create: `<vault>/sailing/_index.md`
- Create: `<vault>/sailing/boats/_index.md`
- Create: `<vault>/sailing/venues/minskoe-more.md`
- Create: `<vault>/sailing/boats/laser.md`

- [ ] **Step 1: `sailing/_index.md` (хаб гонок)**

Create `<vault>/sailing/_index.md`:

```markdown
---
title: "Парусные гонки"
type: catalog
domain: sailing
created: 2026-06-14
updated: 2026-06-14
summary: "Хаб системы: гонки, лодки, акватории."
---

# Парусные гонки

Справочники: [[boats/_index|Лодки]] · [[venues/minskoe-more|Минское море]]

## Все гонки

```dataview
TABLE date, event, class, course_type, weather_actual.wind_dir_card AS "ветер", weather_actual.wind_speed_kt AS "kt", result.position AS "место", status
FROM "sailing/tracks"
WHERE type = "sail-race"
SORT date DESC
```
```

- [ ] **Step 2: `sailing/boats/_index.md`**

Create `<vault>/sailing/boats/_index.md`:

```markdown
---
title: "Лодки"
type: catalog
domain: sailing
created: 2026-06-14
updated: 2026-06-14
summary: "Справочник лодок и классов."
---

# Лодки

```dataview
TABLE class, rig, crew, hull_length_m AS "длина, м"
FROM "sailing/boats"
WHERE type = "sail-boat"
SORT class ASC
```
```

- [ ] **Step 3: `sailing/venues/minskoe-more.md` (координаты по факту треков)**

Create `<vault>/sailing/venues/minskoe-more.md`:

```markdown
---
title: "Минское море"
type: sail-venue
slug: minskoe-more
lat: 53.97
lon: 27.38
windguru_spots: [311332, 110353]
landmarks: ""
prevailing_winds: ""
created: 2026-06-14
updated: 2026-06-14
summary: "Заславское водохранилище под Минском — основная акватория."
---

# Минское море

Заславское водохранилище (~53.97 N, 27.38 E).

- Прогноз/архив: Open-Meteo по `lat/lon` выше.
- Windguru: [311332](https://www.windguru.cz/311332) · [110353 ExtremeClub](https://www.windguru.cz/110353)

## Ориентиры и заметки
```

- [ ] **Step 4: `sailing/boats/laser.md` (пример лодки)**

Create `<vault>/sailing/boats/laser.md`:

```markdown
---
title: "Laser (ILCA)"
type: sail-boat
slug: laser
class: "Laser"
hull_length_m: 4.23
crew: 1
sail_area_m2: 7.06
rig: dinghy
upwind_twa: 45
downwind_twa: 150
polar: null
created: 2026-06-14
updated: 2026-06-14
tags: []
summary: "Швертбот-одиночка; лавировка ~45°, спуск ~150° (идёт галсами вниз)."
---

## Заметки

## Выходы и гонки

```dataview
TABLE date, event, result.position AS "место", weather_actual.wind_speed_kt AS "ветер kt"
FROM "sailing/tracks"
WHERE type = "sail-race" AND boat = "laser"
SORT date DESC
```
```

- [ ] **Step 5: Чекпоинт — frontmatter валиден**

Run:
```bash
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
python3 - <<'PY'
import re, sys
base="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing"
files=["_index.md","boats/_index.md","venues/minskoe-more.md","boats/laser.md"]
try:
    import yaml
    have_yaml=True
except Exception:
    have_yaml=False
for f in files:
    txt=open(f"{base}/{f}",encoding="utf-8").read()
    m=re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    assert m, f"no frontmatter in {f}"
    if have_yaml:
        yaml.safe_load(m.group(1))
print("frontmatter ok (yaml parsed)" if have_yaml else "frontmatter present (yaml lib absent, skipped parse)")
PY
```
Expected: `frontmatter ok ...` или `frontmatter present ...` без AssertionError.

---

### Task 5: Шаблоны заметок (`.templates/`)

Канонические шаблоны, которые скиллы фазы 1 будут копировать. Плейсхолдеры в фигурных скобках `{{...}}` заполняет скилл.

**Files:**
- Create: `<vault>/sailing/.templates/sail-race.md`
- Create: `<vault>/sailing/.templates/sail-boat.md`
- Create: `<vault>/sailing/.templates/sail-venue.md`

- [ ] **Step 1: `sail-race.md`**

Create `<vault>/sailing/.templates/sail-race.md`:

```markdown
---
title: "{{title}}"
type: sail-race
date: {{date}}
venue: {{venue}}
boat: {{boat}}
class: "{{class}}"
event: "{{event}}"
race_no: {{race_no}}
discipline: fleet
course_type: {{course_type}}
distance_nm: {{distance_nm}}
laps: {{laps}}
status: planned
weather_forecast: {}
weather_forecast_sources: []
weather_actual: {}
result: {}
track: {}
tags: []
created: {{date}}
updated: {{date}}
summary: ""
---

## Дистанция

## Прогноз

<!-- sail:auto:start forecast -->
<!-- sail:auto:end forecast -->

## Анализ трека

<!-- sail:auto:start analysis -->
<!-- sail:auto:end analysis -->

## Результат

## Мысли и инсайты
```

- [ ] **Step 2: `sail-boat.md`**

Create `<vault>/sailing/.templates/sail-boat.md`:

```markdown
---
title: "{{title}}"
type: sail-boat
slug: {{slug}}
class: "{{class}}"
hull_length_m: {{hull_length_m}}
crew: {{crew}}
sail_area_m2: {{sail_area_m2}}
rig: {{rig}}
upwind_twa: {{upwind_twa}}
downwind_twa: {{downwind_twa}}
polar: null
created: {{date}}
updated: {{date}}
tags: []
summary: ""
---

## Заметки

## Выходы и гонки

```dataview
TABLE date, event, result.position AS "место", weather_actual.wind_speed_kt AS "ветер kt"
FROM "sailing/tracks"
WHERE type = "sail-race" AND boat = "{{slug}}"
SORT date DESC
```
```

- [ ] **Step 3: `sail-venue.md`**

Create `<vault>/sailing/.templates/sail-venue.md`:

```markdown
---
title: "{{title}}"
type: sail-venue
slug: {{slug}}
lat: {{lat}}
lon: {{lon}}
windguru_spots: []
landmarks: ""
prevailing_winds: ""
created: {{date}}
updated: {{date}}
summary: ""
---

# {{title}}

## Ориентиры и заметки
```

- [ ] **Step 4: Чекпоинт — все шаблоны на месте**

Run:
```bash
T="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/.templates"
for f in sail-race sail-boat sail-venue; do test -f "$T/$f.md" || { echo "MISSING $f"; exit 1; }; done
echo "templates ok"
```
Expected: `templates ok`

---

### Task 6: `sailing/CLAUDE.md` (правила подсистемы для агента)

**Files:**
- Create: `<vault>/sailing/CLAUDE.md`

- [ ] **Step 1: Написать `CLAUDE.md`**

Create `<vault>/sailing/CLAUDE.md`:

```markdown
# Sailing — правила подсистемы

Автономная парусная подсистема внутри Obsidian-хранилища. Дополняет, не заменяет
корневой `CLAUDE.md`. Полный дизайн: `/Users/vita/projects/sailgpx/docs/superpowers/specs/2026-06-14-sailing-system-design.md`.

## Границы
- Работаем только внутри `sailing/`. Не трогать остальной vault и `Hobbies/Sailing/`.
- Никаких `[[wiki-link]]` наружу `sailing/`.

## Пути
- Корень треков — из `sailing/.env` (`SAILING_TRACKS_DIR`); резолвить через
  `source <vault>/tooling/sailenv.sh`, не хардкодить.
- Вложения гонки — только в `<папка-гонки>/files/`; ссылки в заметке с префиксом `files/`.

## Единицы
- Дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N, по часовой).

## Frontmatter
- Имена полей — латиница, значения — русский.
- Slug папок гонок и файлов — латиница: `YYYY-MM-DD-<event-slug>[-r<N>]`.
- Ключи поиска похожих: `venue`, `wind_dir_card`, `wind_bucket`, `course_type`,
  `distance_nm`, `class`.

## Неприкосновенное
- Секцию `## Мысли и инсайты` и любой пользовательский текст НЕ перезаписывать.
- Авто-контент только между маркерами `<!-- sail:auto:start <name> -->` …
  `<!-- sail:auto:end <name> -->`.

## Данные
- GPX дедуплицируем по sha256 в `.race-index.json`. Данные не выдумывать — пустое
  поле остаётся пустым.

## Команды
- Переустановить скиллы: `bash <vault>/tooling/install.sh`.
- Анализатор (фаза 3): `python3` из каталога скилла `sail-analyze` (зависимости:
  `gpxpy pandas numpy scipy haversine`).

## Скиллы
- `/sail-race` — вести гонку (new/update/import).
- `/sail-weather` — погода в заголовки (forecast/actual/ranking).
- `/sail-analyze` — анализ трека (метрики + рендер).
- `/sail-recall` — похожие гонки + инсайты.
Подробности и порядок — в `README.md`.
```

- [ ] **Step 2: Чекпоинт**

Run: `test -f "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/CLAUDE.md" && head -1 "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/CLAUDE.md"`
Expected: `# Sailing — правила подсистемы`

---

### Task 7: `sailing/README.md` (заготовка)

Каркас README; разделы скиллов дописываются по мере их реализации (фазы 1–4), финальный проход — фаза 5.

**Files:**
- Create: `<vault>/sailing/README.md`

- [ ] **Step 1: Написать заготовку `README.md`**

Create `<vault>/sailing/README.md`:

```markdown
# Парусная система (sailing/)

Подготовка к гонкам и их разбор: заметки по гонке, прогноз и фактическая погода,
импорт GPS-треков, анализ трека как тренер-тактик, поиск похожих гонок и инсайты.

> Статус: каркас (фаза 0). Скиллы добавляются по мере реализации — см. план
> `/Users/vita/projects/sailgpx/docs/superpowers/plans/`.

## Установка

1. Путь треков: при необходимости поправь `sailing/.env` (`SAILING_TRACKS_DIR`).
2. Скиллы: `bash <vault>/tooling/install.sh` (симлинкует `sail-*` в `~/.claude/skills/`).
3. Зависимости анализатора (фаза 3): `pip install gpxpy pandas numpy scipy haversine`.

## Скиллы

| Скилл | Назначение | Режимы | Статус |
|-------|-----------|--------|--------|
| `/sail-race` | вести гонку | new / update / import | planned |
| `/sail-weather` | погода в заголовки | forecast / actual / ranking | planned |
| `/sail-analyze` | анализ трека | — | planned |
| `/sail-recall` | похожие гонки + инсайты | — | planned |

## Типовой порядок загрузки и обработки

```
ДО ГОНКИ
  /sail-race new            создать папку + заметку, выбрать boat/venue/дистанцию
  (приложить course.png)    схема дистанции
  /sail-weather forecast    мульти-модельный прогноз в заголовки + план
ПОСЛЕ ГОНКИ
  /sail-race import <gpx>   импорт трека (дедуп, копия, базовая сводка)
  /sail-analyze             метрики тренера-тактика + рендер трека
  /sail-weather actual      фактическая погода (эталон) + лог точности источников
  /sail-race update         результат + свои мысли в «Мысли и инсайты»
  /sail-recall              похожие гонки + советы (можно и ДО гонки)
```

## Структура и формат

Структура папок и frontmatter-схемы — в дизайн-спеке
`/Users/vita/projects/sailgpx/docs/superpowers/specs/2026-06-14-sailing-system-design.md`.

## Единицы и конвенции

- Дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N).
- Секция «Мысли и инсайты» — твоя, агент её не трогает.
```

- [ ] **Step 2: Чекпоинт**

Run: `test -f "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/README.md" && grep -q "Типовой порядок" "/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/README.md" && echo OK`
Expected: `OK`

---

### Task 8: Финальная проверка фазы 0

- [ ] **Step 1: Полный smoke-тест каркаса**

Run:
```bash
bash /Users/vita/projects/sailgpx/tests/test_sailenv.sh
bash /Users/vita/projects/sailgpx/tests/test_install.sh
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
for p in sailing/.env sailing/.race-index.json sailing/.weather-accuracy.json \
         sailing/_index.md sailing/boats/_index.md sailing/venues/minskoe-more.md \
         sailing/boats/laser.md sailing/CLAUDE.md sailing/README.md \
         sailing/.templates/sail-race.md sailing/.templates/sail-boat.md sailing/.templates/sail-venue.md \
         tooling/sailenv.sh; do
  test -e "$VAULT/$p" || { echo "MISSING $p"; exit 1; }
done
echo "PHASE 0 OK"
```
Expected: `PASS test_sailenv`, `PASS test_install`, затем `PHASE 0 OK`.

---

## Self-Review

**Spec coverage (§8 row 0):** `.env` (Task 3) ✓ · `_index.md` (Task 4) ✓ · `boats/_index.md` (Task 4) ✓ · `venues/minskoe-more.md` (Task 4) ✓ · шаблоны заметок (Task 5) ✓ · правка `install.sh` глоб `sail-*` (Task 2) ✓ · `sailing/CLAUDE.md` (Task 6) ✓ · заготовка `README.md` (Task 7) ✓. Резолвер путей `sailenv.sh` (Task 1) — инфраструктура под `.env`, нужен скиллам фаз 1+. Покрытие полное.

**Placeholder scan:** Шаблоны в Task 5 намеренно содержат `{{...}}` — это слоты для скиллов, не плейсхолдеры плана; их заполнение специфицируется в плане фазы 1. Прочих TODO/TBD нет.

**Type/имена consistency:** `SAILING_VAULT/SAILING_DIR/SAILING_TRACKS_DIR` одинаковы в Task 1 (определение), Task 3/4 (использование), Task 6 (документация). Auto-маркеры `<!-- sail:auto:start <name> -->` совпадают в шаблоне (Task 5) и CLAUDE.md (Task 6). Ключи frontmatter совпадают со спекой §3.

**Примечание:** git отсутствует → шаги «Чекпоинт» заменяют коммиты. Если позже инициализируем git в хранилище — добавим `.race-index.json`/`.weather-accuracy.json`/`.env` в `.gitignore` (приватные данные), по аналогии с `Health/.ingest-index.json`.
