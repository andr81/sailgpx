---
name: sail-weather
description: Погода для парусной гонки в заголовки заметки — мульти-модельный прогноз Open-Meteo (forecast), фактическая погода-эталон после гонки (actual), рейтинг точности источников (ranking). Ветер в kt, направления в градусах; пишет weather_forecast/weather_forecast_sources/weather_actual во frontmatter и копит .weather-accuracy.json. Activates on /sail-weather, "прогноз погоды", "погода на гонку", "фактическая погода", "точность прогноза", "рейтинг источников погоды".
---

# Sail Weather

Погода в заголовки заметки гонки. Источник — Open-Meteo (бесплатно, без ключа,
мульти-модель). Лог точности накапливается между гонками.

## ⛔ Критические правила

- **НЕ ПРИДУМЫВАЙ** значения — только из API. Нет данных → поле пустое/`null`.
- Ветер — kt (запрос `wind_speed_unit=kn`), направления — градусы (0°=N).
- Не перезаписывай пользовательский текст и не-погодные auto-секции. Сводка прогноза —
  только между `<!-- sail:auto:start forecast -->` … `<!-- sail:auto:end forecast -->`.
- Обновляй `updated:`.

## Конфигурация

```bash
SAILING_REPO="/Users/vita/projects/sailgpx"
source "$SAILING_REPO/tooling/sailenv.sh"   # → SAILING_DIR, SAILING_TRACKS_DIR
```

- `lat/lon` и `windguru_spots` — из `$SAILING_DIR/venues/<venue>.md` (venue гонки во frontmatter).
- Лог точности: `$SAILING_DIR/.weather-accuracy.json` (нет файла → `{}`).
- Модели по умолчанию: `ecmwf_ifs025,icon_eu,icon_d2,gfs_global,best_match`.
- Окно времени гонки: дата гонки + локальные часы старта–финиша. Если неизвестны —
  спроси (`AskUserQuestion`) или возьми по умолчанию 11:00–14:00.

## Dispatch

`forecast` (до/после), `actual` (после гонки), `ranking`. По умолчанию — `forecast`.

---

## Режим: forecast

1. Возьми `venue` из заметки → `lat/lon` из venue-файла. Определи окно
   (`<date>T<HH:MM>` локально, start/end).
2. Запроси и распарси:

```bash
python3 - <<PY
import sys, json; sys.path.insert(0, "$SAILING_REPO/lib")
from sailweather.core import build_forecast_url, fetch_json, parse_openmeteo, build_forecast
models = ["ecmwf_ifs025","icon_eu","icon_d2","gfs_global","best_match"]
data = fetch_json(build_forecast_url(<lat>, <lon>, models))
parsed = parse_openmeteo(data, models)
canon, sources = build_forecast(parsed, "<startISO>", "<endISO>")
json.dump({"canonical":canon,"sources":sources}, open("$RACE_DIR/files/track.weather.json","w"), ensure_ascii=False, indent=2)
print(json.dumps({"canonical":canon,"sources":sources}, ensure_ascii=False))
PY
```

3. Через **Edit tool** запиши во frontmatter:
   - `weather_forecast:` — канонический (`method`, `wind_dir_deg`, `wind_dir_card`,
     `wind_speed_kt`, `wind_gust_kt`, `wind_bucket`) + `fetched: <today>`.
   - `weather_forecast_sources:` — список из `sources` (каждый: `source`, `wind_dir_deg`,
     `wind_speed_kt`, `wind_gust_kt`; добавь `issued`/`lead_h`, если знаешь время запуска
     прогноза и старта, иначе опусти).
4. Сводку в тело между `<!-- sail:auto:start forecast -->` … `end`: канонический ветер
   (kt, направление, порывы), разброс по моделям, температура/осадки/облачность из
   `data` при желании, и ссылки Windguru из `windguru_spots`
   (`https://www.windguru.cz/<id>`).
5. Проставь `races[<slug>].wind_dir_card` и `wind_bucket` в `.race-index.json`
   (по каноническому прогнозу) — для `/sail-recall`.

---

## Режим: actual

1. Выбери эталон (`reference`) по убыванию качества:
   - **track-derived** — если `/sail-analyze` уже оценил ветер из трека (в `track:`/отчёте);
   - **era5** — гонки старше ~5 дней: `build_archive_url(lat, lon, date, date)`;
   - **historical-forecast** — свежие гонки (заменить хост на `historical-forecast-api`).
2. Запроси (для era5/historical) и агрегируй по окну гонки:

```bash
python3 - <<PY
import sys, json; sys.path.insert(0, "$SAILING_REPO/lib")
from sailweather.core import build_archive_url, fetch_json, parse_openmeteo, aggregate_window
data = fetch_json(build_archive_url(<lat>, <lon>, "<date>", "<date>"))
p = parse_openmeteo(data, ["best_match"])   # archive: одна серия (без суффикса модели)
s = next(iter(p.values()))
print(json.dumps(aggregate_window(s["time"], s["speed"], s["gust"], s["dir"], "<startISO>", "<endISO>")))
PY
```

3. Через **Edit tool** запиши `weather_actual:` (агрегат + `reference: era5|track-derived|historical-forecast`,
   `source`, `shift_pattern` если очевиден из почасовых данных, `temp_c`).
4. Обнови лог точности: для каждого источника из `weather_forecast_sources[]` посчитай
   ошибку против `weather_actual` и сохрани в `.weather-accuracy.json`:

```bash
python3 - <<PY
import sys, json, os; sys.path.insert(0, "$SAILING_REPO/lib")
from sailweather.core import accuracy_update
acc_path = os.path.join("$SAILING_DIR", ".weather-accuracy.json")
acc = json.load(open(acc_path)) if os.path.exists(acc_path) else {}
sources = <weather_forecast_sources list>
actual = <weather_actual dict: wind_speed_kt, wind_gust_kt, wind_dir_deg>
acc = accuracy_update(acc, sources, actual)
json.dump(acc, open(acc_path, "w"), ensure_ascii=False, indent=2)
print("accuracy updated")
PY
```

5. Добавь в сводку строку «прогноз vs факт» (канонический прогноз vs `weather_actual`).

---

## Режим: ranking

```bash
python3 - <<PY
import sys, json, os; sys.path.insert(0, "$SAILING_REPO/lib")
from sailweather.core import ranking
acc_path = os.path.join("$SAILING_DIR", ".weather-accuracy.json")
acc = json.load(open(acc_path)) if os.path.exists(acc_path) else {}
for r in ranking(acc):
    print(f"{r['source']:28} n={r['n']:3} MAE спд={r['wind_speed_mae_kt']} kt  напр={r['wind_dir_mae_deg']}°  порыв={r['gust_mae_kt']} kt  bias={r['bias_speed_kt']}")
PY
```

Выведи таблицу пользователю; отметь точнейший источник. Когда замеров много —
предложи переключить канонический `weather_forecast` с `ensemble-mean` на лучший источник.

## Отчёт

Кратко: режим; канонический ветер (kt/направление/порывы) и разброс по моделям (forecast);
эталон и «прогноз vs факт» (actual); рейтинг (ranking).

## Обработка ошибок

| Ошибка | Решение |
|--------|---------|
| Сеть/таймаут Open-Meteo | Сообщить; предложить повтор; не выдумывать данные |
| Нет lat/lon у venue | Попросить дополнить venue-файл |
| Archive пуст (слишком свежо) | Перейти на historical-forecast-api |
| Нет `weather_forecast_sources` для actual | Пропустить лог точности, отметить в отчёте |
