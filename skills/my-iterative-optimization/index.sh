#!/usr/bin/env bash
# Combine several component metrics into one index number, for use as a MEASURE_CMD:
#   bash measure.sh <workdir> <runs> <timeout_s> stdout <lockdir|none> 'bash index.sh <spec.tsv>'
#
# Usage: bash index.sh <spec.tsv>
# The spec has one tab-separated line per component. Lines starting with # and empty lines
# are skipped.
#   name  direction  floor  weight  base  command
#   direction  lower or higher: which way is better
#   floor      > 0; a value below the floor counts as the floor, so a 0 never divides
#   weight     at most 0.5, so no single component is the whole index; weights sum to 1;
#              0 marks a retired component: its base column is then its limit, and a value
#              worse than the limit (above it for lower, below it for higher) exits 3
#   base       the component's value on the base commit
#   command    the rest of the line; run with bash -c from the current directory; its value
#              is the last number it prints on stdout, as in measure.sh
# Per component, the ratio r says how many times better than base it is, capped to 1/4..4
# so that one component cannot carry or sink the index alone:
#   lower:  r = max(base, floor) / max(value, floor)
#   higher: r = max(value, floor) / max(base, floor)
# index = 100 * exp(sum of weight * ln r), a weighted geometric mean: 100 at base, 200 when
# every component is twice as good.
# Prints "name=<value>" per component, then "index=<n>" (one decimal) as the last line,
# so the last number on stdout, which measure.sh takes, is the index.
# Exit codes: 0 ok; 1 a command exits non-zero or prints no number ("FAIL <name>: <reason>"
# on stderr); 2 usage error or invalid spec (one message line on stderr, no command run);
# 3 a retired component is beyond its limit ("FAIL <name>: <value> beyond limit <limit>").
set -u

number='[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'

invalid() {
  echo "index.sh: $1" >&2
  exit 2
}

# awk_true <condition on x> <x>: compares decimals, which bash arithmetic cannot.
awk_true() {
  awk -v x="$2" "BEGIN { x += 0; exit !($1) }"
}

[ $# -eq 1 ] || invalid "usage: bash index.sh <spec.tsv>"
[ -f "$1" ] || invalid "spec file not found: $1"

names=() directions=() floors=() weights=() bases=() commands=()
while IFS= read -r line || [ -n "$line" ]; do
  line=${line%$'\r'}
  case $line in '' | '#'*) continue ;; esac
  IFS=$'\t' read -r name direction floor weight base command <<<"$line"
  [ -n "$command" ] || invalid "$name: expected 6 tab-separated fields: name direction floor weight base command"
  case $direction in lower | higher) ;; *) invalid "$name: direction is '$direction', not lower or higher" ;; esac
  [[ $floor =~ ^$number$ ]] || invalid "$name: floor '$floor' is not a number"
  [[ $weight =~ ^$number$ ]] || invalid "$name: weight '$weight' is not a number"
  [[ $base =~ ^$number$ ]] || invalid "$name: base '$base' is not a number"
  awk_true 'x > 0' "$floor" || invalid "$name: floor is $floor, must be above 0"
  awk_true 'x <= 0.5' "$weight" || invalid "$name: weight is $weight, must be at most 0.5"
  names+=("$name") directions+=("$direction") floors+=("$floor")
  weights+=("$weight") bases+=("$base") commands+=("$command")
done <"$1"

weighted=$(printf '%s
' "${weights[@]}" | awk '$1 > 0 { n++ } END { print n + 0 }')
[ "$weighted" -ge 2 ] || invalid "the spec has $weighted weighted component(s), needs at least 2"
weight_sum=$(printf '%s\n' "${weights[@]}" | awk '{ s += $1 } END { print s }')
awk_true 'x >= 0.999 && x <= 1.001' "$weight_sum" || invalid "weights sum to $weight_sum, not 1"

rows=
for i in "${!names[@]}"; do
  out=$(bash -c "${commands[i]}")
  code=$?
  if [ "$code" -ne 0 ]; then
    echo "FAIL ${names[i]}: command exited $code" >&2
    exit 1
  fi
  value=$(printf '%s\n' "$out" | grep -Eo -- "$number" | tail -n 1)
  if [ -z "$value" ]; then
    echo "FAIL ${names[i]}: command printed no number on stdout" >&2
    exit 1
  fi
  echo "${names[i]}=$value"
  if awk_true 'x == 0' "${weights[i]}"; then
    if [ "${directions[i]}" = lower ]; then beyond="x > ${bases[i]}"; else beyond="x < ${bases[i]}"; fi
    if awk_true "$beyond" "$value"; then
      echo "FAIL ${names[i]}: $value beyond limit ${bases[i]}" >&2
      exit 3
    fi
  fi
  rows+="${directions[i]} ${floors[i]} ${weights[i]} ${bases[i]} $value"$'\n'
done

printf '%s' "$rows" | awk '
  {
    direction = $1; floor_value = $2 + 0; weight = $3 + 0; base = $4 + 0; value = $5 + 0
    if (base < floor_value) base = floor_value
    if (value < floor_value) value = floor_value
    r = (direction == "lower") ? base / value : value / base
    if (r > 4) r = 4
    if (r < 0.25) r = 0.25
    sum += weight * log(r)
  }
  END { printf "index=%.1f\n", 100 * exp(sum) }'
