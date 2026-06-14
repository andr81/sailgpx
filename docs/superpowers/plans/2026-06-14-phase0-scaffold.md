# Sailing System — Фаза 0: Scaffold + docs-каркас — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать каркас системы: код (резолвер путей, `install.sh`, шаблоны, docs) в репозитории `sailgpx`, данные (`sailing/`) в Obsidian-хранилище; подключить будущие `sail-*` скиллы к репозиторному `install.sh`.

**Architecture:** Source of truth для кода — git-репозиторий `REPO`. У репы свой `tooling/install.sh`, симлинкующий `skills/sail-*` в `~/.claude/skills/` (Obsidian-`tooling` с `life-*` не трогаем). Путь к данным резолвится `tooling/sailenv.sh` из `REPO/.env`. Данные живут в `VAULT/sailing/` и под git не попадают.

**Tech Stack:** Bash, Markdown + YAML frontmatter, Python 3 (валидация YAML в тестах). `REPO` под git → код коммитим обычными `git commit`. Vault не под git → для файлов данных используем verification-чекпоинты.

**Соглашения путей в плане:**
- `REPO` = `/Users/vita/projects/sailgpx`
- `VAULT` = `/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`
- Все пути в командах — абсолютные.

---

### Task 1: Резолвер путей `tooling/sailenv.sh` (в репе)

Sourcing-скрипт: само-локация по `BASH_SOURCE` (репа = родитель `tooling/`), читает `REPO/.env`, экспортирует `SAILING_REPO`, `SAILING_VAULT`, `SAILING_DIR`, `SAILING_TRACKS_DIR`. `SAILING_REPO`/`SAILING_VAULT` переопределяемы извне (для тестов).

**Files:**
- Create: `REPO/tooling/sailenv.sh`
- Test: `REPO/tests/test_sailenv.sh`

- [ ] **Step 1: Написать падающий тест**

Create `/Users/vita/projects/sailgpx/tests/test_sailenv.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
LIB="/Users/vita/projects/sailgpx/tooling/sailenv.sh"
fail=0

# Case 1: .env в репе задаёт SAILING_TRACKS_DIR → используется он
repo1="$(mktemp -d)"
printf 'SAILING_TRACKS_DIR=%s\n' "$repo1/custom-tracks" > "$repo1/.env"
got="$(SAILING_REPO="$repo1" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got" == "$repo1/custom-tracks" ]] || { echo "FAIL case1: got=$got"; fail=1; }

# Case 2: нет .env → дефолт <vault>/sailing/tracks
repo2="$(mktemp -d)"; vault2="$(mktemp -d)"
got2="$(SAILING_REPO="$repo2" SAILING_VAULT="$vault2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got2" == "$vault2/sailing/tracks" ]] || { echo "FAIL case2: got=$got2"; fail=1; }

# Case 3: SAILING_DIR = <vault>/sailing
got3="$(SAILING_REPO="$repo2" SAILING_VAULT="$vault2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_DIR\"")"
[[ "$got3" == "$vault2/sailing" ]] || { echo "FAIL case3: got=$got3"; fail=1; }

rm -rf "$repo1" "$repo2" "$vault2"
[[ $fail -eq 0 ]] && echo "PASS test_sailenv" || { echo "TESTS FAILED"; exit 1; }
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `mkdir -p /Users/vita/projects/sailgpx/tests && bash /Users/vita/projects/sailgpx/tests/test_sailenv.sh`
Expected: FAIL (файл `sailenv.sh` не существует → `source` ошибётся).

- [ ] **Step 3: Написать `sailenv.sh`**

Create `/Users/vita/projects/sailgpx/tooling/sailenv.sh`:

```bash
#!/usr/bin/env bash
# Резолвер путей парусной системы. Использование: source этот файл.
# Экспортирует: SAILING_REPO, SAILING_VAULT, SAILING_DIR, SAILING_TRACKS_DIR.
# SAILING_REPO / SAILING_VAULT можно переопределить извне (тесты).

_sailenv_self="${BASH_SOURCE[0]}"
SAILING_REPO="${SAILING_REPO:-$(cd "$(dirname "$_sailenv_self")/.." && pwd)}"
SAILING_VAULT="${SAILING_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian}"
SAILING_DIR="$SAILING_VAULT/sailing"

