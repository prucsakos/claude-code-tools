#!/usr/bin/env bash
# Structural self-check of this skill. Run it after editing any of the skill's files:
#   bash skills/my-iterative-optimization/check.sh
# It checks structure, never wording:
#   1. SKILL.md frontmatter: name equals the folder name; description has 1 to 1024 characters.
#   2. Each *-prompt.md: every {{X}} below the first --- line is listed in the placeholder
#      table above it, and every listed placeholder is used below it. An unlisted {{X}} is
#      never filled, so it reaches the spawned subagent literally.
#   3. Every "section N" in the skill's .md files has a "## N." heading in SKILL.md.
#   4. Every reply literal SKILL.md acts on, a backticked `FIELD: value` or a bare status value
#      such as `timeout-partial`, is a field and value of a role reply format: the last fenced
#      block of each *-prompt.md, or a backticked one-line reply such as the researcher DONE line.
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

check_reply_contract() {
  awk '
    function add_reply_line(line,   parts, n, i, field, value, alts, m, j, alt) {
      n = split(line, parts, /; /)
      for (i = 1; i <= n; i++) {
        if (!match(parts[i], /^[ \t]*[A-Za-z_]+: /)) continue
        field = parts[i]; sub(/^[ \t]*/, "", field); sub(/:.*/, "", field)
        value = parts[i]; sub(/^[ \t]*[A-Za-z_]+: /, "", value)
        fields[field] = 1
        m = split(value, alts, / [|] /)
        for (j = 1; j <= m; j++) {
          # An alternative is its words before a placeholder or a dash: "no (<reason>)" is "no".
          alt = alts[j]; sub(/ — .*/, "", alt); sub(/[ \t]*[(<].*/, "", alt); sub(/[ \t]+$/, "", alt)
          values[field, alt] = 1; any_value[alt] = 1
        }
      }
    }
    FNR == 1 { file = FILENAME; sub(/.*\//, "", file); fence = 0; delete block; block_lines = 0 }
    FNR == 1 && file ~ /-prompt[.]md$/ { role = file; sub(/-prompt[.]md$/, "", role); roles[role] = 1 }
    { sub(/\r$/, "") }
    file != "SKILL.md" && /^```/ {
      if (fence) { for (i = 1; i <= block_lines; i++) last_block[file, i] = block[i]; last_lines[file] = block_lines; delete block; block_lines = 0 }
      fence = !fence; next
    }
    file != "SKILL.md" && fence { block[++block_lines] = $0; next }
    # A one-line reply, such as the researcher final answer, is a backticked "FIELD: a | b" outside the blocks.
    file != "SKILL.md" {
      text = $0
      while (match(text, /`[A-Z_]+: [^`]* [|] [^`]*`/)) {
        add_reply_line(substr(text, RSTART + 1, RLENGTH - 2))
        text = substr(text, RSTART + RLENGTH)
      }
      next
    }
    file == "SKILL.md" && !replies_read {
      # The reply block of a prompt is its last fenced block.
      for (key in last_lines) for (i = 1; i <= last_lines[key]; i++) add_reply_line(last_block[key, i])
      replies_read = 1
    }
    file == "SKILL.md" {
      text = $0
      while (match(text, /`[^`]+`/)) {
        literal = substr(text, RSTART + 1, RLENGTH - 2)
        text = substr(text, RSTART + RLENGTH)
        if (match(literal, /^[A-Za-z_]+: /)) {
          field = literal; sub(/:.*/, "", field)
          value = literal; sub(/^[A-Za-z_]+: /, "", value)
          # A reply literal has an upper-case field like the reply blocks, a known field, or a yes/no flag.
          if (field !~ /^[A-Z][A-Z_]*$/ && !(field in fields) && value !~ /^(yes|no)$/) continue
          if (!((field, value) in values)) { print "FAIL SKILL.md: line " FNR ": " literal " — no role reply defines it"; bad = 1 }
        } else if (literal ~ /^[a-z]+(-[a-z]+)+$/ && !(literal in any_value)) {
          # A bare status value such as "timeout-partial" is a hyphenated word; one that starts with a role
          # name, such as "researcher-code-hygiene", is an agent name instead.
          split(literal, words, "-")
          if (!(words[1] in roles)) { print "FAIL SKILL.md: line " FNR ": " literal " — no role reply defines it"; bad = 1 }
        }
      }
    }
    END { exit bad }' "$skill_dir"/*-prompt.md "$skill_dir/SKILL.md"
}

if [ ! -f "$skill_dir/SKILL.md" ]; then
  echo "FAIL SKILL.md: not found in $skill_dir"
  exit 1
fi

status=0
check_frontmatter || status=1
check_prompt_placeholders || status=1
check_section_references || status=1
check_reply_contract || status=1
if [ "$status" -eq 0 ]; then
  echo OK
fi
exit "$status"
