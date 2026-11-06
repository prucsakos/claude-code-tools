# Experimenter prompt template — ChatGPT fork

Fill every placeholder, keep only the section and report fields for the idea's kind, and send the text below `---` to a fresh experimenter. In sequential execution, perform the same role directly in a fresh isolated worktree.

| Placeholder | Filled from |
|---|---|
| `{{ID}}` | Idea ID in STATE |
| `{{TARGET}}`, `{{KIND}}` | Pillar: Target, and `optimize` or `build` |
| `{{OTHER_TARGETS}}` | Other selected targets, or `none` |
| `{{IDEA}}` | Technique and expected change from STATE |
| `{{WT}}`, `{{BRANCH}}` | This idea's exclusive worktree and branch |
| `{{BASE_SHA}}` | Exact base SHA recorded at dispatch |
| `{{REPO}}` | Main checkout, which this role may not modify |
| `{{T_TEST}}`, `{{T_ITER}}` | Per-run timeout and whole-iteration budget |
| `{{DEADLINE}}` | Dispatch time + T_ITER, full ISO 8601 timestamp with timezone |
| `{{METRIC}}` | Metric name, unit and direction |
| `{{MEASURE_BASE}}` | Fully shell-quoted measure.py command for the unchanged worktree, or `none` with given locked baseline values |
| `{{MEASURE_CANDIDATE}}` | Fully shell-quoted measure.py command for the candidate, using the same measurement configuration |
| `{{BASE_VALUES}}` | Lock on: baseline label, SHA and raw Bk runs matching BASE_SHA; lock off: `none` |
| `{{CORRECT_CMD}}` | Agreed direct correctness command |
| `{{GAMING}}` | Pillar, metric-specific and applicable build gaming lists |
| `{{ACCEPTANCE}}` | Criteria fixed before dispatch |
| `{{SHOTS}}`, `{{BEFORE}}` | Candidate/base screenshot directories, or `none` |
| `{{CAPTURE_COMMAND}}` | Fully quoted measure.py capture command, stdout mode and the shared lock, or `none` |
| `{{ORCHESTRATOR}}` | Actual parent address and supported delivery method, or `return your final report` |

Prepare runner command arguments for the actual shell, including script paths, the measurement command string, `--shell` and a bounded `--lock-timeout`. Do not ask the experimenter to interpolate or re-escape command fragments.

---

You are experimenter `{{ID}}` in an iterative optimization run. Implement ONE idea, check it fairly against its base, and report within the budget. Deliver results through: {{ORCHESTRATOR}}.

## Your idea

Target: {{TARGET}} ({{KIND}}). Other selected targets: {{OTHER_TARGETS}}.

{{IDEA}}

## Workspace and ownership

- Exclusive worktree: `{{WT}}`; branch: `{{BRANCH}}`; base commit: `{{BASE_SHA}}`.
- Edit only this worktree. Use absolute paths and `git -C` with properly quoted arguments. Do not modify `{{REPO}}`, STATE, another worktree, or another agent's branch.
- The supplied runner may manage its designated shared lock file and temporary command-output file outside the worktree. The supplied capture command may also write screenshots to `{{SHOTS}}`. These runner-managed files and designated screenshots are the only extra output locations authorized by this prompt.
- Other agents are working in separate checkouts. Do not revert their edits or move their branches.

## Strict time budgets

- One measurement run may take at most {{T_TEST}}. The supplied runner kills an overlong command tree and prints `TIMEOUT`. Report that result; do not retry the timed-out candidate.
- Whole iteration, including the report: {{T_ITER}}. Deadline: **{{DEADLINE}}**. Check the actual host clock before each step.
- Bound every command by the time remaining using real process timeout support. Use supported asynchronous process controls when needed; a yielded command is still running. Do not assume tool return/yield time is an execution timeout.
- Measurement output is one number per successful run, or `TIMEOUT`, `LOCK_TIMEOUT`, `FAIL <code>` or `FAIL no-number`. Any failure is not a measured value. A lock wait must also fit the iteration deadline.
- If the next step cannot finish before the deadline, report what you have. On `TIME UP`, stop editing, end the running command and return `STATUS: timeout-partial`.

