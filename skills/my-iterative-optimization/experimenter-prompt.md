# Experimenter prompt template

| Placeholder | Filled from |
|---|---|
| `{{ID}}` | The idea's id in STATE |
| `{{RUN}}` | The run's start time from STATE config, as `YYYYMMDD-HHMM` |
| `{{TARGET}}` | The idea's target, as `<Pillar>: <Target>` |
| `{{KIND}}` | The target's kind: `optimize`, `build` or `judged` |
| `{{OTHER_TARGETS}}` | The other selected targets, or `none` |
| `{{IDEA}}` | The idea's technique, expected change and prediction, from STATE |
| `{{WT}}` | `RUN_DIR/wt/<id>` (section 2, Dispatch an experimenter) |
| `{{BRANCH}}` | `opt/<id>` |
| `{{BASE_SHA}}` | The base SHA recorded in STATE at dispatch |
| `{{REPO}}` | Plan input REPO |
| `{{T_TEST}}`, `{{T_ITER}}` | Plan input T_TEST;T_ITER |
| `{{T_TEST_SECONDS}}` | T_TEST in seconds |
| `{{DEADLINE}}` | Dispatch time + T_ITER, as HH:MM:SS |
| `{{METRIC}}` | Plan input Metric of the target: name, unit, direction |
| `{{MEASURE_SH}}` | Absolute path of `measure.sh` in this skill's directory |
| `{{R}}` | Runs per side of the target (setup step 4) |
| `{{MODE}}` | The target's mode: `time` or `stdout` |
| `{{LOCK}}` | The target's LOCK (setup step 2); for a UI build item, `RUN_DIR/measure.lock` |
| `{{MEASURE_CMD}}` | Plan input MEASURE_CMD of the target, each `'` written as `'\''` |
| `{{BASE_VALUES}}` | Lock on: the target's runs of the current Bk; lock off: `none` |
| `{{OUTPUT_CHECK}}` | Section 2, Dispatch an experimenter |
| `{{CORRECT_CMD}}` | Plan input CORRECT_CMD |
| `{{GAMING}}` | Section 2, Dispatch an experimenter |
| `{{ACCEPTANCE}}` | The idea's acceptance criteria, from STATE |
| `{{EVIDENCE_FORM}}` | The build target's evidence form, from the plan |
| `{{RUBRIC}}` | The idea's rubric criteria, from STATE |
| `{{SHOTS}}` | UI item: `RUN_DIR/shots/<id>`; otherwise `none` |
| `{{BEFORE}}` | UI item: `RUN_DIR/shots/Bk` of the current baseline; otherwise `none` |
| `{{EVIDENCE_CMD}}` | Plan input EVIDENCE_CMD |

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
- Before each step, check the clock. If the next step cannot finish before the deadline, skip to the report with `STATUS: timeout-partial`.
- If you get a message that starts with `TIME UP`, stop at once and report with `STATUS: timeout-partial` and whatever you measured so far.

## Rules for every change

Do not weaken a check: new tests are fine, but never edit or delete existing tests. Do not change the benchmark code the measurement runs, test inputs, reference outputs or check rules (lint and type-check rules, ignore lists, coverage thresholds, suppression comments). Build, tool and dependency configuration may change when the same work still runs. Do not game the result: {{GAMING}}. Do not knowingly worsen other selected targets. If the idea does not apply, report `STATUS: failed` with the reason; do not substitute another idea.

## Kind: optimize

Metric: {{METRIC}}. Measure the base and the candidate only with this command:

```
bash {{MEASURE_SH}} <dir> {{R}} {{T_TEST_SECONDS}} {{MODE}} {{LOCK}} '{{MEASURE_CMD}}'
```

It prints one value per run, or `TIMEOUT` / `FAIL <code>`. With a lock, it first waits until no other measurement runs.

1. **Base:** given base values: `{{BASE_VALUES}}`. If they are given (not `none`), use them and do not measure the base. Otherwise measure `{{WT}}` before you change anything.
2. **Implement** the idea with the smallest change that does it. No special-casing of the measured input.
3. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise skip the remaining steps and report `STATUS: failed` with `CORRECTNESS: fail (<detail>)`. Then the output check: `{{OUTPUT_CHECK}}`. If it is not `none`, after the commit (step 4) run its command on your commit and on the base, each into its own new folder outside `{{WT}}`. Run it with `bash {{MEASURE_SH}} {{WT}} 1 {{T_TEST_SECONDS}} time {{LOCK}} '<command> <folder>'`. For the base run, first `git -C {{WT}} checkout --detach {{BASE_SHA}}`, and afterwards `git -C {{WT}} checkout {{BRANCH}}`. Compare the two folders by its rule and report the result as `OUTPUT_DIFF`.
4. **Commit** (see Commit).
5. **Candidate:** measure `{{WT}}` again with the same command.

## Kind: build

Acceptance criteria, fixed before you started; report on each one:

{{ACCEPTANCE}}

Evidence form: {{EVIDENCE_FORM}}.

