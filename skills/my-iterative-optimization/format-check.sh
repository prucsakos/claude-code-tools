#!/usr/bin/env bash
# Format self-check of this skill. Run it after editing any of the skill's files:
#   bash skills/my-iterative-optimization/format-check.sh
# It checks file format, never wording:
#   1. Markdown tables in the skill's .md files and in the README.md section headed with the
#      skill's name: every row has as many cells as its header row, counted as GitHub does
#      (unescaped "|", leading and trailing "|" optional; fenced code blocks skipped). A row with
#      fewer cells renders with a merged or empty column; extra cells are dropped.
#   2. Every *.sh in this folder has no CR byte. .gitattributes here sets "*.sh text eol=lf", so git
#      writes LF into the working tree on every platform, also with core.autocrlf on Windows; a CR
#      means an editor wrote CRLF, and bash rejects that script. So the working-tree file is tested.
#   3. Every *.sh in this folder passes "bash -n".
# Prints one "FAIL <file>:<line>: <reason>" line per defect and exits 1, or prints OK and exits 0.
set -u

skill_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
skill_name=${skill_dir##*/}
readme="$skill_dir/../../README.md"

# check_tables <file> <heading text or empty>: with a heading text, only the section under a heading
# that contains it is checked, up to the next heading of the same or a higher level.
check_tables() {
  awk -v file="${1##*/}" -v heading="$2" '
    function cells(row, n) {
      gsub(/\\\|/, "", row)
      sub(/^[ \t]+/, "", row); sub(/[ \t]+$/, "", row)
      n = gsub(/\|/, "|", row) + 1
      if (row ~ /^\|/) n--
      if (length(row) > 1 && row ~ /\|$/) n--
      return n
    }
    BEGIN { in_section = (heading == "") }
    { sub(/\r$/, "") }
    /^ ? ? ?(```|~~~)/ { fenced = !fenced; in_table = 0; next }
    fenced { next }
    heading != "" && /^#+ / {
      level = match($0, / /) - 1
      if (index($0, heading)) { in_section = 1; section_level = level }
      else if (in_section && level <= section_level) in_section = 0
      in_table = 0
      next
    }
    !in_section { next }
    /^[ \t]*$/ { in_table = 0; next }
    !in_table && /^[ \t]*\|/ { in_table = 1; want = cells($0); header = FNR; next }
    in_table && cells($0) != want {
      print "FAIL " file ":" FNR ": table row has " cells($0) " cells, its header (line " header ") has " want
      bad = 1
    }
    END { exit bad }' "$1"
}

check_line_endings() {
  local file=$1 line
  # On Git for Windows, awk drops CRs and grep matched every line for a CR pattern; tr makes CR a byte both keep.
  line=$(tr '\r' '\001' < "$file" | grep -a -n -m 1 $'\001' | cut -d: -f1)
  if [ -n "$line" ]; then
    echo "FAIL ${file##*/}:$line: CR line endings"
    return 1
  fi
}

check_syntax() {
  local file=$1 output
  if output=$(bash -n "$file" 2>&1); then
    return 0
  fi
  # bash -n reports "<path>: line <n>: <message>"; keep the line number and the message.
  printf '%s\n' "$output" | sed -n "s|^.*: line \([0-9][0-9]*\): \(.*\)$|FAIL ${file##*/}:\1: bash -n: \2|p" | grep . ||
    echo "FAIL ${file##*/}:1: bash -n: $output"
  return 1
}

status=0
for file in "$skill_dir"/*.md; do
  check_tables "$file" "" || status=1
done
if [ -f "$readme" ]; then
  check_tables "$readme" "\`$skill_name\`" || status=1
fi
for file in "$skill_dir"/*.sh; do
  check_line_endings "$file" || status=1
  check_syntax "$file" || status=1
done
if [ "$status" -eq 0 ]; then
  echo OK
fi
exit "$status"
