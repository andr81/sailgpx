# Sailing System — дизайн-спецификация

**Дата:** 2026-06-14
**Статус:** утверждён к реализации
**Владелец:** Andrei (andrei.vitkouski@clawbuster.com)

Набор скиллов и скриптов для подготовки к парусным гонкам и их разбора: ведение
заметок по гонке, прогноз и фактическая погода, импорт GPS-треков, анализ трека как
тренер-тактик, поиск похожих гонок и извлечение инсайтов.

**Разделение код / данные:**

- **Код** (скиллы, tooling, скрипты, шаблоны, тесты, docs) — в git-репозитории
  `/Users/vita/projects/sailgpx` (`origin git@github.com:andr81/sailgpx.git`). Это
  единственный source of truth для скиллов. У репы свой `tooling/install.sh`, который
  симлинкует `skills/sail-*` в `~/.claude/skills/`.
- **Данные** (заметки гонок, треки, справочники, индексы) — в автономной папке
  `sailing/` Obsidian-хранилища; система не пересекается с остальным личным vault'ом.
- Obsidian-`tooling/` (с `life-*` скиллами) **не трогаем** — он отдельный.

---

## 1. Контекст и принципы

- Репозиторий кода: `/Users/vita/projects/sailgpx` (далее `REPO`).
- Хранилище Obsidian: `$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/`
  (далее `VAULT`).
- Папка данных системы: `VAULT/sailing/` (top-level, **автономная**). Существующая
  `Hobbies/Sailing/` (type: note) не трогается.
- Корень папок гонок берётся из `REPO/.env` → `SAILING_TRACKS_DIR`
  (по умолчанию `VAULT/sailing/tracks`). Скрипты НЕ хардкодят путь — резолвят через
  `REPO/tooling/sailenv.sh`.
- Конвенции наследуются из vault CLAUDE.md и `life-*` скиллов:
  - frontmatter-driven; имена полей — **латиница**, значения — **русский**;
  - дедупликация вложений по **sha256** в JSON-индексе;
  - паттерн look-back / «похожие записи» (как динамика анализов) → основа поиска
    похожих гонок;
  - скиллы живут в `REPO/skills/<name>/SKILL.md`, симлинкуются в `~/.claude/skills/`
    через `REPO/tooling/install.sh` (глоб `skills/sail-*`).
- **Единицы:** дистанции — морские мили (**nm**), скорости (лодки и ветра) — узлы
  (**kt**). Углы/направления — градусы (0°=N, по часовой). Координаты — WGS84.
- Принцип YAGNI: схемы богатые, но любое поле опционально; пустое поле остаётся
  пустым, данные не выдумываются.

---

## 2. Структура папок

### 2.1. Репозиторий кода (`REPO = /Users/vita/projects/sailgpx`)

```
sailgpx/
├── CLAUDE.md                      # правила проекта (Claude Code), корень репы
├── README.md                      # скиллы, использование, порядок обработки
├── .env                           # SAILING_TRACKS_DIR (в .gitignore)
├── .env.example                   # коммитится — образец
├── tooling/
│   ├── install.sh                 # симлинкует skills/sail-* → ~/.claude/skills/
│   └── sailenv.sh                 # резолвит VAULT + SAILING_TRACKS_DIR из .env
├── skills/
│   ├── sail-race/SKILL.md
│   ├── sail-weather/SKILL.md
│   ├── sail-analyze/              # SKILL.md + python-пакет анализатора
│   └── sail-recall/SKILL.md
├── templates/                     # шаблоны заметок, копируются скиллами в VAULT
│   ├── sail-race.md
│   ├── sail-boat.md
│   └── sail-venue.md
├── tests/
└── docs/superpowers/{specs,plans}/
```

### 2.2. Данные в хранилище (`VAULT/sailing/`)

