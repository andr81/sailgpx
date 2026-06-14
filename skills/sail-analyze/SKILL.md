---
name: sail-analyze
description: Анализ GPS-трека парусной гонки как тренер-тактик — скорость, TWD/TWA, VMG, повороты (tack/gybe) с углами и ценой, сегментация ног, groove; SVG-рендер трека. Пишет метрики и картинку в заметку гонки, ставит status analyzed. Единицы kt/nm. Activates on /sail-analyze, "разобрать гонку", "анализ трека", "проанализируй трек", "метрики гонки", "разбор трека".
---

# Sail Analyze

Разбор GPS-трека как тренер-тактик. Чистый Python (stdlib), без внешних зависимостей.

## ⛔ Критические правила

- Единицы — kt/nm, направления — градусы (0°=N). Не выдумывать — числа только из анализа.
- Таблицу метрик и рендер писать **только** между
  `<!-- sail:auto:start analysis -->` … `<!-- sail:auto:end analysis -->`.
  Пользовательский текст и другие auto-секции не трогать. Обновлять `updated:`.
- TWD из трека — **оценка** (для тренировочных треков ненадёжна). Если есть
  `weather_actual.wind_dir_deg` — передавать его как `--twd` (приоритет).

## Конфигурация

```bash
SAILING_REPO="/Users/vita/projects/sailgpx"
source "$SAILING_REPO/tooling/sailenv.sh"   # → SAILING_TRACKS_DIR
```

## Workflow

1. Найди папку гонки и `files/track.gpx` (если трека нет — предложи `/sail-race import`).
2. Параметры лодки: прочитай `boats/<boat>.md` → `{upwind_twa, downwind_twa, hull_length_m}`.
3. TWD: если в заметке есть `weather_actual.wind_dir_deg` — используй как `--twd`;
   иначе анализатор оценит из трека.
4. Запусти анализатор:

```bash
RACE_DIR="$SAILING_TRACKS_DIR/<slug>"
PYTHONPATH="$SAILING_REPO/lib" python3 -m sailtrack.cli \
  "$RACE_DIR/files/track.gpx" \
  [--twd <weather_actual.wind_dir_deg>] \
  --boat-json '{"upwind_twa":<u>,"downwind_twa":<d>,"hull_length_m":<h>}' \
  --svg "$RACE_DIR/files/track-render.svg"
```

Возвращает JSON: `speed{max_kt,avg_kt}`, `wind{twd_deg,twd_source}`,
`maneuvers{tacks,gybes,avg_tacking_angle_deg,list[]}`, `legs[]`, `groove_twa_std_deg`.

5. Через **Edit tool** между `<!-- sail:auto:start analysis -->` … `end` запиши:
   - сводку (дистанция nm, длительность, max/avg kt; TWD + источник);
   - таблицу поворотов (tacks/gybes, средний угол лавировки, заметные потери/восстановление из `list`);
   - таблицу ног (`type`, `duration_min`, `avg_speed_kt`, `avg_vmg_kt`, `% правый галс`);
   - groove (σ TWA на лавировке);
   - встрой рендер: `![[files/track-render.svg]]`.
   Если `twd_source == "estimated"` — добавь пометку «TWD оценён из трека, ориентир».
6. Через **Edit tool** обнови `track:` (tacks, gybes; duration_min/distance_nm/max_speed_kt/avg_speed_kt
   уже могли стоять от import — синхронизируй) и поставь `status: analyzed`.
7. Опционально: если TWD оценивался и трек «чистый» — можно записать `track-derived`
   ветер для `/sail-weather actual` (reference=track-derived).
8. Дай краткий тренерский разбор (2–4 пункта): что по скорости/углам/поворотам/groove
   стоит улучшить.

## Замечания по методу (v1)

- Реализация на stdlib; рендер — SVG (не matplotlib), раскраска **красный=медленно →
  зелёный=быстро**. Метрики калибруются на размеченных треках (§6 спеки). Углы
  лавировки/повороты надёжны; сегментация ног и оценка TWD — ориентировочные.
  %-of-polar, VMC к знакам и route-efficiency — будущее (нужны polar и координаты знаков).
- **Знаки могут переноситься между гонками одного дня** — позицию верхнего/нижнего знака
  определять по треку каждой гонки отдельно (по апексу наветренной/подветренной части),
  не переносить из соседней гонки.

## Обработка ошибок

| Ошибка | Решение |
|--------|---------|
| Нет `track.gpx` | Предложить `/sail-race import <gpx>` |
| `error: too few points` в JSON | Сообщить, что трек слишком короткий/битый |
| Нет параметров лодки | Запустить с дефолтами (upwind 45, downwind 150), отметить |