if [[ -f "$SAILING_REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SAILING_REPO/.env"
  set +a
fi

SAILING_TRACKS_DIR="${SAILING_TRACKS_DIR:-$SAILING_DIR/tracks}"
export SAILING_REPO SAILING_VAULT SAILING_DIR SAILING_TRACKS_DIR
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `bash /Users/vita/projects/sailgpx/tests/test_sailenv.sh`
Expected: `PASS test_sailenv`

- [ ] **Step 5: Commit**

```bash
cd /Users/vita/projects/sailgpx
git add tooling/sailenv.sh tests/test_sailenv.sh
git commit -m "feat(tooling): add sailenv.sh path resolver with tests"
```

---

### Task 2: `tooling/install.sh` (репозиторный симлинкер `sail-*`)

Новый скрипт в репе (не правка vault'ового). Симлинкует `REPO/skills/sail-*` в `~/.claude/skills/`. Идемпотентен: корректный симлинк — no-op; неверный — перелинковать; реальная папка — бэкап и симлинк. `SRC_DIR` переопределяем через `SAIL_SKILLS_SRC` (для тестов), `DST` — через `CLAUDE_SKILLS_DIR`.

**Files:**
- Create: `REPO/tooling/install.sh`
- Test: `REPO/tests/test_install.sh`

- [ ] **Step 1: Написать падающий тест**

Create `/Users/vita/projects/sailgpx/tests/test_install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
INSTALL="/Users/vita/projects/sailgpx/tooling/install.sh"
fail=0

work="$(mktemp -d)"
src="$work/skills"; dst="$work/dst"
mkdir -p "$src/sail-foo" "$src/sail-bar" "$dst"
echo "x" > "$src/sail-foo/SKILL.md"
echo "x" > "$src/sail-bar/SKILL.md"

SAIL_SKILLS_SRC="$src" CLAUDE_SKILLS_DIR="$dst" bash "$INSTALL" >/dev/null

[[ -L "$dst/sail-foo" ]] || { echo "FAIL: sail-foo not symlinked"; fail=1; }
[[ -L "$dst/sail-bar" ]] || { echo "FAIL: sail-bar not symlinked"; fail=1; }
# повторный прогон не падает (идемпотентность)
SAIL_SKILLS_SRC="$src" CLAUDE_SKILLS_DIR="$dst" bash "$INSTALL" >/dev/null || { echo "FAIL: not idempotent"; fail=1; }

rm -rf "$work"
[[ $fail -eq 0 ]] && echo "PASS test_install" || { echo "TESTS FAILED"; exit 1; }
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `bash /Users/vita/projects/sailgpx/tests/test_install.sh`
Expected: FAIL (`install.sh` не существует).

- [ ] **Step 3: Написать `install.sh`**

Create `/Users/vita/projects/sailgpx/tooling/install.sh`:

```bash
#!/usr/bin/env bash
# Симлинкует sail-* скиллы репозитория в ~/.claude/skills/.
# Идемпотентен: верный симлинк -> no-op; неверный -> перелинк; реальная папка -> бэкап.
set -euo pipefail

TOOLING="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$TOOLING/.." && pwd)"
SRC_DIR="${SAIL_SKILLS_SRC:-$REPO/skills}"
DST_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$DST_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
created=0; updated=0; skipped=0; backed_up=()

shopt -s nullglob
for src in "$SRC_DIR"/sail-*/; do
  [[ -d "$src" ]] || continue
  name="$(basename "$src")"
  src_abs="${src%/}"
  dst="$DST_DIR/$name"

  if [[ -L "$dst" ]]; then
    current="$(readlink "$dst")"
    if [[ "$current" == "$src_abs" ]]; then
      echo "✓ $name already linked"; skipped=$((skipped + 1)); continue
    fi
    rm "$dst"; ln -s "$src_abs" "$dst"
    echo "↻ $name relinked → $src_abs"; updated=$((updated + 1)); continue
  fi

  if [[ -e "$dst" ]]; then
    backup="${dst}.bak.${timestamp}"; mv "$dst" "$backup"; backed_up+=("$backup")
  fi

  ln -s "$src_abs" "$dst"
  echo "+ $name linked → $src_abs"; created=$((created + 1))
done

echo ""
echo "sail-* skills installed into $DST_DIR"
echo "  created: $created"
echo "  updated: $updated"
echo "  unchanged: $skipped"
if (( ${#backed_up[@]} > 0 )); then
  echo "  backed up (real dirs at target path):"
  for b in "${backed_up[@]}"; do echo "    $b"; done
fi
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `bash /Users/vita/projects/sailgpx/tests/test_install.sh`
Expected: `PASS test_install`

- [ ] **Step 5: Commit**

```bash
cd /Users/vita/projects/sailgpx
git add tooling/install.sh tests/test_install.sh
git commit -m "feat(tooling): add install.sh symlinking sail-* skills with tests"
```

---

### Task 3: Каталоги репы, `.env(.example)`, `.gitignore`

**Files:**
- Create: `REPO/.env.example`, `REPO/.env`
- Modify: `REPO/.gitignore`
- Create: каталоги `REPO/{skills,templates}`

- [ ] **Step 1: Создать каталоги репы**

Run:
```bash
mkdir -p /Users/vita/projects/sailgpx/skills /Users/vita/projects/sailgpx/templates
```
Expected: без вывода.

- [ ] **Step 2: `.env.example` (коммитится) и `.env` (локальный)**

Create `/Users/vita/projects/sailgpx/.env.example`:

```
# Корень папок гонок. По умолчанию <vault>/sailing/tracks.
SAILING_TRACKS_DIR=/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing/tracks
```

Create `/Users/vita/projects/sailgpx/.env` с тем же содержимым (копия для локального запуска).

- [ ] **Step 3: Добавить `.env` в `.gitignore`**

В `/Users/vita/projects/sailgpx/.gitignore` добавить строку (в конец):

```
# local env
.env
```

- [ ] **Step 4: Чекпоинт — .env резолвится и не трекается**

Run:
```bash
cd /Users/vita/projects/sailgpx
source tooling/sailenv.sh && echo "tracks=$SAILING_TRACKS_DIR"
git check-ignore .env && echo ".env ignored OK"
```
Expected: путь к `.../sailing/tracks` и `.env ignored OK`.

- [ ] **Step 5: Commit**

```bash
cd /Users/vita/projects/sailgpx
git add .env.example .gitignore
git commit -m "chore: add .env.example and gitignore .env"
```

---

### Task 4: Шаблоны заметок (`REPO/templates/`)

Канонические шаблоны, которые скиллы фазы 1 копируют в vault. Плейсхолдеры `{{...}}` заполняет скилл.

**Files:**
- Create: `REPO/templates/sail-race.md`, `REPO/templates/sail-boat.md`, `REPO/templates/sail-venue.md`

- [ ] **Step 1: `sail-race.md`**

Create `/Users/vita/projects/sailgpx/templates/sail-race.md`:

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

Create `/Users/vita/projects/sailgpx/templates/sail-boat.md`:

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

Create `/Users/vita/projects/sailgpx/templates/sail-venue.md`:

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

- [ ] **Step 4: Чекпоинт + Commit**

Run:
```bash
cd /Users/vita/projects/sailgpx
for f in sail-race sail-boat sail-venue; do test -f "templates/$f.md" || { echo "MISSING $f"; exit 1; }; done
echo "templates ok"
git add templates/
git commit -m "feat(templates): add sail-race / sail-boat / sail-venue note templates"
```
Expected: `templates ok`, затем успешный коммит.

---

### Task 5: `REPO/CLAUDE.md` (правила проекта) и `REPO/README.md` (заготовка)

**Files:**
- Create: `REPO/CLAUDE.md`, `REPO/README.md`

- [ ] **Step 1: `CLAUDE.md`**

Create `/Users/vita/projects/sailgpx/CLAUDE.md`:

```markdown
# sailgpx — правила проекта

Код парусной системы (скиллы, tooling, анализатор, шаблоны). Данные — в Obsidian-vault
(`<vault>/sailing/`), под git НЕ попадают. Полный дизайн:
`docs/superpowers/specs/2026-06-14-sailing-system-design.md`.

## Раскладка
- Код — здесь (`REPO`). Данные — `<vault>/sailing/`. Obsidian-`tooling` (`life-*`) не трогать.
- Скиллы — `skills/sail-*/SKILL.md`; шаблоны заметок — `templates/`.

## Пути
- Путь треков — из `REPO/.env` (`SAILING_TRACKS_DIR`); резолвить `source tooling/sailenv.sh`,
  не хардкодить. `.env` в `.gitignore`; образец — `.env.example`.

## Команды
- Тесты: `bash tests/*.sh`.
- Установка скиллов (симлинки в `~/.claude/skills/`): `bash tooling/install.sh`.
- Анализатор (фаза 3): зависимости `pip install gpxpy pandas numpy scipy haversine`.

## Единицы
- Дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N, по часовой).

## Скиллы
- `/sail-race` — вести гонку (new/update/import).
- `/sail-weather` — погода в заголовки (forecast/actual/ranking).
- `/sail-analyze` — анализ трека (метрики + рендер).
- `/sail-recall` — похожие гонки + инсайты.
Подробности и порядок обработки — в `README.md`.

Не раздувать: детали — в README/спеку, здесь держать правила.
```

- [ ] **Step 2: `README.md` (заготовка)**

Create `/Users/vita/projects/sailgpx/README.md`:

```markdown
# Парусная система (sailgpx)

Подготовка к гонкам и их разбор: заметки по гонке, прогноз и фактическая погода,
импорт GPS-треков, анализ трека как тренер-тактик, поиск похожих гонок и инсайты.

**Код** — в этом репозитории. **Данные** (заметки, треки, справочники) — в Obsidian-vault
`<vault>/sailing/`.

> Статус: каркас (фаза 0). Скиллы добавляются по мере реализации — см.
> `docs/superpowers/plans/`.

## Установка

1. `cp .env.example .env` и при необходимости поправь `SAILING_TRACKS_DIR`.
2. `bash tooling/install.sh` — симлинкует `skills/sail-*` в `~/.claude/skills/`.
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
`docs/superpowers/specs/2026-06-14-sailing-system-design.md`.

## Единицы и конвенции

- Дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N).
- Секция «Мысли и инсайты» — твоя, агент её не трогает.
```

- [ ] **Step 3: Чекпоинт + Commit**

Run:
```bash
cd /Users/vita/projects/sailgpx
test -f CLAUDE.md && grep -q "Типовой порядок" README.md && echo OK
git add CLAUDE.md README.md
git commit -m "docs: add project CLAUDE.md and README skeleton"
```
Expected: `OK`, затем успешный коммит.

---

### Task 6: Scaffolding данных в vault (`VAULT/sailing/`)

Каталоги, JSON-индексы и markdown-справочники в хранилище. **Не под git** → проверяем чекпоинтами.

**Files (в VAULT, без git):**
- Create: каталоги `VAULT/sailing/{boats,venues,tracks}`
- Create: `VAULT/sailing/.race-index.json`, `VAULT/sailing/.weather-accuracy.json`
- Create: `VAULT/sailing/_index.md`, `boats/_index.md`, `venues/minskoe-more.md`, `boats/laser.md`
- Create: `VAULT/sailing/CLAUDE.md`

- [ ] **Step 1: Каталоги и JSON-индексы**

Run:
```bash
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
mkdir -p "$VAULT/sailing/boats" "$VAULT/sailing/venues" "$VAULT/sailing/tracks"
printf '{}\n' > "$VAULT/sailing/.race-index.json"
printf '{}\n' > "$VAULT/sailing/.weather-accuracy.json"
echo "dirs+json ok"
```
Expected: `dirs+json ok`.

- [ ] **Step 2: `sailing/_index.md` (хаб гонок)**

Create `<VAULT>/sailing/_index.md`:

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

- [ ] **Step 3: `sailing/boats/_index.md`**

Create `<VAULT>/sailing/boats/_index.md`:

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

- [ ] **Step 4: `sailing/venues/minskoe-more.md`**

Create `<VAULT>/sailing/venues/minskoe-more.md`:

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

- [ ] **Step 5: `sailing/boats/laser.md` (пример лодки)**

Create `<VAULT>/sailing/boats/laser.md`:

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

- [ ] **Step 6: `VAULT/sailing/CLAUDE.md` (лёгкие правила данных)**

Create `<VAULT>/sailing/CLAUDE.md`:

```markdown
# Sailing (данные) — правила

Автономная папка ДАННЫХ парусной системы. Код и скиллы — в репозитории
`/Users/vita/projects/sailgpx` (`andr81/sailgpx`).

## Границы
- Работаем только внутри `sailing/`. Не трогать остальной vault и `Hobbies/Sailing/`.
- Никаких `[[wiki-link]]` наружу `sailing/`.

## Файлы и вложения
- Вложения гонки — только в `<папка-гонки>/files/`; ссылки в заметке с префиксом `files/`.
- Slug папок гонок и файлов — латиница: `YYYY-MM-DD-<event-slug>[-r<N>]`.

## Единицы
- Дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N).

## Frontmatter
- Имена полей — латиница, значения — русский.
- Ключи поиска похожих: `venue`, `wind_dir_card`, `wind_bucket`, `course_type`,
  `distance_nm`, `class`.

## Неприкосновенное
- Секцию `## Мысли и инсайты` и любой пользовательский текст НЕ перезаписывать.
- Авто-контент только между `<!-- sail:auto:start <name> -->` … `<!-- sail:auto:end <name> -->`.

## Данные
- GPX дедуплицируем по sha256 в `.race-index.json`. Данные не выдумывать — пустое поле
  остаётся пустым.
```

- [ ] **Step 7: Чекпоинт — frontmatter валиден**

Run:
```bash
python3 - <<'PY'
import re
base="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/sailing"
files=["_index.md","boats/_index.md","venues/minskoe-more.md","boats/laser.md"]
try:
    import yaml; have=True
except Exception:
    have=False
for f in files:
    txt=open(f"{base}/{f}",encoding="utf-8").read()
    m=re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    assert m, f"no frontmatter in {f}"
    if have: yaml.safe_load(m.group(1))
assert __import__("os").path.isfile(f"{base}/CLAUDE.md"), "no CLAUDE.md"
print("vault scaffold ok (yaml parsed)" if have else "vault scaffold ok (yaml lib absent)")
PY
```
Expected: `vault scaffold ok ...` без AssertionError. (Vault не под git — коммита нет.)

---

### Task 7: Финальная проверка фазы 0

- [ ] **Step 1: Полный smoke-тест**

Run:
```bash
cd /Users/vita/projects/sailgpx
bash tests/test_sailenv.sh
bash tests/test_install.sh
# репо-артефакты
for p in tooling/sailenv.sh tooling/install.sh .env.example templates/sail-race.md \
         templates/sail-boat.md templates/sail-venue.md CLAUDE.md README.md; do
  test -e "$p" || { echo "MISSING repo:$p"; exit 1; }
done
# vault-данные
VAULT="/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
for p in sailing/.race-index.json sailing/.weather-accuracy.json sailing/_index.md \
         sailing/boats/_index.md sailing/venues/minskoe-more.md sailing/boats/laser.md \
         sailing/CLAUDE.md; do
  test -e "$VAULT/$p" || { echo "MISSING vault:$p"; exit 1; }
done
git status -sb
echo "PHASE 0 OK"
```
Expected: `PASS test_sailenv`, `PASS test_install`, чистый/ожидаемый `git status`, затем `PHASE 0 OK`.

- [ ] **Step 2: Push**

```bash
cd /Users/vita/projects/sailgpx
git push
```
Expected: коммиты фазы 0 уходят в `origin/main`.

---

## Self-Review

**Spec coverage (§8 row 0):** `REPO/tooling/sailenv.sh` (Task 1) ✓ · `REPO/tooling/install.sh` глоб `skills/sail-*` (Task 2) ✓ · `REPO/.env(.example)` (Task 3) ✓ · `REPO/templates/*` (Task 4) ✓ · `REPO/CLAUDE.md` + `README.md` (Task 5) ✓ · vault `sailing/CLAUDE.md`, `_index.md`, `boats/_index.md`, `venues/minskoe-more.md`, пример лодки, JSON-индексы (Task 6) ✓. Финальная проверка + push (Task 7). Покрытие полное.

**Placeholder scan:** `{{...}}` в шаблонах (Task 4) — слоты для скиллов, не плейсхолдеры плана; заполнение — в плане фазы 1. Прочих TODO/TBD нет.

**Type/имена consistency:** `SAILING_REPO/SAILING_VAULT/SAILING_DIR/SAILING_TRACKS_DIR` одинаковы в Task 1 (определение/тест), Task 3 (использование), Task 5 (документация). Переменные тестов `SAIL_SKILLS_SRC`/`CLAUDE_SKILLS_DIR` совпадают между `install.sh` (Task 2 Step 3) и его тестом (Task 2 Step 1). Auto-маркеры `<!-- sail:auto:start <name> -->` совпадают в шаблоне (Task 4) и vault CLAUDE.md (Task 6). Ключи frontmatter совпадают со спекой §3.

**Git:** `REPO` под git → реальные коммиты (Task 1–5) + push (Task 7). `.env` в `.gitignore` (Task 3). Vault-данные (Task 6) под git не идут — проверяются чекпоинтами.