```
sailing/
├── CLAUDE.md                      # лёгкие правила работы с ДАННЫМИ в vault
├── _index.md                      # хаб: dataview-таблицы всех гонок
├── boats/
│   ├── _index.md                  # таблица лодок
│   ├── laser.md                   # type: sail-boat
│   └── open-800-<slug>.md
├── venues/
│   └── minskoe-more.md            # type: sail-venue: координаты, ориентиры, ветра
├── .race-index.json               # дедуп GPX по sha256 + кэш заголовков для поиска
├── .weather-accuracy.json         # накопительная статистика ошибок по источникам прогноза
└── tracks/                        # = $SAILING_TRACKS_DIR
    └── 2026-06-14-kubok-otkrytia-r3/      # папка гонки (slug — латиница)
        ├── 2026-06-14-kubok-otkrytia-r3.md
        └── files/
            ├── track.gpx                   # исходный трек
            ├── track.weather.json          # кэш ответов погоды
            ├── course.png                  # схема дистанции (прикладывает пользователь)
            ├── track-render.png            # авто-рендер трека (анализатор)
            └── forecast.png                # опц. скрин Windguru
```

- Slug папки гонки — **латиница** (надёжность путей в GPX/скриптах);
  `title`/`summary` — русский. Шаблон slug: `YYYY-MM-DD-<event-slug>[-r<N>]`.
- Внутри папки гонки только `.md` в корне, все вложения — в `files/`
  (как в Health-домене). Ссылки в заметке всегда с префиксом `files/`.

---

## 3. Frontmatter-схемы

### 3.1. Гонка — `type: sail-race`

```yaml
---
title: "Кубок открытия — гонка 3"
type: sail-race
date: 2026-06-14
venue: minskoe-more            # → venues/<slug>.md
boat: open-800-bohun           # → boats/<slug>.md
class: "Open 800"              # денормализовано для поиска
event: "Кубок открытия 2026"
race_no: 3
discipline: fleet              # fleet | pursuit | distance | training | match
course_type: windward-leeward  # windward-leeward | triangle | coastal | distance
distance_nm: 5.0
laps: 2
status: planned                # planned | sailed | analyzed

weather_forecast:              # КАНОНИЧЕСКИЙ прогноз (ансамблевое среднее моделей) — ключи поиска
  method: ensemble-mean        # ensemble-mean | <конкретный источник, когда выберем точнейший>
  wind_dir_deg: 270
  wind_dir_card: W             # ключ поиска похожих
  wind_speed_kt: 11
  wind_gust_kt: 16
  wind_bucket: "10-15"         # ключ поиска: 0-5,5-10,10-15,15-20,20+
  temp_c: 18
  pressure_hpa: 1012
  clouds_pct: 40
  precip_mm: 0
  fetched: 2026-06-13

weather_forecast_sources:      # по записи на источник/модель (для сравнения точности)
  - source: open-meteo:ecmwf_ifs025
    issued: 2026-06-12T18:00   # когда выпущен прогноз
    lead_h: 17                 # за сколько часов до старта взят
    wind_dir_deg: 268
    wind_speed_kt: 10
    wind_gust_kt: 15
  - source: open-meteo:icon_eu
    issued: 2026-06-12T18:00
    lead_h: 17
    wind_dir_deg: 274
    wind_speed_kt: 12
    wind_gust_kt: 17
  # ... gfs_global, best_match

weather_actual:                # ЭТАЛОН после гонки
  reference: track-derived     # station | track-derived | era5  (по убыванию качества)
  source: open-meteo-archive   # фактический поставщик данных эталона
  wind_dir_deg: 280
  wind_dir_card: W
  wind_speed_kt: 12
  wind_gust_kt: 18
  wind_bucket: "10-15"
  shift_pattern: oscillating   # oscillating | persistent-left | persistent-right | building | dying
  temp_c: 19

result:
  position: 3
  fleet_size: 12
  status: finished             # finished | dnf | dns | dsq | ocs

track:                         # заполняет import + analyzer
  file: files/track.gpx
  source: waterspeed           # waterspeed | gpx
  sha256: "…"
  duration_min: 60
  distance_nm: 4.8
  max_speed_kt: 11.3
  avg_speed_kt: 5.6
  tacks: 14
  gybes: 6

tags: [кубок-открытия]
created: 2026-06-14
updated: 2026-06-14
summary: "Open 800, W 11 kt, 3-е из 12; теряли на огибании верхнего знака"
---
```

