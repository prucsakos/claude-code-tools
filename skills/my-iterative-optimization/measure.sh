#!/usr/bin/env bash
# Run a measurement command several times and print one value per run.
#
# Usage: bash measure.sh <workdir> <runs> <timeout_s> <time|stdout> <lockdir|none> <command>
#   time    the value is the command's wall-clock seconds
#   stdout  the value is the last number the command prints on stdout
# A run that exceeds <timeout_s> prints "TIMEOUT" and ends the measurement, because
# repeating a run that hangs or is too slow only burns the time budget.
# A non-zero exit prints "FAIL <code>".
# With a lockdir, only one measurement on the machine runs at a time, so parallel
# experimenters do not slow each other down.
set -u

if [ $# -ne 6 ]; then
  echo "usage: bash measure.sh <workdir> <runs> <timeout_s> <time|stdout> <lockdir|none> <command>" >&2
  exit 2
fi
workdir=$1 runs=$2 limit=$3 mode=$4 lockdir=$5 cmd=$6

acquire_lock() {
  [ "$lockdir" = none ] && return 0
  until mkdir "$lockdir" 2>/dev/null; do
    # A holder can never legitimately keep the lock longer than one run's timeout,
    # so an older lock was left by a killed process.
    local age=$(( $(date +%s) - $(stat -c %Y "$lockdir" 2>/dev/null || date +%s) ))
    if [ "$age" -gt $((limit + 30)) ]; then rm -rf "$lockdir"; fi
    sleep 1
  done
}

release_lock() {
  [ "$lockdir" = none ] && return 0
  rm -rf "$lockdir"
}

cd "$workdir" || exit 2
for _ in $(seq "$runs"); do
  acquire_lock
  start=$(date +%s.%N)
  out=$(timeout "$limit" bash -c "$cmd" 2>/dev/null)
  code=$?
  end=$(date +%s.%N)
  release_lock

  if [ "$code" -eq 124 ]; then echo TIMEOUT; break; fi
  if [ "$code" -ne 0 ]; then echo "FAIL $code"; continue; fi
  if [ "$mode" = time ]; then
    awk -v s="$start" -v e="$end" 'BEGIN { printf "%.3f\n", e - s }'
  else
    value=$(printf '%s\n' "$out" | grep -Eo '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?' | tail -n 1)
    echo "${value:-FAIL no-number}"
  fi
done
