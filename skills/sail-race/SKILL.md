---
name: sail-race
description: Вести заметку парусной гонки в Obsidian-vault — создать папку и заметку (new), импортировать GPS-трек GPX из WaterSpeed или иного источника (import), обновить результат и мысли (update). Данные в sailing/tracks, дедуп GPX по sha256, единицы nm/kt. Activates on /sail-race, "новая гонка", "добавить гонку", "импортировать трек", "обновить гонку", "загрузить gpx".
---

# Sail Race

Ведение заметки парусной гонки. Код — в репозитории, данные — в Obsidian-vault.

## ⛔ Критические правила

- **НЕ ПРИДУМЫВАЙ** данные — только из источника/пользователя. Пустое поле → пустым.
- **Единицы:** дистанции — nm, скорости и ветер — kt, направления — градусы (0°=N).
- Имена полей frontmatter — латиница; значения — русский. Slug папки гонки — латиница.
- **Не перезаписывай** секцию `## Мысли и инсайты` и любой пользовательский текст.
  Авто-контент — только между `<!-- sail:auto:start <name> -->` … `<!-- sail:auto:end <name> -->`.
- Всегда обновляй поле `updated:` при правке заметки.

## Конфигурация

```bash
SAILING_REPO="/Users/vita/projects/sailgpx"
source "$SAILING_REPO/tooling/sailenv.sh"   # → SAILING_DIR, SAILING_TRACKS_DIR
```

- Шаблоны: `$SAILING_REPO/templates/sail-race.md`.
- Библиотека трека: `$SAILING_REPO/lib` (модуль `sailtrack.gpx`).
- Индекс: `$SAILING_DIR/.race-index.json` — структура:

```json
{
  "races":  { "<slug>": { "date": "...", "venue": "...", "boat": "...", "class": "...",
                          "course_type": "...", "distance_nm": 0,
                          "wind_dir_card": null, "wind_bucket": null, "path": "tracks/<slug>" } },
  "tracks": { "<sha256>": "<slug>" }
}
```

`tracks` — дедуп GPX по sha256; `races` — кэш заголовков для `/sail-recall`.
Если файла нет — считать `{"races":{},"tracks":{}}`.

## Dispatch

Определи режим по запросу:
- создать гонку / «новая гонка» / до гонки → **new**;
- передан путь к `.gpx` / «импортировать трек» → **import**;
- «результат» / «обновить» / дописать мысли → **update**.

Если режим неясен — спроси через `AskUserQuestion` (new / import / update).

---

## Режим: new

1. Собери поля (`AskUserQuestion`, если не даны): `date` (YYYY-MM-DD), `event`,
   `boat` (slug из `boats/`), `venue` (slug из `venues/`, по умолчанию `minskoe-more`),
   `course_type` (windward-leeward | triangle | coastal | distance), `distance_nm`,
   `race_no`, `laps`. Для `class` — прочитай `boats/<boat>.md` и возьми `class`.
2. Сформируй slug: `<date>-<event-translit>[-r<race_no>]`, латиница, kebab-case
   (транслитерация кириллицы в латиницу). Пример: `2026-06-14-kubok-otkrytia-r3`.
3. Создай папку и заметку:

```bash
RACE_DIR="$SAILING_TRACKS_DIR/<slug>"
mkdir -p "$RACE_DIR/files"
cp "$SAILING_REPO/templates/sail-race.md" "$RACE_DIR/<slug>.md"
```

4. Заполни `{{...}}` в заметке через **Edit tool** (title — человеческое русское
   название, напр. «Кубок открытия — гонка 3»; остальные — собранные значения).
   `summary` оставь коротким или пустым.
5. Добавь запись в `races` индекса (Python-сниппет ниже, см. «Обновление индекса»).
6. **Фото акватории.** Если пользователь дал картинку акватории с треком/дистанцией —
   скопируй её в `files/area.png` и вставь в раздел `## Дистанция`:
   `![[files/area.png]]`. Это важно — по фото видна береговая зависимость (заливы,
   острова, веер ветра у знаков). Схему дистанции (если есть) — `files/course.png`.
