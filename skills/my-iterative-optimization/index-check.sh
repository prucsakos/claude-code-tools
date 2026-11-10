#!/usr/bin/env bash
# Behavior self-test of index.sh: runs it on tiny specs whose commands echo fixed values,
# and checks the contract in its header comment. Prints one "FAIL <case>: expected .. got .."
# line per broken case and exits 1; prints "OK" and exits 0 otherwise. Takes about 2 s.
#
# Usage: bash index-check.sh [index.sh to test]   (default: the index.sh next to this file)
set -u

here=$(cd "$(dirname "$0")" && pwd)
index=${1:-$here/index.sh}
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
failures=0

# check <case> <expected> <actual>
check() {
  if [ "$2" != "$3" ]; then
    echo "FAIL $1: expected $(printf %q "$2") got $(printf %q "$3")"
    failures=$((failures + 1))
  fi
}

# spec <file> <line>...: writes one spec line per argument; "|" stands for a tab.
spec() {
  local file=$scratch/$1
  shift
  printf '%s\n' "$@" | tr '|' '\t' >"$file"
}

# last_line <spec file>: runs index.sh in the scratch dir and prints its last stdout line.
last_line() {
  (cd "$scratch" && bash "$index" "$1") 2>/dev/null | tr -d '\r' | tail -n 1
}

spec base.tsv '# components at their base values' 'words|lower|1|0.5|120|echo words 120' 'speed|higher|1|0.5|30|echo 30'
check base "index=100.0" "$(last_line base.tsv)"

# words halved, lower is better: r = 2 and 1, index = 100 * sqrt(2).
spec halved.tsv 'words|lower|1|0.5|120|echo 60' 'speed|higher|1|0.5|30|echo 30'
check halved "index=141.4" "$(last_line halved.tsv)"

# errors drops from 10 to 0: the floor 1 avoids a division by 0, and r = 10 is capped at 4.
spec capped.tsv 'errors|lower|1|0.5|10|echo 0' 'speed|higher|1|0.5|30|echo 30'
check capped "index=200.0" "$(last_line capped.tsv)"

# Each invalid spec exits 2 with one message line, before any command runs.
spec heavy.tsv 'a|lower|1|0.6|10|touch ran; echo 10' 'b|lower|1|0.4|10|touch ran; echo 10'
spec sum.tsv 'a|lower|1|0.5|10|touch ran; echo 10' 'b|lower|1|0.4|10|touch ran; echo 10'
spec single.tsv 'a|lower|1|0.5|10|touch ran; echo 10'
for name in heavy sum single; do
  (cd "$scratch" && bash "$index" "$name.tsv") >/dev/null 2>"$scratch/err"
  code=$?
  messages=$(tr -d '\r' <"$scratch/err" | grep -c .)
  if [ -e "$scratch/ran" ]; then ran=yes; else ran=no; fi
  check "invalid-$name" "exit 2, 1 message line, command ran: no" "exit $code, $messages message line, command ran: $ran"
  rm -f "$scratch/ran"
done

spec failing.tsv 'a|lower|1|0.5|10|exit 1' 'b|lower|1|0.5|10|echo 10'
(cd "$scratch" && bash "$index" failing.tsv) >/dev/null 2>"$scratch/err"
code=$?
check failing-command "exit 1, FAIL a" "exit $code, $(tr -d '\r' <"$scratch/err" | grep -o '^FAIL a')"

# A retired component (weight 0) leaves the index alone within its limit, and exits 3 beyond it.
spec retired-within.tsv 'a|lower|1|0.5|10|echo 10' 'b|lower|1|0.5|10|echo 10' 'old|lower|1|0|12|echo 12'
spec retired-beyond.tsv 'a|lower|1|0.5|10|echo 10' 'b|lower|1|0.5|10|echo 10' 'old|lower|1|0|12|echo 15'
within=$(last_line retired-within.tsv)
(cd "$scratch" && bash "$index" retired-beyond.tsv) >/dev/null 2>"$scratch/err"
code=$?
check retired-limit "index=100.0, exit 3, FAIL old" "$within, exit $code, $(tr -d '\r' <"$scratch/err" | grep -o '^FAIL old')"

# Through measure.sh, the measured value is the index, not a component value.
out=$(bash "$here/measure.sh" "$scratch" 1 30 stdout none "bash $(printf %q "$index") halved.tsv" | tr -d '\r')
check measure "141.4" "$out"

if [ "$failures" -gt 0 ]; then exit 1; fi
echo OK
