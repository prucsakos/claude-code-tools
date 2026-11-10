#!/usr/bin/env bash
# Installed-copy drift check: compares this skill folder with the copy Claude Code loads,
# ${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/my-iterative-optimization, file by file.
# CRs are dropped before each compare, so a CRLF checkout or a CRLF installed copy is not drift.
# It never copies or changes anything; the README's rm + cp is the install step.
# Prints "installed copy matches (<n> files)" and exits 0; one "FAIL <file>: <reason>" line
# per differing, missing or extra file and exits 1; "not installed at <path>" and exits 2.
#
# Usage: bash skills/my-iterative-optimization/install-check.sh
set -u

repo_copy=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
installed=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/my-iterative-optimization

if [ ! -d "$installed" ]; then
  echo "not installed at $installed"
  exit 2
fi

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

# list_files <dir>: the path of every file under <dir>, relative to it, sorted for comm.
list_files() {
  (cd "$1" && find . -type f | sed 's|^\./||' | LC_ALL=C sort)
}
list_files "$repo_copy" > "$scratch/repo"
list_files "$installed" > "$scratch/installed"

failures=0
while IFS= read -r file; do
  echo "FAIL $file: missing from the installed copy"
  failures=$((failures + 1))
done < <(LC_ALL=C comm -23 "$scratch/repo" "$scratch/installed")

while IFS= read -r file; do
  echo "FAIL $file: extra file in the installed copy, not in the repo"
  failures=$((failures + 1))
done < <(LC_ALL=C comm -13 "$scratch/repo" "$scratch/installed")

while IFS= read -r file; do
  if ! cmp -s <(tr -d '\r' < "$repo_copy/$file") <(tr -d '\r' < "$installed/$file"); then
    echo "FAIL $file: differs from the repo copy"
    failures=$((failures + 1))
  fi
done < <(LC_ALL=C comm -12 "$scratch/repo" "$scratch/installed")

if [ "$failures" -gt 0 ]; then exit 1; fi
echo "installed copy matches ($(grep -c '' "$scratch/repo") files)"
