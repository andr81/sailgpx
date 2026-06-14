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