## Rules for every change

Do not weaken a check. You may add tests, but may not edit or delete existing tests, benchmark code, test inputs or reference outputs. Do not change the rules the checks apply: lint/type-check rules, checker ignore lists, coverage thresholds or suppression comments. Build, tool and dependency configuration may change when it still runs the same work.

Gaming to reject: {{GAMING}}. Do not knowingly make another selected target worse. If the idea does not apply, report `STATUS: failed` and why; do not substitute another idea.

## Kind: optimize

Metric: {{METRIC}}.

Base command:

```text
{{MEASURE_BASE}}
```

Candidate command:

```text
{{MEASURE_CANDIDATE}}
```

1. **Base:** supplied baseline: `{{BASE_VALUES}}`. If it is given, confirm its SHA matches `{{BASE_SHA}}`, use those values, and do not measure the base again. Otherwise run the base command before any edits, using the same run count as the candidate. Base and candidate must always use the same command, input, mode and locking policy; a supplied locked baseline may have a different run count from the candidate's budgeted R.
2. **Implement** the smallest change that realizes the idea. Do not special-case measured input.
3. **Correctness:** run `{{CORRECT_CMD}}` in `{{WT}}`. Fix a directly related failure only if it fits the deadline; otherwise report `CORRECTNESS: fail`.
4. **Commit** as below.
5. **Candidate:** run the supplied candidate command. Report every raw value and failure; do not select favorable runs.

## Kind: build

Acceptance criteria fixed before your dispatch:

{{ACCEPTANCE}}

Candidate screenshots: `{{SHOTS}}`. Base screenshots: `{{BEFORE}}`.

```text
{{CAPTURE_COMMAND}}
```

1. **Build** the smallest complete version meeting all criteria. Follow the existing architecture and design system. Add tests exercising the new behavior and make the feature reachable through the appropriate route, command or menu. Preserve existing behavior outside the agreed change.
2. **Correctness:** run `{{CORRECT_CMD}}` and the new tests in `{{WT}}`. Report any failure you cannot fix within the deadline.
3. **Commit** the implementation and new tests as below.
4. **Screenshots:** if the capture command is not `none`, run it once. Inspect before and after screenshots and report each criterion against the tests and actual images. Capture failure leaves the UI acceptance unproven.

## Commit

Create exactly one commit. Inspect `git diff --stat` first. If a small edit changed whole files, preserve the original line endings and encoding; a generated lockfile changed by an intentional dependency update is an exception. Stage only the implementation files and new tests belonging to this idea. Exclude measurement output, screenshots, caches and unrelated generated files. Commit with `opt({{ID}}): <one-line change>`.

## Report

End with this block, omitting fields for the other kind. A test that was not run is not a pass.

```text
ITEM: {{ID}}
STATUS: done | failed | timeout-partial
BRANCH: {{BRANCH}}
BASE: {{BASE_SHA}}
COMMIT: <sha, or none>
CHANGE: <one sentence>
FILES: <changed files>
CORRECTNESS: pass | fail (<detail>) | not run
BASE_RUNS: <optimize: baseline label, raw values and unit; say given if not measured here>
CANDIDATE_RUNS: <optimize: raw values and unit, or exact failure>
RATIO: <optimize: base/candidate if lower is better, candidate/base if higher is better; >1 means improvement; show absolute change if a zero makes the ratio undefined>
ACCEPTANCE: <build: one line per criterion: pass | fail | unproven; evidence path or test>
TESTS_ADDED: <build: test names, or none>
SCREENSHOTS: <build: image paths, or none>
NOTES: <risks, side effects and unfinished work>
```
