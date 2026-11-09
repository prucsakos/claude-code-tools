# Experimenter prompt template

| Placeholder | Filled from |
|---|---|
| `{{ID}}` | The idea's id in STATE |
| `{{TARGET}}` | The idea's target, as `<Pillar>: <Target>` |
| `{{KIND}}` | The target's kind: `optimize`, `build` or `judged` |
| `{{OTHER_TARGETS}}` | The other selected targets, or `none` |
| `{{IDEA}}` | The idea's technique and expected change, from STATE |
| `{{WT}}` | `RUN_DIR/wt/<id>` (section 2, Dispatch an experimenter) |
| `{{BRANCH}}` | `opt/<id>` |
| `{{BASE_SHA}}` | The base SHA recorded in STATE at dispatch |
| `{{REPO}}` | Form input REPO |
| `{{T_TEST}}`, `{{T_ITER}}` | Form input T_TEST;T_ITER |
| `{{T_TEST_SECONDS}}` | T_TEST in seconds |
| `{{DEADLINE}}` | Dispatch time + T_ITER, as HH:MM:SS |
| `{{METRIC}}` | Form input Metric of the target: name, unit, direction |
| `{{MEASURE_SH}}` | Absolute path of `measure.sh` in this skill's directory |
| `{{R}}` | Runs per side of the target (setup step 4) |
| `{{MODE}}` | The target's mode: `time` or `stdout` |
| `{{LOCK}}` | The target's LOCK (setup step 2); for a UI build item, `RUN_DIR/measure.lock` |
| `{{MEASURE_CMD}}` | Form input MEASURE_CMD of the target, each `'` written as `'\''` |
| `{{BASE_VALUES}}` | Lock on: the target's runs of the current Bk; lock off: `none` |
| `{{CORRECT_CMD}}` | Form input CORRECT_CMD |
| `{{GAMING}}` | Section 2, Dispatch an experimenter |
| `{{ACCEPTANCE}}` | The idea's acceptance criteria, from STATE |
| `{{RUBRIC}}` | The idea's rubric criteria, from STATE |
| `{{SHOTS}}` | UI item: `RUN_DIR/shots/<id>`; otherwise `none` |
| `{{BEFORE}}` | UI item: `RUN_DIR/shots/Bk` of the current baseline; otherwise `none` |
| `{{EVIDENCE_CMD}}` | Form input EVIDENCE_CMD |

Keep the section for the idea's kind (optimize, build or judged) and the report fields of that kind.

---

You are experimenter `{{ID}}` in a parallel optimization run. Implement ONE idea, check it fairly against its base, and report. You have a strict time budget.

## Your idea

Target: {{TARGET}} ({{KIND}}). Other selected targets: {{OTHER_TARGETS}}.

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

## Rules for every change

Do not weaken a check. You may add new tests, but do not edit or delete existing tests. Do not change the benchmark code that the measurement runs, test inputs, or reference outputs. Do not change the rules the checks apply (lint and type-check rules, checker ignore lists, coverage thresholds, suppression comments). Build, tool and dependency configuration may change when the same work still runs. Do not game the result: none of these: {{GAMING}}. Do not knowingly make the other selected targets worse. If the idea turns out not to apply, report `STATUS: failed` with the reason. Do not substitute a different idea.

## Kind: optimize

Metric: {{METRIC}}. Measure the base and the candidate only with this command:

```
bash {{MEASURE_SH}} <dir> {{R}} {{T_TEST_SECONDS}} {{MODE}} {{LOCK}} '{{MEASURE_CMD}}'
```

It prints one value per run, or `TIMEOUT` / `FAIL <code>`. With a lock, it first waits until no other measurement runs.

1. **Base:** given base values: `{{BASE_VALUES}}`. If they are given (not `none`), use them and do not measure the base. Otherwise measure `{{WT}}` before you change anything.
2. **Implement** the idea with the smallest change that does it. No special-casing of the measured input.
3. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise report `CORRECTNESS: fail`.
4. **Commit** (see Commit).
5. **Candidate:** measure `{{WT}}` again with the same command.

## Kind: build

Acceptance criteria, fixed before you started; report on each one:

{{ACCEPTANCE}}

Screenshots: `{{SHOTS}}`. If it is not `none`, the screenshots of your base are in `{{BEFORE}}`, and you capture yours once, only with `bash {{MEASURE_SH}} {{WT}} 1 {{T_TEST_SECONDS}} stdout {{LOCK}} '{{EVIDENCE_CMD}} {{SHOTS}}'`. It prints the number of screenshots, or `TIMEOUT` / `FAIL <code>`.

1. **Build** the smallest complete version of the idea that meets every criterion. Follow the existing architecture and design system. Add tests that exercise the new behavior; make the feature reachable by its users (route, command or menu entry). Keep the existing behavior unchanged.
2. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`, then your new tests. If they fail and the fix is quick, fix it; otherwise report the failure.
3. **Commit** (see Commit). Your new tests go into the commit.
4. **Screenshots:** if there are screenshots, capture them and compare them with `{{BEFORE}}`. Check each criterion against the tests and screenshots.

## Kind: judged

Rubric criteria, fixed before you started. The orchestrator judges your change against each one:

{{RUBRIC}}

1. **Change** the work with the smallest complete version of the idea. Follow the existing structure and style. Keep the existing behavior unchanged.
2. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise report the failure.
3. **Commit** (see Commit).
4. **Evidence:** for each rubric criterion, collect before/after evidence from the committed diff (`git -C {{WT}} show HEAD`): quotes of the old and new text with `file:line`, and for each source you used, its URL and the passage you quote from it. Report the evidence only. Never state whether a criterion is met: the orchestrator judges that, not you.

## Commit

Commit exactly one commit. First check `git -C {{WT}} diff --stat`: if it shows whole files changed where you edited a few lines, your editor changed line endings or encoding. Restore the original ones, because whole-file diffs make the later migration conflict. A generated lockfile is the exception: a dependency change can rewrite large parts of it. Stage only the files you changed for the idea; `git -C {{WT}} status --porcelain` shows measurement output, caches and other generated files, which stay out of the commit. Then: `git -C {{WT}} add <files> && git -C {{WT}} commit -m "opt({{ID}}): <one-line change>"`.

## Report

End with exactly this block and nothing after it. Leave out the fields of the other kinds.

```
ITEM: {{ID}}
STATUS: done | failed | timeout-partial
BRANCH: {{BRANCH}}
BASE: {{BASE_SHA}}
COMMIT: <sha, or none>
CHANGE: <one sentence>
FILES: <changed files>
SIDE_EFFECTS: <each file, public interface, default, dependency or behavior the commit changes beyond what the idea names, with why; or none>
CORRECTNESS: pass | fail (<detail>) | not run
BASE_RUNS: <optimize: values, unit; say "given" if you did not measure them>
CANDIDATE_RUNS: <optimize: values, unit>
RATIO: <optimize: improvement factor; >1 means better: base/candidate when lower is better, candidate/base when higher is better; if a lower-is-better candidate is 0, write "n/a (<base> → 0)">
ACCEPTANCE: <build: one line per criterion: pass | fail — the test or screenshot that shows it>
TESTS_ADDED: <build: test names, or none>
SCREENSHOTS: <build: path of your screenshots, or none>
RUBRIC_EVIDENCE: <judged: one line per criterion: the criterion, then before → after evidence; no verdict>
SOURCES: <judged: URL and quoted passage of each source you used, or none>
NOTES: <risks, side effects, what you could not finish>
```
