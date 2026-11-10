#!/usr/bin/env bash
# Runs every self-check of this skill: check.sh and each *-check.sh in this directory, found
# by glob, so a new check runs here without an edit. checks.sh matches neither pattern, so it
# never runs itself. Each check gets stdin from /dev/null and, where `timeout` exists, 300 s.
# Prints "== <script>" before each check's own output, then one summary line:
#   "OK (<n> checks)" and exit 0, or "FAIL: <names>" and exit 1.
# install-check.sh compares the repo with the installed copy under $HOME, so its result depends
# on the machine, not the repo: "not installed" (its exit 2) is reported as skipped and a
# differing installed copy (its exit 1) as differs, appended to the summary; neither fails the run.
#
# Usage: bash skills/my-iterative-optimization/checks.sh
set -u

skill_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if command -v timeout > /dev/null 2>&1; then
  run_check() { timeout 300 bash "$1" < /dev/null; }
else
  run_check() { bash "$1" < /dev/null; }
fi

passed=0
failed=()
install_note=""
for script in "$skill_dir"/check.sh "$skill_dir"/*-check.sh; do
  name=${script##*/}
  echo "== $name"
  run_check "$script"
  status=$?
  if [ "$status" -eq 0 ]; then
    passed=$((passed + 1))
  elif [ "$name" = install-check.sh ] && [ "$status" -eq 2 ]; then
    install_note="; install-check.sh skipped (not installed)"
  elif [ "$name" = install-check.sh ] && [ "$status" -eq 1 ]; then
    install_note="; install-check.sh differs (installed copy is not the repo's)"
  elif [ "$status" -eq 124 ]; then
    failed+=("$name(timeout)")
  else
    failed+=("$name")
  fi
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAIL: ${failed[*]}$install_note"
  exit 1
fi
echo "OK ($passed checks)$install_note"
