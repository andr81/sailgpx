# Sailing System — Фаза 1: `/sail-race` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Скилл `/sail-race` (new / update / import) для ведения заметки гонки, плюс stdlib-парсер GPX и базовая статистика трека, переиспользуемые анализатором.

**Architecture:** Логика скилла — в `skills/sail-race/SKILL.md` (инструкции + bash/python-сниппеты, как `life-*`). Парсинг GPX и базовая статистика — в репозиторной библиотеке `lib/sailtrack/gpx.py` (только stdlib, без внешних зависимостей), вызывается из скилла по `$SAILING_REPO`. Дедуп GPX по sha256 в `VAULT/sailing/.race-index.json`.

**Tech Stack:** Python 3 stdlib (`xml.etree`, `datetime`, `math`, `hashlib`, `json`), Bash. Тесты — `python3` unittest-free assert-скрипты (как в фазе 0 — простые), запуск `python3 tests/test_gpx.py`.

**Соглашения:** `REPO=/Users/vita/projects/sailgpx`, `VAULT=/Users/vita/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`. Скорости — kt, дистанции — nm.

---

### Task 1: Библиотека `lib/sailtrack/gpx.py` + тесты

Парсер GPX (lat/lon из атрибутов; time; скорость по приоритету extension-`speed`(м/с)→вычисление; курс) и `basic_stats` (duration_min, distance_nm, max_speed_kt, avg_speed_kt).

**Files:**
- Create: `REPO/lib/sailtrack/__init__.py`
- Create: `REPO/lib/sailtrack/gpx.py`
- Create: `REPO/tests/fixtures/mini.gpx`
- Test: `REPO/tests/test_gpx.py`

- [ ] **Step 1: Фикстура `tests/fixtures/mini.gpx`**

Create `/Users/vita/projects/sailgpx/tests/fixtures/mini.gpx` — 3 точки, со speed-extension (м/с), 1 Гц:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v2">
  <trk><trkseg>
    <trkpt lat="53.9684" lon="27.3868"><time>2026-06-13T08:00:00Z</time>
      <extensions><gpxtpx:TrackPointExtension><gpxtpx:speed>2.5722</gpxtpx:speed><gpxtpx:course>10</gpxtpx:course></gpxtpx:TrackPointExtension></extensions></trkpt>
    <trkpt lat="53.9686" lon="27.3869"><time>2026-06-13T08:00:01Z</time>
      <extensions><gpxtpx:TrackPointExtension><gpxtpx:speed>5.1444</gpxtpx:speed></gpxtpx:TrackPointExtension></extensions></trkpt>
    <trkpt lat="53.9688" lon="27.3870"><time>2026-06-13T08:00:02Z</time>
      <extensions><gpxtpx:TrackPointExtension><gpxtpx:speed>0</gpxtpx:speed></gpxtpx:TrackPointExtension></extensions></trkpt>
  </trkseg></trk>
</gpx>
```

(speed 2.5722 м/с = 5.0 kt; 5.1444 м/с = 10.0 kt.)

Также create `/Users/vita/projects/sailgpx/tests/fixtures/nospeed.gpx` — те же 3 точки без extensions (для проверки вычисления скорости из координат):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="53.9684" lon="27.3868"><time>2026-06-13T08:00:00Z</time></trkpt>
    <trkpt lat="53.9686" lon="27.3869"><time>2026-06-13T08:00:01Z</time></trkpt>
    <trkpt lat="53.9688" lon="27.3870"><time>2026-06-13T08:00:02Z</time></trkpt>
  </trkseg></trk>
</gpx>
```

- [ ] **Step 2: Падающий тест `tests/test_gpx.py`**

Create `/Users/vita/projects/sailgpx/tests/test_gpx.py`:

```python
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from sailtrack.gpx import parse_gpx, basic_stats

FIX = os.path.join(HERE, "fixtures")
fail = 0

def check(cond, msg):
    global fail
    if not cond:
        print("FAIL:", msg); fail = 1

# parse with speed extension
pts = parse_gpx(os.path.join(FIX, "mini.gpx"))
check(len(pts) == 3, f"expected 3 points, got {len(pts)}")
check(abs(pts[0].speed_kt - 5.0) < 0.05, f"pt0 speed_kt ~5.0, got {pts[0].speed_kt}")
check(abs(pts[1].speed_kt - 10.0) < 0.05, f"pt1 speed_kt ~10.0, got {pts[1].speed_kt}")
check(pts[0].course == 10.0, f"pt0 course 10, got {pts[0].course}")
check(pts[0].time is not None, "pt0 time parsed")

st = basic_stats(pts)
check(abs(st["duration_min"] - (2/60)) < 0.01, f"duration_min, got {st['duration_min']}")
check(st["max_speed_kt"] == 10.0, f"max_speed_kt 10.0, got {st['max_speed_kt']}")
check(st["distance_nm"] > 0, f"distance_nm > 0, got {st['distance_nm']}")

# parse without speed → computed from coords, still > 0
pts2 = parse_gpx(os.path.join(FIX, "nospeed.gpx"))
check(all(p.speed_kt is None for p in pts2), "nospeed: extension speed absent")
st2 = basic_stats(pts2)
check(st2["max_speed_kt"] > 0, f"nospeed computed max > 0, got {st2['max_speed_kt']}")

print("PASS test_gpx" if fail == 0 else "TESTS FAILED")
sys.exit(fail)
```

