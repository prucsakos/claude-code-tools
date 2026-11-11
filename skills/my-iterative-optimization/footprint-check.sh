#!/usr/bin/env bash
# Behavior self-test of footprint.sh: seeds run leftovers into a temp repo and checks the
# contract in its header comment. Prints one "FAIL: <assertion>: expected .. got .." line per
# broken assertion and exits 1; prints "OK (<n> assertions)" and exits 0 otherwise.
#
# Usage: bash footprint-check.sh [footprint.sh to test]   (default: the footprint.sh next to this file)
set -u

here=$(cd "$(dirname "$0")" && pwd)
footprint=${1:-$here/footprint.sh}
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
failures=0
assertions=0

# The user's git config (hooks, signing, default branch) must not change the seeded repos.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=check GIT_AUTHOR_EMAIL=check@example.invalid
export GIT_COMMITTER_NAME=check GIT_COMMITTER_EMAIL=check@example.invalid

# check <assertion> <expected> <actual>
check() {
  assertions=$((assertions + 1))
  if [ "$2" != "$3" ]; then
    echo "FAIL: $1: expected $(printf %q "$2") got $(printf %q "$3")"
    failures=$((failures + 1))
  fi
}

# new_repo <dir>: a repo with one commit; prints its top level as git reports it, the form
# footprint.sh derives RUN_DIR from.
new_repo() {
  git init -q "$1" && git -C "$1" commit -q --allow-empty -m init && git -C "$1" rev-parse --show-toplevel
}

# footprint <repo>: footprint.sh's output with CRs dropped, so comparisons also hold on Windows Git Bash.
footprint() {
  bash "$footprint" "$1" | tr -d '\r'
}

# refs_and_worktrees <repo>: everything footprint.sh must leave unchanged.
refs_and_worktrees() {
  git -C "$1" for-each-ref
  git -C "$1" worktree list --porcelain
}

stamp=20260101-0000
repo=$(new_repo "$scratch/repo")
git init -q --bare "$scratch/origin.git"
git -C "$repo" remote add origin "$scratch/origin.git"
run_commit=$(git -C "$repo" commit-tree -p HEAD -m "run result" -m "Optimize-Run: $stamp" 'HEAD^{tree}')
item_commit=$(git -C "$repo" commit-tree -p "$run_commit" -m "item" -m "Optimize-Run: $stamp" 'HEAD^{tree}')
git -C "$repo" branch "optimize/$stamp" "$run_commit"
git -C "$repo" branch opt/1 "$item_commit"
git -C "$repo" branch 'opt/a;b' HEAD
git -C "$repo" worktree add -q --detach "$repo.optimize/wt/x"
git -C "$repo" branch "optimize/$stamp-shots" HEAD
git -C "$repo" push -q origin "optimize/$stamp" "optimize/$stamp-shots"
git -C "$repo" fetch -q origin

before=$(refs_and_worktrees "$repo")
out=$(footprint "$repo")
after=$(refs_and_worktrees "$repo")

# (a) One line per leftover; the two trailer commits are counted once under their run id.
count_lines() {
  printf '%s\n' "$out" | grep -c -e "$1"
}
check "worktree listed" 1 "$(count_lines '^worktree .*\.optimize/wt/x ')"
check "opt/1 listed" 1 "$(count_lines '^branch opt/1 ')"
check "optimize/$stamp listed" 1 "$(count_lines "^branch optimize/$stamp ")"
check "origin/optimize/$stamp listed" 1 "$(count_lines "^remote origin/optimize/$stamp ")"
check "shots branch listed as screenshots" "1 1" "$(count_lines "^branch optimize/$stamp-shots (PR screenshots") $(count_lines "^remote origin/optimize/$stamp-shots (PR screenshots")"
check "Optimize-Run count listed" 1 "$(count_lines "Optimize-Run: $stamp (2 ")"
check "RUN_DIR listed" 1 "$(count_lines '^RUN_DIR .*\.optimize ')"

# (b) The run branch's local delete and every remote delete are commented out; opt/1's is not.
check "optimize/$stamp delete commented out" 1 "$(count_lines "^branch optimize/$stamp .* #.*branch -D")"
pushes=$(count_lines 'push --delete')
check "every push --delete commented out" "$pushes" "$(count_lines ' #.*push --delete')"
check "opt/1 delete not commented out" "1 0" "$(count_lines '^branch opt/1 .*branch -D') $(count_lines '^branch opt/1 .*#')"
check "local shots delete not commented out" 0 "$(count_lines "^branch optimize/$stamp-shots .*#")"

# (c) A branch name holding a shell metacharacter is quoted in its command.
semicolon_line=$(printf '%s\n' "$out" | grep -F 'branch opt/a;b')
check "opt/a;b quoted" "-- $(printf %q 'opt/a;b')" "-- ${semicolon_line##* -- }"

# (d) Read-only: refs and worktrees are the same before and after.
check "refs and worktrees unchanged" "$before" "$after"

# (e) A repo without leftovers.
clean=$(new_repo "$scratch/clean")
check "clean repo" "nothing left" "$(footprint "$clean")"

if [ "$failures" -gt 0 ]; then exit 1; fi
echo "OK ($assertions assertions)"
