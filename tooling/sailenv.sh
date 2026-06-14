#!/usr/bin/env bash
# Резолвер путей парусной системы. Использование: source этот файл.
# Экспортирует: SAILING_REPO, SAILING_VAULT, SAILING_DIR, SAILING_TRACKS_DIR.
# SAILING_REPO / SAILING_VAULT можно переопределить извне (тесты).
# Приоритет источника SAILING_TRACKS_DIR: значение из .env репы > дефолт
# <vault>/sailing/tracks. (.env — единственный канал конфигурации пути.)

_sailenv_self="${BASH_SOURCE[0]}"
SAILING_REPO="${SAILING_REPO:-$(cd "$(dirname "$_sailenv_self")/.." && pwd)}"
SAILING_VAULT="${SAILING_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian}"
SAILING_DIR="$SAILING_VAULT/sailing"
unset _sailenv_self

if [[ -f "$SAILING_REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SAILING_REPO/.env"
  set +a
fi

SAILING_TRACKS_DIR="${SAILING_TRACKS_DIR:-$SAILING_DIR/tracks}"
export SAILING_REPO SAILING_VAULT SAILING_DIR SAILING_TRACKS_DIR
