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
