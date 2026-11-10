#!/usr/bin/env bash
# Check that every source a prompt's placeholder table names exists in SKILL.md.
#
# Usage: bash source-check.sh [skill_dir]   (default: the directory of this script)
# In each "| {{X}} | <source> |" row of the *-prompt.md files it resolves:
#   Plan input NAME[, NAME]   a row of SKILL.md's "| Input | Default and notes |" table
#   setup step N              a numbered item "N." under "## 1. Setup"
#   section N, Name           a bold paragraph lead "**Name" under "## N."
# Prints one line per reference that does not resolve and exits 1; else prints the
# count checked and exits 0. Without it, renaming an input, a step or a paragraph
# leaves prompt rows that point at nothing, and the orchestrator guesses the value.
set -u

dir=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
skill="$dir/SKILL.md"
[ -f "$skill" ] || { echo "no $skill" >&2; exit 2; }
prompts=("$dir"/*-prompt.md)
[ -f "${prompts[0]}" ] || { echo "no *-prompt.md in $dir" >&2; exit 2; }

awk -v skill="$skill" '
# A CRLF checkout must pass too.
{ sub(/\r$/, "") }

FILENAME == skill {
  if ($0 ~ /^## /) {
    sec = ($0 ~ /^## [0-9]+\. /) ? $2 + 0 : ""
    intable = 0
  }
  if (sec == 1 && match($0, /^[0-9]+\. /)) steps[substr($0, 1, RLENGTH - 2) + 0] = 1
  if (sec != "" && $0 ~ /^\*\*/) leads[sec, ++nlead[sec]] = substr($0, 3)
  if ($0 == "| Input | Default and notes |") { intable = 1; next }
  if (intable && $0 !~ /^\|/) intable = 0
  if (intable && $0 !~ /^\|[-: |]+$/) {
    split($0, cell, "|")
    names = cell[2]
    # Drop the tags such as *per optimize target* and *advanced*.
    gsub(/ *\*[^*]*\*/, "", names)
    gsub(/^ +|[ ,]+$/, "", names)
    n = split(names, name, ", ")
    for (i = 1; i <= n; i++) inputs[name[i]] = 1
  }
  next
}

function report(ref, ok) {
  checked++
  if (!ok) { printf "%s:%d: %s not found in SKILL.md\n", FILENAME, FNR, ref; bad++ }
}

function has_lead(n, title,    i, lead) {
  for (i = 1; i <= nlead[n]; i++) {
    lead = leads[n, i]
    if (index(lead, title) == 1 && substr(lead, length(title) + 1, 1) ~ /[*:.]/) return 1
  }
  return 0
}

/^\|[^|]*\{\{[A-Z_]+\}\}[^|]*\|/ {
  src = $0
  sub(/^\|[^|]*\|/, "", src)

  s = src
  while (match(s, /[Pp]lan input [A-Z][A-Za-z_;]*(, [A-Z][A-Za-z_;]*)*/)) {
    names = substr(s, RSTART + 11, RLENGTH - 11)
    s = substr(s, RSTART + RLENGTH)
    n = split(names, name, ", ")
    for (i = 1; i <= n; i++) report("Plan input " name[i], (name[i] in inputs))
  }

  s = src
  while (match(s, /[Ss]etup step [0-9]+/)) {
    n = substr(s, RSTART + 11, RLENGTH - 11) + 0
    s = substr(s, RSTART + RLENGTH)
    report("setup step " n, (n in steps))
  }

  s = src
  while (match(s, /[Ss]ection [0-9]+, [^,.;)|]+/)) {
    ref = substr(s, RSTART, RLENGTH)
    s = substr(s, RSTART + RLENGTH)
    sub(/ +$/, "", ref)
    n = substr(ref, 9) + 0
    title = ref
    sub(/^[^,]*, /, "", title)
    report(ref, has_lead(n, title))
  }
}

END {
  if (bad) { printf "source-check: %d of %d references not found\n", bad, checked; exit 1 }
  printf "source-check: %d references found in SKILL.md\n", checked
}
' "$skill" "${prompts[@]}"