**Ключи поиска похожих гонок:** `venue`, `wind_dir_card`, `wind_bucket`,
`course_type`, `distance_nm` (± допуск), `class`.

### 3.2. Тело заметки гонки

```markdown
## Дистанция
схема (course.png) + описание, координаты знаков (если есть)

## Прогноз
авто-сводка погоды + тактический план

## Анализ трека
авто-таблица метрик + ![[files/track-render.png]]

## Результат
факт, протокол

## Мысли и инсайты   ← свободный формат пользователя (не перезаписывать)
```

> **Правило агента:** секцию «Мысли и инсайты» и любой пользовательский текст НЕ
> перезаписывать. Авто-секции (Прогноз/Анализ) обновляются между маркерами
> `<!-- sail:auto:start --> … <!-- sail:auto:end -->`.

### 3.3. Лодка — `type: sail-boat`

Frontmatter:

```yaml
---
title: "Open 800 «Богун»"
type: sail-boat
slug: open-800-bohun
class: "Open 800"
hull_length_m: 8.0
crew: 4
sail_area_m2: 0
rig: keelboat                  # dinghy | keelboat | catamaran
# параметры классификации курсов для анализатора (град, |TWA|):
upwind_twa: 42
downwind_twa: 145
polar: null                    # путь к polar-таблице или null → личный лучший
created:
updated:
tags: []
summary: ""
---
```

Тело: секции `## Заметки` и `## Выходы и гонки` с dataview-таблицей вида
`TABLE date, event, class, result.position FROM "sailing/tracks" WHERE boat = "<slug>" SORT date DESC`.

### 3.4. Акватория — `type: sail-venue`

```yaml
---
title: "Минское море"
type: sail-venue
slug: minskoe-more
lat: 53.97                      # для запросов погоды (по факту GPS-треков)
lon: 27.38
windguru_spots: [311332, 110353]
landmarks: ""
prevailing_winds: ""
created:
updated:
summary: ""
---
```

---

## 4. Источники погоды (исследование подтверждено живыми запросами)

### 4.1. PRIMARY — Open-Meteo (бесплатно, без ключа, JSON REST)

**Мульти-модельный прогноз из одного вызова** через `&models=` — даёт 3–4 независимых
источника бесплатно и без ключей; каждый пишется в `weather_forecast_sources[]`,
их среднее — в канонический `weather_forecast`.

- **Forecast** (до гонки), мульти-модель:
  ```
  https://api.open-meteo.com/v1/forecast?latitude=53.97&longitude=27.38
    &models=ecmwf_ifs025,icon_eu,icon_d2,gfs_global,best_match
    &hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m,surface_pressure,precipitation,cloud_cover
    &wind_speed_unit=kn&timezone=Europe%2FMinsk
  ```
  (При `&models=` ответ содержит по колонке на модель, напр. `wind_speed_10m_ecmwf_ifs025`.)
- **Archive / ERA5** (разбор, гонки старше ~5 дней):
  ```
  https://archive-api.open-meteo.com/v1/archive?latitude=53.97&longitude=27.38
    &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    &hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&wind_speed_unit=kn&timezone=Europe%2FMinsk
  ```
- **Historical-forecast** (совсем свежие гонки, пока ERA5 не подъехал):
  `https://historical-forecast-api.open-meteo.com/v1/forecast` (те же параметры).
- Лимиты free: 600/мин, 10 000/день. Без SLA. Ответы кэшируем в `files/track.weather.json`.

### 4.2. SECONDARY / кросс-чек

