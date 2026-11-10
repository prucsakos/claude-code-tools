#!/usr/bin/env bash
# Seeded-defect test of the self-checks: proves each check still catches its defect class.
# Run it after editing a check script or the skill's layout:
#   bash skills/my-iterative-optimization/seed-check.sh
# It copies this skill folder to a temp directory and runs every check named in the seed table
# on the unmodified copy, which must pass. Then, per seed, it applies the seed's sed edit to a
# fresh copy and runs the seed's check there; the check must exit 1 and print a line containing
# the seed's expected text. Each check finds the skill by its own directory, so the copy's
# script checks the copy. The copy keeps the folder name, which check.sh compares with the
# frontmatter name.
# Prints "OK (<n> seeds caught)" and exits 0; else one line per problem and exits 1:
#   "MISSED <seed>: <check> exited <status>"   the check let the defect through
#   "FAIL seed did not apply: <seed>"          the sed edit changed nothing; not counted as caught
#   "FAIL <check> fails on the unmodified skill"
# To cover a new defect class, add one row to the table.
set -u

skill_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
skill_name=${skill_dir##*/}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
copy="$work/$skill_name"

# seed | file in the skill | sed edit | check that must FAIL | text its output must contain
# No field may contain "|". The edits stay POSIX sed, so they also run with BSD sed.
seeds='
unlisted-placeholder  | experimenter-prompt.md | $ s/$/ {{SEED_UNLISTED}}/                 | check.sh        | {{SEED_UNLISTED}}
unknown-section       | pillars.md             | $ s/$/ See section 99./                   | check.sh        | section 99
removed-reply-field   | integrator-prompt.md   | /^MERGED: /d                              | check.sh        | MERGED: yes
renumbered-setup-step | SKILL.md               | /^## 1\. /,/^## 2\. / s/^4\. /4) /        | source-check.sh | setup step 4
renamed-frontmatter   | SKILL.md               | 1,/^name: / s/^name: /name: seeded-/      | check.sh        | seeded-
'

trim() {
  local s=$1
  s=${s#"${s%%[![:space:]]*}"}
  s=${s%"${s##*[![:space:]]}"}
  printf '%s' "$s"
}

fresh_copy() {
  rm -rf "$copy"
  cp -R "$skill_dir" "$copy"
}

# Every check the table names must pass on the unmodified copy, or a seed result means nothing.
fresh_copy
checks=$(printf '%s\n' "$seeds" | awk -F'|' 'NF >= 5 { gsub(/^[ \t]+|[ \t]+$/, "", $4); print $4 }' | sort -u)
for check in $checks; do
  if ! output=$(bash "$copy/$check" 2>&1); then
    echo "FAIL $check fails on the unmodified skill:"
    printf '%s\n' "$output"
    exit 1
  fi
done

caught=0
status=0
while IFS='|' read -r seed file edit check expect; do
  seed=$(trim "$seed")
  [ -n "$seed" ] || continue
  file=$(trim "$file"); edit=$(trim "$edit"); check=$(trim "$check"); expect=$(trim "$expect")
  fresh_copy
  # Compare with an empty sed edit, not with the file: some sed builds drop CRs, so the output
  # can differ from a CRLF file even when the edit matched nothing.
  sed -e '' "$copy/$file" > "$work/unseeded"
  if ! sed -e "$edit" "$copy/$file" > "$work/seeded" || cmp -s "$work/seeded" "$work/unseeded"; then
    echo "FAIL seed did not apply: $seed"
    status=1
    continue
  fi
  mv "$work/seeded" "$copy/$file"
  output=$(bash "$copy/$check" 2>&1 < /dev/null)
  check_status=$?
  if [ "$check_status" -ne 1 ]; then
    echo "MISSED $seed: $check exited $check_status"
    status=1
  elif ! printf '%s\n' "$output" | grep -qF -- "$expect"; then
    echo "MISSED $seed: $check exited 1 without a line containing \"$expect\""
    status=1
  else
    caught=$((caught + 1))
  fi
done <<EOF
$seeds
EOF

if [ "$status" -eq 0 ]; then
  echo "OK ($caught seeds caught)"
fi
exit "$status"
