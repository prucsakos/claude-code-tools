#!/usr/bin/env bash
# Structural self-check of this skill. Run it after editing any of the skill's files:
#   bash skills/my-iterative-optimization/check.sh
# It checks structure, never wording:
#   1. SKILL.md frontmatter: name equals the folder name; description has 1 to 1024 characters.
#   2. Each *-prompt.md: every {{X}} below the first --- line is listed in the placeholder
#      table above it, and every listed placeholder is used below it. An unlisted {{X}} is
#      never filled, so it reaches the spawned subagent literally.
#   3. Every "section N" in the skill's .md files has a "## N." heading in SKILL.md.
# Prints one "FAIL <file>: <reason>" line per defect and exits 1, or prints OK and exits 0.
# Each awk program strips CR first, because Windows checkouts may have CRLF line endings.
set -u

skill_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
skill_name=${skill_dir##*/}

check_frontmatter() {
  awk -v folder="$skill_name" '
    { sub(/\r$/, "") }
    NR == 1 { if ($0 != "---") exit; next }
    $0 == "---" { closed = 1; exit }
    /^name:/ { name = $0; sub(/^name:[ \t]*/, "", name); sub(/[ \t]+$/, "", name) }
    /^description:/ { desc = $0; sub(/^description:[ \t]*/, "", desc); sub(/[ \t]+$/, "", desc) }
    END {
      if (!closed) { print "FAIL SKILL.md: no frontmatter between two --- lines at the top"; exit 1 }
      bad = 0
      if (name != folder) { print "FAIL SKILL.md: frontmatter name is \"" name "\", but the folder is \"" folder "\""; bad = 1 }
      if (length(desc) < 1 || length(desc) > 1024) { print "FAIL SKILL.md: frontmatter description has " length(desc) " characters, not 1 to 1024"; bad = 1 }
      exit bad
    }' "$skill_dir/SKILL.md"
}

check_prompt_placeholders() {
  local file status=0
  for file in "$skill_dir"/*-prompt.md; do
    awk -v file="${file##*/}" '
      function collect(text, set) {
        while (match(text, /[{][{][A-Za-z0-9_]+[}][}]/)) {
          set[substr(text, RSTART, RLENGTH)] = 1
          text = substr(text, RSTART + RLENGTH)
        }
      }
      { sub(/\r$/, "") }
      !below && $0 == "---" { below = 1; next }
      # Above the --- line, a placeholder is listed only in the first cell of a table row.
      !below && /^\|/ { split($0, cells, "|"); collect(cells[2], listed); next }
      below { collect($0, used) }
      END {
        if (!below) { print "FAIL " file ": no --- line separates the placeholder table from the prompt"; exit 1 }
        bad = 0
        for (p in used) if (!(p in listed)) { print "FAIL " file ": " p " is used in the prompt but not listed in its placeholder table"; bad = 1 }
        for (p in listed) if (!(p in used)) { print "FAIL " file ": " p " is listed in the placeholder table but not used in the prompt"; bad = 1 }
        exit bad
      }' "$file" || status=1
  done
  return "$status"
}

check_section_references() {
  awk '
    FNR == 1 { file = FILENAME; sub(/.*\//, "", file) }
    { sub(/\r$/, "") }
    file == "SKILL.md" && /^## [0-9]+\. / { number = $2; sub(/\.$/, "", number); heading[number] = 1 }
    {
      text = tolower($0)
      while (match(text, /section [0-9]+/)) {
        # Skip words that only end in "section", such as "subsection".
        if (RSTART == 1 || substr(text, RSTART - 1, 1) !~ /[a-z]/) {
          refs++
          ref_file[refs] = file; ref_line[refs] = FNR
          ref_number[refs] = substr(text, RSTART + 8, RLENGTH - 8)
        }
        text = substr(text, RSTART + RLENGTH)
      }
    }
    END {
      bad = 0
      for (i = 1; i <= refs; i++) if (!(ref_number[i] in heading)) {
        print "FAIL " ref_file[i] ": line " ref_line[i] " refers to section " ref_number[i] ", but SKILL.md has no \"## " ref_number[i] ".\" heading"
        bad = 1
      }
      exit bad
    }' "$skill_dir"/*.md
}

if [ ! -f "$skill_dir/SKILL.md" ]; then
  echo "FAIL SKILL.md: not found in $skill_dir"
  exit 1
fi

status=0
check_frontmatter || status=1
check_prompt_placeholders || status=1
check_section_references || status=1
if [ "$status" -eq 0 ]; then
  echo OK
fi
exit "$status"
