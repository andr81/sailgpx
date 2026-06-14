#!/usr/bin/env bash
set -euo pipefail
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL="$TESTS_DIR/../tooling/install.sh"
fail=0
run() { SAIL_SKILLS_SRC="$src" CLAUDE_SKILLS_DIR="$dst" bash "$INSTALL" >/dev/null; }

work="$(mktemp -d)"
src="$work/skills"; dst="$work/dst"
mkdir -p "$src/sail-foo" "$src/sail-bar" "$dst"
echo "x" > "$src/sail-foo/SKILL.md"
echo "x" > "$src/sail-bar/SKILL.md"

run

[[ -L "$dst/sail-foo" ]] || { echo "FAIL: sail-foo not symlinked"; fail=1; }
[[ -L "$dst/sail-bar" ]] || { echo "FAIL: sail-bar not symlinked"; fail=1; }
# повторный прогон не падает (идемпотентность)
run || { echo "FAIL: not idempotent"; fail=1; }
[[ "$(readlink "$dst/sail-foo")" == "$src/sail-foo" ]] || { echo "FAIL: link changed on rerun"; fail=1; }

# relink: устаревший симлинк → перелинковать на верную цель
rm "$dst/sail-foo"; ln -s "$work/stale-target" "$dst/sail-foo"
run
[[ "$(readlink "$dst/sail-foo")" == "$src/sail-foo" ]] || { echo "FAIL: stale symlink not relinked"; fail=1; }

# backup: реальная папка на месте цели → бэкап + симлинк
rm "$dst/sail-bar"; mkdir "$dst/sail-bar"; echo "real" > "$dst/sail-bar/marker"
run
[[ -L "$dst/sail-bar" ]] || { echo "FAIL: real dir not replaced by symlink"; fail=1; }
ls "$dst"/sail-bar.bak.* >/dev/null 2>&1 || { echo "FAIL: real dir not backed up"; fail=1; }

rm -rf "$work"
[[ $fail -eq 0 ]] && echo "PASS test_install" || { echo "TESTS FAILED"; exit 1; }