- [ ] **Step 3: Запустить — упадёт**

Run: `python3 /Users/vita/projects/sailgpx/tests/test_gpx.py`
Expected: FAIL (ModuleNotFoundError: sailtrack).

- [ ] **Step 4: Реализация**

Create `/Users/vita/projects/sailgpx/lib/sailtrack/__init__.py`:

```python
"""sailtrack — парсинг и анализ парусных GPS-треков."""
```

Create `/Users/vita/projects/sailgpx/lib/sailtrack/gpx.py`:

```python
"""Устойчивый парсер GPX и базовая статистика трека (kt/nm). Только stdlib."""
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from math import radians, sin, cos, asin, sqrt
from typing import Optional, List

MS_TO_KT = 1.94384       # м/с → узлы
M_TO_NM = 1.0 / 1852.0   # метры → морские мили
_EARTH_M = 6371000.0


@dataclass
class TrackPoint:
    time: Optional[datetime]
    lat: float
    lon: float
    speed_kt: Optional[float]   # из extension (м/с→kt), если есть
    course: Optional[float]     # градусы, если есть


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_time(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_gpx(path: str) -> List[TrackPoint]:
    root = ET.parse(path).getroot()
    points: List[TrackPoint] = []
    for el in root.iter():
        if _localname(el.tag) != "trkpt":
            continue
        lat = float(el.get("lat"))
        lon = float(el.get("lon"))
        t = speed_ms = course = None
        for child in el.iter():
            ln = _localname(child.tag)
            txt = (child.text or "").strip()
            if not txt:
                continue
            if ln == "time" and t is None:
                t = _parse_time(txt)
            elif ln == "speed" and speed_ms is None:   # <speed> или gpxtpx:speed / gpxdata:speed
                try:
                    speed_ms = float(txt)
                except ValueError:
                    pass
            elif ln == "course" and course is None:
                try:
                    course = float(txt)
                except ValueError:
                    pass
        speed_kt = round(speed_ms * MS_TO_KT, 2) if speed_ms is not None else None
        points.append(TrackPoint(t, lat, lon, speed_kt, course))
    return points


def haversine_nm(a: TrackPoint, b: TrackPoint) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_M * asin(sqrt(h)) * M_TO_NM


def basic_stats(points: List[TrackPoint]) -> dict:
    zero = {"duration_min": 0.0, "distance_nm": 0.0, "max_speed_kt": 0.0, "avg_speed_kt": 0.0}
    if len(points) < 2:
        return zero
    dist_nm = sum(haversine_nm(points[i], points[i + 1]) for i in range(len(points) - 1))
    times = [p.time for p in points if p.time is not None]
    dur_min = (times[-1] - times[0]).total_seconds() / 60.0 if len(times) >= 2 else 0.0

    speeds = [p.speed_kt for p in points if p.speed_kt is not None]
    if not speeds:  # вычислить из координат/времени
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            if a.time and b.time:
                dt_h = (b.time - a.time).total_seconds() / 3600.0
                if dt_h > 0:
                    speeds.append(haversine_nm(a, b) / dt_h)
    max_kt = max(speeds) if speeds else 0.0
    avg_kt = dist_nm / (dur_min / 60.0) if dur_min > 0 else 0.0
    return {
        "duration_min": round(dur_min, 1),
        "distance_nm": round(dist_nm, 2),
        "max_speed_kt": round(max_kt, 1),
        "avg_speed_kt": round(avg_kt, 1),
    }
```

- [ ] **Step 5: Запустить — пройдёт**

Run: `python3 /Users/vita/projects/sailgpx/tests/test_gpx.py`
Expected: `PASS test_gpx`

- [ ] **Step 6: Smoke на реальном треке (если есть)**

Run:
```bash
F="/Users/vita/Downloads/waterspeed-0586dc65-6bee-4d1b-9e3c-678ce49732ab.gpx"
[ -f "$F" ] && python3 -c "import sys; sys.path.insert(0,'/Users/vita/projects/sailgpx/lib'); from sailtrack.gpx import parse_gpx, basic_stats; p=parse_gpx('$F'); print(len(p),'pts', basic_stats(p))" || echo "real track absent — skip"
```
Expected: ~3244 точек и правдоподобная статистика (max ~11 kt), либо skip.

