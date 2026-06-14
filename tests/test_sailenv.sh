#!/usr/bin/env bash
set -euo pipefail
LIB="/Users/vita/projects/sailgpx/tooling/sailenv.sh"
fail=0

# Case 1: .env в репе задаёт SAILING_TRACKS_DIR → используется он
repo1="$(mktemp -d)"
printf 'SAILING_TRACKS_DIR=%s\n' "$repo1/custom-tracks" > "$repo1/.env"
got="$(SAILING_REPO="$repo1" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got" == "$repo1/custom-tracks" ]] || { echo "FAIL case1: got=$got"; fail=1; }

# Case 2: нет .env → дефолт <vault>/sailing/tracks
repo2="$(mktemp -d)"; vault2="$(mktemp -d)"
got2="$(SAILING_REPO="$repo2" SAILING_VAULT="$vault2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_TRACKS_DIR\"")"
[[ "$got2" == "$vault2/sailing/tracks" ]] || { echo "FAIL case2: got=$got2"; fail=1; }

# Case 3: SAILING_DIR = <vault>/sailing
got3="$(SAILING_REPO="$repo2" SAILING_VAULT="$vault2" bash -c "source \"$LIB\"; printf '%s' \"\$SAILING_DIR\"")"
[[ "$got3" == "$vault2/sailing" ]] || { echo "FAIL case3: got=$got3"; fail=1; }

rm -rf "$repo1" "$repo2" "$vault2"
[[ $fail -eq 0 ]] && echo "PASS test_sailenv" || { echo "TESTS FAILED"; exit 1; }
