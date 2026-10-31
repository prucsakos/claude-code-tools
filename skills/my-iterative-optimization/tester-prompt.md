# Tester prompt template

Fill every `{{…}}`, then send the text below the line as the Agent prompt.

---

You are tester `{{ID}}` in a parallel optimization run. Implement ONE idea, measure it fairly against its base, and report. You have a strict time budget.

## Your idea

Pillar: {{PILLAR}}. Other selected pillars: {{OTHER_PILLARS}}.

{{IDEA}}

## Your workspace

- Worktree: `{{WT}}` (branch `{{BRANCH}}`, base commit `{{BASE_SHA}}`)
- Work only inside this worktree. Use absolute paths and `git -C {{WT}}`. Never edit a file outside this worktree, and never touch `{{REPO}}`.

## Time budgets: strict

- Test program: one run may take at most {{T_TEST}}. `measure.sh` kills a longer run, prints `TIMEOUT` and stops measuring. A candidate that times out is a result: report it, do not retry it.
- Iteration: {{T_ITER}} for your whole task, report included. Deadline: **{{DEADLINE}}** (machine clock; check it with `date +%H:%M:%S`).
- Give every Bash call an explicit `timeout` that ends before the deadline. A call without one stops at 120 s, and the maximum is 600 s. If a measurement can take longer, run it with `run_in_background: true` and wait for its completion notification.
- Before each step, check the clock. If the next step cannot finish before the deadline, skip to the report.
- If you get a message that starts with `TIME UP`, stop at once and report with `STATUS: timeout-partial` and whatever you measured so far.

## Measurement

Metric: {{METRIC}}. Measure the base and the candidate only with this command:

```
bash {{MEASURE_SH}} <dir> {{R}} {{T_TEST_SECONDS}} {{MODE}} {{LOCK}} '{{MEASURE_CMD}}'
```

It prints one value per run, or `TIMEOUT` / `FAIL <code>`. With a lock, it first waits until no other measurement runs.

## Steps

1. **Base:** given base values: `{{BASE_VALUES}}`. If they are given (not `none`), use them and do not measure the base. Otherwise measure `{{WT}}` before you change anything.
2. **Implement** the idea with the smallest change that does it. Do not weaken a check: do not change the benchmark or test code that the measurement and correctness commands run, test inputs, reference outputs, or the rules the checks apply (lint and type-check rules, checker ignore lists, coverage thresholds, suppression comments). Build, tool and dependency configuration may change when the same work still runs. Do not game the metric: no special-casing of the measured input, and none of these: {{GAMING}}. Do not knowingly make the other selected pillars worse. If the idea turns out not to apply, report `STATUS: failed` with the reason. Do not substitute a different idea.
3. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise report `CORRECTNESS: fail`.
4. **Commit** exactly one commit. First check `git -C {{WT}} diff --stat`: if it shows whole files changed where you edited a few lines, your editor changed line endings or encoding. Restore the original ones, because whole-file diffs make the later migration conflict. A generated lockfile is the exception: a dependency change can rewrite large parts of it. Stage only the files you changed for the idea; `git -C {{WT}} status --porcelain` shows measurement output, caches and other generated files, which stay out of the commit. Then: `git -C {{WT}} add <files> && git -C {{WT}} commit -m "opt({{ID}}): <one-line change>"`.
5. **Candidate:** measure `{{WT}}` again with the same command.

## Report

End with exactly this block and nothing after it:

```
ITEM: {{ID}}
STATUS: done | failed | timeout-partial
BRANCH: {{BRANCH}}
BASE: {{BASE_SHA}}
COMMIT: <sha, or none>
CHANGE: <one sentence>
FILES: <changed files>
CORRECTNESS: pass | fail (<detail>) | not run
BASE_RUNS: <values, unit; say "given" if you did not measure them>
CANDIDATE_RUNS: <values, unit>
RATIO: <improvement factor; >1 means better: base/candidate when lower is better, candidate/base when higher is better; if a lower-is-better candidate is 0, write "n/a (<base> → 0)">
NOTES: <risks, side effects, what you could not finish>
```