7. Предложи запустить `/sail-weather forecast` для прогноза. По желанию —
   `/sail-recall` для похожих гонок.

---

## Режим: import

1. Получи путь к `.gpx` и определи целевую гонку (slug). Если гонка не указана —
   спроси или предложи создать (`new`).
2. **Дедуп по sha256:**

```bash
HASH="$(shasum -a 256 "<input.gpx>" | awk '{print $1}')"
python3 -c "
import json,sys,os
idx_path=os.path.join('$SAILING_DIR','.race-index.json')
idx=json.load(open(idx_path)) if os.path.exists(idx_path) else {'races':{},'tracks':{}}
slug=idx.get('tracks',{}).get('$HASH')
print('DUP:'+slug if slug else 'NEW')
"
```

Если `DUP:<slug>` → **ABORT**, сообщи «Этот трек уже импортирован в гонку <slug>».

3. Скопируй трек:

```bash
cp "<input.gpx>" "$SAILING_TRACKS_DIR/<slug>/files/track.gpx"
```

4. Базовая статистика:

```bash
python3 -c "
import sys,json; sys.path.insert(0,'$SAILING_REPO/lib')
from sailtrack.gpx import parse_gpx, basic_stats
p=parse_gpx('$SAILING_TRACKS_DIR/<slug>/files/track.gpx')
print(json.dumps(basic_stats(p)))
"
```

5. Через **Edit tool** заполни в заметке блок `track:`:
   `file: files/track.gpx`, `source: waterspeed` (или `gpx`), `sha256: <HASH>`,
   и `duration_min/distance_nm/max_speed_kt/avg_speed_kt` из JSON. Установи `status: sailed`.
6. Добавь `tracks["<HASH>"] = "<slug>"` в индекс (см. ниже).
7. Предложи запустить `/sail-analyze` для полного разбора и `/sail-weather actual`.

---

## Режим: update

- Допиши `result:` (`position`, `fleet_size`, `status`: finished|dnf|dns|dsq|ocs) —
  через **Edit tool**.
- Смени `status:` (`sailed` → `analyzed` делает `/sail-analyze`; вручную можно
  `planned`→`sailed`).
- Мысли пользователя дописывай в `## Мысли и инсайты`, **не перезаписывая** уже
  написанное. Авто-секции не трогай.
- Обнови `updated:`.

---

## Обновление индекса (Python)

```bash
python3 - <<PY
import json, os
idx_path = os.path.join("$SAILING_DIR", ".race-index.json")
idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
idx.setdefault("races", {}); idx.setdefault("tracks", {})

# --- new: добавить/обновить запись гонки ---
idx["races"]["<slug>"] = {
    "date": "<date>", "venue": "<venue>", "boat": "<boat>", "class": "<class>",
    "course_type": "<course_type>", "distance_nm": <distance_nm>,
    "wind_dir_card": None, "wind_bucket": None, "path": "tracks/<slug>",
}
# --- import: привязать sha256 → slug ---
# idx["tracks"]["<HASH>"] = "<slug>"

json.dump(idx, open(idx_path, "w"), ensure_ascii=False, indent=2)
print("index updated")
PY
```

(`/sail-weather` позже проставит `wind_dir_card`/`wind_bucket` в `races[slug]`.)

## Отчёт

Кратко: режим, slug гонки, путь заметки; для import — статистика трека (kt/nm) и
предложение следующего шага (`/sail-analyze`, `/sail-weather`).

## Обработка ошибок

| Ошибка | Решение |
|--------|---------|
| `.gpx` не найден | Сообщить, попросить путь |
| Дубль sha256 | ABORT, назвать гонку, куда трек уже импортирован |
| Нет полей для new | `AskUserQuestion` |
| Трек без точек/времени | Импортировать файл, в `track:` оставить нули, отметить в отчёте |
| Гонка для import не найдена | Предложить `new` |
