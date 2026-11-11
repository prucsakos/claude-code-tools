#!/usr/bin/env bash
# Run footprint: lists what runs of this skill left in a repo, at any time, also after a
# session that died before its final report. Read-only: it prints delete commands, never runs them.
#   bash skills/my-iterative-optimization/footprint.sh <REPO>
# Lists, one item per line, each line ending with its delete command:
#   worktrees under RUN_DIR = <REPO>.optimize/, local and remote-tracking opt/* and optimize/*
#   branches, Optimize-Run trailer commits on those branches per run id, and RUN_DIR with its size.
# Remote branches are read from the remote-tracking refs (as of the last fetch), not from the network.
# A run branch optimize/<stamp> may be a PR head and holds the run's result, so its local delete
# is commented out; every remote delete is commented out too. optimize/<stamp>-shots holds only
# the screenshots a PR body shows: its local copy may go, its remote one serves the PR's images.
# Prints "nothing left" when clean.
set -u

if [ $# -ne 1 ]; then
  echo "usage: footprint.sh <REPO>" >&2
  exit 2
fi
repo=$(git -C "$1" rev-parse --show-toplevel) || exit 2
run_dir="$repo.optimize"
items=0

# Branch names, remotes, paths and trailers may hold shell metacharacters or terminal escapes:
# a command quotes every such value, and a description drops control characters.
# q <value>: the value shell-quoted for a printed command.
q() {
  printf '%q' "$1"
}

# item <description> <command>: one inventory line; the command is printed, never run.
item() {
  printf '%-72s %s\n' "$(printf '%s' "$1" | tr -d '\000-\037\177')" "$2"
  items=$((items + 1))
}

git_cmd="git -C $(q "$repo")"

while IFS= read -r line; do
  case "$line" in
    "worktree $run_dir/"*)
      path=${line#worktree }
      item "worktree $path" "$git_cmd worktree remove --force -- $(q "$path")"
      ;;
  esac
done < <(git -C "$repo" worktree list --porcelain)

current=$(git -C "$repo" symbolic-ref --quiet --short HEAD || true)
run_refs=()
while IFS= read -r branch; do
  case "$branch" in
    optimize/*-shots)
      item "branch $branch (PR screenshots; the remote copy serves them)" "$git_cmd branch -D -- $(q "$branch")"
      ;;
    optimize/*)
      run_refs+=("refs/heads/$branch")
      note="run branch, holds the result; PR head?"
      [ "$branch" = "$current" ] && note="$note, checked out"
      item "branch $branch ($note)" "# once BASE has it, or to drop the run: $git_cmd branch -D -- $(q "$branch")"
      ;;
    opt/*)
      run_refs+=("refs/heads/$branch")
      item "branch $branch" "$git_cmd branch -D -- $(q "$branch")"
      ;;
  esac
done < <(git -C "$repo" for-each-ref --format='%(refname:short)' refs/heads/opt refs/heads/optimize)

while IFS= read -r ref; do
  remote_branch=${ref#refs/remotes/}
  remote=${remote_branch%%/*}
  branch=${remote_branch#*/}
  case "$branch" in
    optimize/*-shots)
      item "remote $remote/$branch (PR screenshots)" "# after the PR is merged or closed, which removes its screenshots: $git_cmd push --delete -- $(q "$remote") $(q "$branch")"
      ;;
    opt/* | optimize/*)
      run_refs+=("$ref")
      item "remote $remote/$branch (PR head?)" "# after the PR is merged or closed: $git_cmd push --delete -- $(q "$remote") $(q "$branch")"
      ;;
  esac
done < <(git -C "$repo" for-each-ref --format='%(refname)' refs/remotes)

if [ ${#run_refs[@]} -gt 0 ]; then
  while read -r count run_id; do
    item "commits Optimize-Run: $run_id ($count on the branches above)" "# dropped with those branches"
  done < <(git -C "$repo" log --format='%(trailers:key=Optimize-Run,valueonly)' "${run_refs[@]}" \
    | sed '/^$/d' | sort | uniq -c)
fi

if [ -d "$run_dir" ]; then
  size=$(du -sh "$run_dir" | cut -f1)
  item "RUN_DIR $run_dir ($size: STATE, archives, harness, ref, shots)" "rm -rf -- $(q "$run_dir")"
fi

if [ "$items" -eq 0 ]; then
  echo "nothing left"
fi
