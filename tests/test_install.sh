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