- **Windguru-споты** акватории: `windguru.cz/311332` (Минское море),
  `windguru.cz/110353` (ExtremeClub / клубный). Дают мульти-модельный разброс и —
  если зарегистрирована физическая станция — реально измеренный ветер на воде
  (Windguru Station JSON API). Программного forecast-API нет → ссылки в заметку +
  опц. ручной скрин `forecast.png`.
- **Visual Crossing** — программный backup (free 1000 записей/день, forecast+history
  в одном API). Подключается только если Open-Meteo недоступен.

### 4.3. Оговорка

Все модельные источники дают ветер на 10 м на грубой сетке и НЕ ловят локальные
термические/береговые сдвиги озера. Поэтому фактический ветер с трека (оценка TWD из
GPS) ценнее модели — используется в анализаторе наряду с `weather_actual`.

### 4.4. Отслеживание точности источников

Эталон (`weather_actual.reference`) берётся по убыванию качества: **station**
(физическая метеостанция Windguru-спота, измеренный ветер) → **track-derived**
(TWD/TWS из GPS-трека, считает анализатор — независимый «полевой» эталон по точке) →
**era5** (Open-Meteo archive, fallback). Иначе сравнивали бы модель с моделью.

При заполнении `weather_actual` для каждого источника из `weather_forecast_sources[]`
считаем ошибку и пополняем `sailing/.weather-accuracy.json`:

```json
{
  "open-meteo:ecmwf_ifs025": {
    "n": 12,
    "wind_speed_mae_kt": 1.8,        // средняя абсолютная ошибка скорости
    "wind_dir_mae_deg": 14.2,        // циклическая ошибка направления
    "gust_mae_kt": 2.6,
    "bias_speed_kt": -0.4,           // систематическое смещение (модель занижает)
    "by_lead": { "6": {...}, "24": {...} }   // разбивка по lead_h (опц.)
  },
  "open-meteo:icon_eu": { ... }
}
```

`/sail-weather` выводит текущий рейтинг источников. Когда наберётся достаточно
замеров, канонический `weather_forecast` можно переключить с `ensemble-mean` на
точнейший источник, а неточные — отключить. Формат лога **source-agnostic**: добавить
нового провайдера (Visual Crossing, Yandex, OWM) позже = просто новый ключ, без
переделки.

---

## 5. Формат трека WaterSpeed (зафиксирован по реальным файлам)

- GPX 1.1, `creator="fabulator:gpx-builder"`, namespace
  `gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v2"`.
- Точка: `<trkpt lat lon>` (lat/lon — **атрибуты**) + `<time>` (ISO-8601 UTC, мс) +
  `<extensions><gpxtpx:TrackPointExtension><gpxtpx:speed>` (**м/с**) и
  `<gpxtpx:course>` (град).
- **Семплирование ~1 Гц** (медиана dt = 1.0 с), но встречаются пропуски (13–47 с) →
  ресемплинг и обработка дыр обязательны.
- Скорость в kt = `speed_m_s × 1.94384`. Дистанции считаем в nm.
- Нет программного API → импорт только файловый (экспорт GPX из приложения/веба).

### Устойчивый GPX-парсер (общий для любых устройств)

1. lat/lon — из атрибутов; `<time>` — парсить, толерантно к отсутствию.
2. Скорость по приоритету: `gpxtpx:speed` (v2, м/с) → `<speed>` (GPX 1.0, м/с) →
   `gpxdata:speed` → **вычислить** из haversine(p−1,p)/Δt.
3. Курс: `gpxtpx:course` → `<course>` → вычислить из последовательных точек.
4. Матчить расширения по namespace-URI / localname, не по префиксу.
5. Не предполагать наличие HDOP/accuracy.

---

## 6. Анализатор трека — методика (исследование)

Стек: **`gpxpy + pandas + numpy + scipy + haversine`** (+ опц. `pyproj` для проекции
в метры, `movingpandas` для траекторных примитивов). Все углы — циклическая
арифметика (`atan2(sinΔ, cosΔ)`); ресемплинг ДО оконных статистик; COG/повороты
гейтить по минимальной скорости.