Screenshots: `{{SHOTS}}`. If it is not `none`, the screenshots of your base are in `{{BEFORE}}`, and you capture yours once, only with `bash {{MEASURE_SH}} {{WT}} 1 {{T_TEST_SECONDS}} stdout {{LOCK}} '{{EVIDENCE_CMD}} {{SHOTS}}'`. It prints the number of screenshots, or `TIMEOUT` / `FAIL <code>`.

1. **Build** the smallest complete version of the idea that meets every criterion. Follow the existing architecture and design system. When the evidence form includes tests, add tests that exercise the new behavior; otherwise add no test files and produce the evidence the form names. Make the feature reachable by its users (route, command or menu entry). Keep the existing behavior unchanged.
2. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`, then your new tests, if you added any. If they fail and the fix is quick, fix it; otherwise skip the remaining steps and report `STATUS: failed` with `CORRECTNESS: fail (<detail>)`.
3. **Commit** (see Commit). Your new tests, if any, go into the commit.
4. **Check:** if there are screenshots, capture them and compare them with `{{BEFORE}}`. Then re-read each criterion and check it against the committed diff (`git -C {{WT}} show HEAD`), the test output and the screenshots, not against your memory of the edit. For each criterion, name evidence the orchestrator can re-check: a test name with its output line, a screenshot path, or a `file:line` quote from the commit. Report the evidence only; do not state whether a criterion is met.

## Kind: judged

Rubric criteria, fixed before you started. The orchestrator judges your change against each one:

{{RUBRIC}}

1. **Change** the work with the smallest complete version of the idea. Follow the existing structure and style. Keep the existing behavior unchanged.
2. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. If it fails and the fix is quick, fix it; otherwise skip the remaining steps and report `STATUS: failed` with `CORRECTNESS: fail (<detail>)`.
3. **Commit** (see Commit).
4. **Evidence:** for each rubric criterion, collect before/after evidence from the committed diff (`git -C {{WT}} show HEAD`): quotes of the old and new text with `file:line`, and for each source you used, its URL and the passage you quote from it. Report the evidence only. Never state whether a criterion is met: the orchestrator judges that, not you.

## Commit

First compare `git -C {{WT}} diff --stat` with `git -C {{WT}} diff --stat --ignore-cr-at-eol`: many more changed lines for a file in the first mean your editor changed line endings. Check the base file: `git -C {{WT}} show HEAD:<file> | grep -c -U $'\r'` prints 0 for LF, its line count for CRLF (`-U` keeps CRs on Windows). Restore CRLF with `sed -i 's/\r*$/\r/' {{WT}}/<file>` or LF with `sed -i 's/\r$//' {{WT}}/<file>` and recheck: whole-file diffs make the later migration conflict. If both still show whole files changed, restore the encoding, unless a dependency change rewrote a generated lockfile. Stage only the idea's files, not measurement output, caches or other generated files `git -C {{WT}} status --porcelain` shows. Then commit once: `git -C {{WT}} add <files> && git -C {{WT}} commit -m "opt({{ID}}): <one-line change>" --trailer "Optimize-Run: {{RUN}}" --trailer "Target: {{TARGET}}"`.

## Report

End with exactly this block and nothing after it. Leave out the fields of the other kinds.

```
ITEM: {{ID}}
STATUS: done | failed | timeout-partial
BRANCH: {{BRANCH}}
BASE: {{BASE_SHA}}
COMMIT: <sha, or none>
PROBLEM: <one sentence: what was wrong or missing before, for a reviewer who never saw the run>
CHANGE: <one sentence>
PREDICTION: held | failed | not checked — <what you saw>
FILES: <changed files>
SIDE_EFFECTS: <each file, public interface, default, dependency or behavior the commit changes beyond what the idea names, with why; or none>
CORRECTNESS: pass | fail (<detail>) | not run
BASE_RUNS: <optimize: values, unit; say "given" if you did not measure them>
CANDIDATE_RUNS: <optimize: values, unit>
RATIO: <optimize: improvement factor; >1 means better: base/candidate when lower is better, candidate/base when higher is better; if a lower-is-better candidate is 0, write "n/a (<base> → 0)">
OUTPUT_DIFF: same | within tolerance <value> | differs <first difference> | none — optimize: the output check result, `none` when the target has none
ACCEPTANCE: <build: one line per criterion: the criterion, then its evidence: test name and output line, screenshot path, or file:line quote; no verdict>
TESTS_ADDED: <build: test names, or none>
SCREENSHOTS: <build: path of your screenshots, or none>
NEW_CASE: <build: a repo path or command, never invented, on which the item or MAIN failed or behaved wrong and that no acceptance criterion names, with what happened; or none>
RUBRIC_EVIDENCE: <judged: one line per criterion: the criterion, then before → after evidence; no verdict>
SOURCES: <judged: URL and quoted passage of each source you used, or none>
NOT_CHECKED: <claims in CHANGE or ACCEPTANCE you did not verify, cases you did not run, or none>
VERIFY: <one command or file:line a reviewer can check on the PR>
RISK: <what could go wrong after merge, or none>
BEHAVIOR: <what a user of the changed product sees or must do differently after merge (command, flag, default, output format, file path), or none>
NOTES: <risks, side effects, what you could not finish>
```
