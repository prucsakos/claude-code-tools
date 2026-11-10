#!/usr/bin/env bash
# Behavior self-test of measure.sh: runs it against tiny fake commands and checks the
# contract in its header comment. Prints one "FAIL <case>: expected .. got .." line per
# broken case and exits 1; prints "OK" and exits 0 otherwise. Takes about 2 s.
#
# Usage: bash measure-check.sh [measure.sh to test]   (default: the measure.sh next to this file)
set -u

here=$(cd "$(dirname "$0")" && pwd)
measure=${1:-$here/measure.sh}
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

# measure <runs> <timeout_s> <time|stdout> <lockdir|none> <command>, with the scratch dir as workdir.
# CRs are dropped so the comparisons also hold on Windows Git Bash.
measure() {
  bash "$measure" "$scratch" "$@" | tr -d '\r'
}

out=$(measure 2 5 stdout none 'echo x 1.5')
check stdout "$(printf '1.5\n1.5')" "$out"

out=$(measure 2 5 time none 'true')
numbers=$(printf '%s\n' "$out" | grep -Ec '^[0-9]+(\.[0-9]+)?$')
lines=$(printf '%s\n' "$out" | grep -c '')
check time "2 numeric lines of 2" "$numbers numeric lines of $lines"

out=$(measure 2 5 stdout none 'exit 3')
check non-zero-exit "$(printf 'FAIL 3\nFAIL 3')" "$out"

# The second and third runs must not happen: TIMEOUT ends the measurement.
out=$(measure 3 1 stdout none 'sleep 3')
check timeout "TIMEOUT" "$out"

bash "$measure" "$scratch" 2 5 >/dev/null 2>"$scratch/usage.err"
code=$?
case $(head -n 1 "$scratch/usage.err") in
  usage:*) usage_line=present ;;
  *) usage_line=missing ;;
esac
check usage "exit 2, usage line present" "exit $code, usage line $usage_line"

# One run only: if the lock were not released, a second run would wait for it.
lock=$scratch/lock
out=$(measure 1 5 stdout "$lock" 'echo 7')
if [ -e "$lock" ]; then lock_state=left-behind; else lock_state=released; fi
check lock "7, released" "$out, $lock_state"

if [ "$failures" -gt 0 ]; then exit 1; fi
echo OK