**Пайплайн:** parse → clean (выбросы/дубли/гэпы) → resample(1 Гц) → project(метры) →
derive COG/SOG (rolling-median(3) → Savgol; SOG из `speed` иначе вычисление) →
TWD (из `weather_actual` ИЛИ оценка из трека: биссектриса галсов + гистограмма COG,
**скользящее окно** для шифтов) → TWA + классификация курса (пороги из `boats/`) →
detect tacks/gybes (флип галса + пересечение оси ветра, debounce ≥5 с; ROT-пики для
границ) → mark roundings (устойчивый большой поворот; если даны координаты знаков —
по минимуму дистанции) → segment legs → aggregate.

**Метрики (kt/nm), приоритет «как у тренера»:**

- %-of-polar (Open 800 — табличный polar; прочие — личный лучший polar из накопленных
  треков), per leg.
- VMG вверх/вниз vs target; VMC к знаку, если даны координаты.
- Повороты: число tacks/gybes, углы лавировки/гибовки, **цена поворота** — потеря
  скорости (kt), время восстановления до 95% target, потеря в длинах корпуса
  (интеграл дефицита VMG / hull_length).
- % времени на port/starboard; лишняя дистанция % (actual vs `rhumb/cos β`),
  разложение: оверстенд / лишние повороты / широкие углы.
- Groove: σ(TWA) на устоявшихся лавировочных участках; CV скорости.
- Огибания знаков: вход/выход (kt), радиус, время, потеря/восстановление.

**Вывод:** JSON-метрики → таблица в секцию «Анализ трека» (между auto-маркерами) +
`files/track-render.png` (matplotlib: трек, раскраска по курсу/скорости) + опц.
таймлайны скорости/VMG. После анализа `status: analyzed`, заполняется `track:`.

**Калибровка:** пороги (бины курсов, ROT-триггер, debounce, % восстановления) —
параметры на класс лодки. Детектор поворотов проверить на 1–2 размеченных треках до
доверия агрегатам.

---

## 7. Скиллы

Все — в `REPO/skills/sail-*/SKILL.md`, симлинк в `~/.claude/skills/` через
`REPO/tooling/install.sh` (глоб `skills/sail-*`). Имена slug'ов/папок — латиница;
общение и контент — русский. Пути к данным — через `source REPO/tooling/sailenv.sh`.

### 7.1. `/sail-race` — ведение гонки

Под-режимы (определяются по аргументам/диалогу):

- **new** — создать папку гонки + заметку из шаблона; запросить недостающее
  (event, boat, venue, course_type, distance_nm, date) через `AskUserQuestion`;
  если до гонки — сразу позвать погоду (forecast) и предложить приложить `course.png`.
- **update** — дописать результат (`result:`), сменить `status`, добавить мысли
  (не перезаписывая пользовательский текст).
- **import** — принять путь к `.gpx`: sha256 дедуп в `.race-index.json`, копия в
  `files/track.gpx`, базовая сводка в `track:`; предложить запустить `/sail-analyze`.

Обновляет `.race-index.json` (кэш заголовков для поиска).

### 7.2. `/sail-weather` — погода в заголовки

- `forecast` — Open-Meteo **мульти-модель** (`&models=ecmwf_ifs025,icon_eu,icon_d2,gfs_global,best_match`)
  на окно времени гонки → каждая модель в `weather_forecast_sources[]` (с `issued`,
  `lead_h`), их среднее в канонический `weather_forecast` + сводка в тело + ссылки
  Windguru. Кэш сырых ответов в `track.weather.json`.
- `actual` — эталон по убыванию качества (station → track-derived → era5), фиксируется
  в `weather_actual.reference`; затем для каждого источника считается ошибка и
  пополняется `sailing/.weather-accuracy.json`; строка «прогноз vs факт».