- [ ] **Step 7: Commit**

```bash
cd /Users/vita/projects/sailgpx
git add lib/sailtrack/ tests/test_gpx.py tests/fixtures/
git commit -m "feat(sailtrack): stdlib GPX parser and basic track stats with tests"
```

---

### Task 2: Скилл `skills/sail-race/SKILL.md`

Инструкция скилла. Контроллер-автор (как `life-*`). Режимы new/update/import.

**Files:**
- Create: `REPO/skills/sail-race/SKILL.md`

- [ ] **Step 1: Написать SKILL.md** (полный текст — в реализации фазы; следует структуре §7.1 спеки и шаблонам). Должен:
  - резолвить пути `source "$SAILING_REPO/tooling/sailenv.sh"` (REPO определять от расположения скилла через `realpath`/симлинк → `lib`, `templates`);
  - **new:** собрать поля (event, boat, venue, course_type, distance_nm, date, race_no, laps) через `AskUserQuestion`; slug `YYYY-MM-DD-<event-slug>[-r<N>]` (латиница); `mkdir -p $SAILING_TRACKS_DIR/<slug>/files`; скопировать `templates/sail-race.md`, заполнить `{{...}}`; добавить запись в `.race-index.json`; предложить `/sail-weather forecast`;
  - **import:** взять путь к `.gpx`; `shasum -a 256` → проверить дубль в `.race-index.json` (по любой гонке) → ABORT при дубле; копировать в `<race>/files/track.gpx`; вызвать `python3 $SAILING_REPO/lib/...` (`parse_gpx`+`basic_stats`) → записать `track:` (file, source, sha256, duration_min, distance_nm, max_speed_kt, avg_speed_kt) во frontmatter; `status: sailed`; предложить `/sail-analyze`;
  - **update:** дописать `result:`/`status:`/мысли, не перезаписывая пользовательский текст и auto-секции;
  - правила: единицы kt/nm; не выдумывать данные; обновлять `updated:`.

- [ ] **Step 2: Установить и проверить симлинк**

Run:
```bash
bash /Users/vita/projects/sailgpx/tooling/install.sh
test -L "$HOME/.claude/skills/sail-race" && echo "linked OK"
```
Expected: `+ sail-race linked …` и `linked OK`.

- [ ] **Step 3: Lint SKILL.md frontmatter (name/description есть)**

Run: `head -5 /Users/vita/projects/sailgpx/skills/sail-race/SKILL.md`
Expected: YAML-frontmatter с `name: sail-race` и `description:`.

- [ ] **Step 4: Commit**

```bash
cd /Users/vita/projects/sailgpx
git add skills/sail-race/SKILL.md
git commit -m "feat(sail-race): add /sail-race skill (new/update/import)"
```

---

### Task 3: Обновить README (статус sail-race) + финальная проверка

**Files:**
- Modify: `REPO/README.md`

- [ ] **Step 1:** В таблице скиллов README сменить статус `/sail-race` с `planned` на `ready`.

- [ ] **Step 2: Финальная проверка фазы 1**

Run:
```bash
cd /Users/vita/projects/sailgpx
python3 tests/test_gpx.py
bash tests/test_sailenv.sh; bash tests/test_install.sh
test -f skills/sail-race/SKILL.md && test -f lib/sailtrack/gpx.py && echo "phase1 files ok"
```
Expected: `PASS test_gpx`, `PASS test_sailenv`, `PASS test_install`, `phase1 files ok`.

- [ ] **Step 3: Commit + push**

```bash
cd /Users/vita/projects/sailgpx
git add README.md
git commit -m "docs: mark /sail-race ready in README"
git push
```

---

## Self-Review

**Spec coverage (§8 row 1, §7.1, §5):** GPX-парсер с приоритетом скорости и fallback (Task 1) ✓ · basic_stats kt/nm (Task 1) ✓ · скилл new/update/import + дедуп sha256 (Task 2) ✓ · README статус (Task 3) ✓.

**Placeholder scan:** Task 2 Step 1 описывает SKILL.md требованиями, а не готовым текстом — текст авторится контроллером в реализации (skill — инструкция, не код); это допустимо, т.к. поведение специфицировано пунктами и §7.1. Прочих TODO нет.

**Type consistency:** `parse_gpx`/`basic_stats`/`TrackPoint.speed_kt` совпадают между тестом (Task 1 Step 2) и реализацией (Step 4). Ключи `track:` (duration_min/distance_nm/max_speed_kt/avg_speed_kt) совпадают со спекой §3.1 и `basic_stats`.

**Deviation от спеки:** парсер на stdlib (`xml.etree`), а не `gpxpy` — убирает внешнюю зависимость для фазы 1; `gpxpy`/pandas остаются для анализатора (фаза 3), если понадобятся. Поведение (приоритет speed, fallback) соответствует §5.
