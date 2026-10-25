# Tester prompt template

Fill every `{{…}}`, then send the text below the line as the Agent prompt.

---

You are tester `{{ID}}` in a parallel optimization run. Implement ONE idea, measure it fairly against its base, and report. You have a strict time budget.

## Your idea

{{IDEA}}

## Your workspace

- Worktree: `{{WT}}` (branch `{{BRANCH}}`, base commit `{{BASE_SHA}}`)
- Work only inside this worktree. Use absolute paths and `git -C {{WT}}`. Never touch `{{REPO}}` or any other worktree.

## Time budget: strict

- Budget: {{T}}. Deadline: **{{DEADLINE}}** (machine clock; check it with `date +%H:%M:%S`).
- Give every Bash call an explicit `timeout` that ends before the deadline. A call without one stops at 120 s.
- Before each step, check the clock. If the next step cannot finish before the deadline, skip to the report.
- If you get a message that starts with `TIME UP`, stop at once and report with `STATUS: timeout-partial` and whatever you measured so far.

## Measurement

Metric: {{METRIC}}. Measure only with this command (Bash timeout ≥ {{R}} × ({{RUN_TIMEOUT}} + 30) s):

```
bash {{MEASURE_SH}} <dir> {{R}} {{RUN_TIMEOUT}} {{MODE}} {{LOCK}} '{{MEASURE_CMD}}'
```

It prints one value per run, or `TIMEOUT` / `FAIL <code>`.

## Steps

1. **Base:** measure `{{WT}}` before you change anything.
2. **Implement** the idea with the smallest change that does it. Do not change the measurement command, the correctness command, test inputs or reference outputs. Do not game the metric (caching results across runs, skipping required work, special-casing the benchmark input). If the idea turns out not to apply, report `STATUS: failed` with the reason. Do not substitute a different idea.
3. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise report `CORRECTNESS: fail`.
4. **Commit** exactly one commit. First check `git -C {{WT}} diff --stat`: if it shows whole files changed where you edited a few lines, your editor changed line endings or encoding. Restore the original ones, because whole-file diffs make the later migration conflict. Then: `git -C {{WT}} add -A && git -C {{WT}} commit -m "opt({{ID}}): <one-line change>"`.
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
BASE_RUNS: <values, unit>
CANDIDATE_RUNS: <values, unit>
RATIO: <improvement factor; >1 means better: base/candidate when lower is better, candidate/base when higher is better>
NOTES: <risks, side effects, what you could not finish>
```