- `ranking` — вывести текущий рейтинг точности источников из `.weather-accuracy.json`.
- Заполняет `wind_dir_card` и `wind_bucket` (узловые бакеты) — ключи поиска.

### 7.3. `/sail-analyze` — анализатор (главный)

- Python-пакет в каталоге скилла (`analyze.py` + lib). Вход — `files/track.gpx`
  (+ опц. координаты знаков, + `weather_actual` как TWD). Реализует пайплайн §6.
- Выход — метрики в заметку + `track-render.png` + обновление `track:` и
  `status: analyzed`.

### 7.4. `/sail-recall` — похожие гонки + инсайты

- Запрос по `venue` + `wind_dir_card` + `wind_bucket` + `course_type` +
  `distance_nm` (± допуск) + `class`. Источник — `.race-index.json`, верификация по
  файлам.
- Агрегирует «Мысли и инсайты», результаты и метрики похожих гонок → советы на новую
  гонку. Может вызываться из `/sail-race new` автоматически.

---

## 8. Порядок реализации

| # | Артефакт | Содержит |
|---|----------|----------|
| 0 | Scaffold + docs-каркас | `REPO/tooling/sailenv.sh` + `install.sh` (глоб `skills/sail-*`), `REPO/.env(.example)`, `REPO/templates/*`, `REPO/CLAUDE.md`, заготовка `REPO/README.md`; данные в vault: `sailing/CLAUDE.md`, `_index.md`, `boats/_index.md`, `venues/minskoe-more.md`, пример лодки, JSON-индексы |
| 1 | `/sail-race` | new/update/import, frontmatter-схема, GPX-парсер, `.race-index.json` |
| 2 | `/sail-weather` | Open-Meteo мульти-модель forecast + archive, лог точности, Windguru-ссылки, кэш |
| 3 | `/sail-analyze` | Python-пайплайн, метрики, рендер |
| 4 | `/sail-recall` | поиск похожих + инсайты |
| 5 | Финализация docs | дописать `REPO/README.md` под все реализованные скиллы; добавить строки `sail-*` в таблицу скиллов корневого `CLAUDE.md` хранилища |

Каждый пункт — отдельный цикл план→реализация. Сначала спроектировано всё (этот
документ), далее сборка строго по порядку 0→1→2→3→4→5. `README.md` ведём инкрементально
(каждый скилл при готовности дописывает свой раздел), финальный проход — на шаге 5.
Код коммитим в `REPO`; данные в vault под git не попадают.

---

## 9. Открытые вопросы (решаются по ходу, не блокируют старт)

- Polar-таблица для Open 800 — найти/задать; до этого работает «личный лучший polar».
- Точные координаты знаков дистанции — опциональный ввод; без них огибания/лэйлайны
  считаются эвристически (по форме трека).
- Наличие физической метеостанции на клубном Windguru-споте (110353) — проверить;
  если есть, добавить как источник измеренного ветра.
- Точный CSV/Excel-формат экспорта WaterSpeed — не подтверждён; вход v1 = GPX.

---

## 10. Приложение: обоснование (саммари ресёрча)

- **Погода:** Open-Meteo — единственный бесплатный key-less источник с почасовым
  ветром/порывами и обоими эндпоинтами (forecast + ERA5 archive), покрывает точку
  53.97/27.38 (проверено). Windguru — парусный кросс-чек/измеренный ветер. Visual
  Crossing — программный backup. Stormglass/Windy-API/PredictWind — дорого или
  непригодно для пресноводного водохранилища.
- **WaterSpeed:** GPX с допплеровской скоростью в `gpxtpx:speed` (м/с); API нет →
  файловый импорт; GPX — универсальный вход и для других устройств.
- **Анализ трека:** установленное ядро — навигационная математика (COG/bearing,
  haversine), wind-relative метрики (TWA, point-of-sail, VMG/VMC), %-of-polar
  (Sailmon/SAP/Vakaros/RaceQs). Детект поворотов, цена поворота, огибания,
  сегментация ног, route-efficiency, TWD-из-трека — практические эвристики,
  калибруются на размеченных треках. На водохранилище критичен time-varying TWD →
  инсайт «поворот на заходах».

---

## 11. Документация

### 11.1. `REPO/README.md` (человекочитаемо, для пользователя)

Разделы:

1. **Что это** — 2–3 строки о системе + разделение код(repo)/данные(vault).
2. **Установка** — скопировать `.env.example` → `.env` (`SAILING_TRACKS_DIR`),
   `bash tooling/install.sh`, зависимости Python анализатора
   (`pip install gpxpy pandas numpy scipy haversine`).
3. **Скиллы** — таблица: `/sail-race`, `/sail-weather`, `/sail-analyze`,
   `/sail-recall` — назначение, режимы, пример вызова.
4. **Типовой порядок загрузки и обработки** (жизненный цикл гонки):
   ```
   ДО ГОНКИ
     /sail-race new            → создать папку + заметку, выбрать boat/venue/дистанцию
     (приложить course.png)    → схема дистанции
     /sail-weather forecast    → мульти-модельный прогноз в заголовки + план
   ПОСЛЕ ГОНКИ
     /sail-race import <gpx>   → импорт трека (дедуп, копия, базовая сводка)
     /sail-analyze             → метрики тренера-тактика + рендер трека
     /sail-weather actual      → фактическая погода (эталон) + лог точности источников
     /sail-race update         → результат + свои мысли в «Мысли и инсайты»
     /sail-recall              → похожие гонки + советы (можно и ДО гонки)
   ```
5. **Структура папок и формат заметки** — кратко, со ссылкой на эту спецификацию.
6. **Единицы и конвенции** — nm/kt/градусы; что НЕ перезаписывается агентом.

### 11.2. `REPO/CLAUDE.md` (основной, для агента, по гайдам Claude Code)

Принципы: коротко, императивно, высокий сигнал. Правила работы над **кодом** проекта:

- **Назначение и раскладка** — код в `REPO`, данные в `VAULT/sailing/`; Obsidian-`tooling`
  (`life-*`) не трогать.
- **Пути** — путь треков из `REPO/.env` `SAILING_TRACKS_DIR`, резолвить через
  `source tooling/sailenv.sh`, не хардкодить.
- **Скиллы** — в `skills/sail-*/SKILL.md`; переустановка симлинков `bash tooling/install.sh`.
- **Команды** — тесты (`bash tests/*.sh`), анализатор (зависимости
  `gpxpy pandas numpy scipy haversine`).
- **Единицы** — nm, kt, градусы (0°=N).
- **Скиллы и ответственность** — одна строка на `/sail-*`, ссылки на README и эту спеку.
- Не раздувать: детали — в README/спеку, в CLAUDE.md держать правила.

### 11.3. `VAULT/sailing/CLAUDE.md` (лёгкий, правила работы с данными)

Scoped к `sailing/` в vault; срабатывает при редактировании данных. Содержит:

- **Границы** — автономная подсистема; не трогать остальной vault и `Hobbies/Sailing/`;
  никаких cross-links наружу.
- **Пути/вложения** — вложения только в `files/`, ссылки с префиксом `files/`.
- **Единицы** — nm, kt, градусы (0°=N).
- **Frontmatter** — латиница в именах полей, русский в значениях; slug папок гонок —
  латиница; ключи поиска `venue/wind_dir_card/wind_bucket/course_type/distance_nm/class`.
- **Неприкосновенное** — секцию «Мысли и инсайты» и пользовательский текст не
  перезаписывать; авто-секции только между `<!-- sail:auto:start -->` … `<!-- sail:auto:end -->`.
- **Дедуп** — GPX по sha256 в `.race-index.json`; данные не выдумывать, пустое — пустым.
- Указатель на код/скиллы: репозиторий `REPO` (`andr81/sailgpx`).
