# Execution details

Read this before executing a run. It complements SKILL.md; it does not grant extra authorization.

## Setup and measurement budgets

Record REPO's resolved path, clean status, current branch and starting SHA. Do not switch branches, stash, discard or overwrite the user's uncommitted work. While a run is active, ask the user to avoid editing MAIN; unexpected edits block integration, not independent experiments.

Use a fresh sibling directory, such as `<repo>.optimize/<run-id>/`, as RUN_DIR. Never reuse another run's state, worktrees or locks. Record exact paths and branch names in STATE. Keep the harness independent of candidate changes.

Create `RUN_DIR/wt/measure` detached from MAIN and a detached `RUN_DIR/wt/researcher-<pillar>` for each active researcher with `git -C REPO worktree add --detach <path> MAIN`. Run SETUP_CMD in every fresh worktree; tracked files alone may not include required dependencies or data. Read-only researchers inspect their own checkout; do not move the measuring worktree underneath them.

### Canonical measurement runner

All baseline/candidate measurements, resource-intensive profiles and UI captures use the bundled Python runner:

```text
python /absolute/skill/scripts/measure.py WORKDIR RUNS TIMEOUT_SECONDS MODE LOCKFILE COMMAND [--shell SHELL] [--lock-timeout SECONDS]
```

Resolve the actual Python executable (`python`, `python3` or equivalent). MODE is `time` (wall seconds) or `stdout` (last finite numeric value). SHELL is `auto`, `bash`, `sh`, `powershell`, `pwsh` or `cmd`; select and record it once for the run. Auto uses PowerShell on Windows and sh on POSIX. Shell selection and setup must match the project's commands. The whole COMMAND is intentional shell code, passed as **one argument** to the runner; quote paths and arguments for both the outer and selected inner shell. Prefer a small external harness file over complex nested quoting. Never interpolate untrusted text into commands.

The runner prints one number per successful run. `TIMEOUT`, `LOCK_TIMEOUT`, `FAIL <exit>` or `FAIL no-number` is failure, never a metric. Failure stops repetitions and returns nonzero. Diagnostics remain on stderr. The measurement timeout covers each command; lock acquisition has its own bounded timeout. Supply `--lock-timeout` from the remaining iteration budget, leaving room for R runs, correctness and the final report. The runner serializes commands with an OS advisory lock and does not delete the shared lock file. A file remaining on disk is not proof that the lock is held.

`stdout` metrics must print the intended scalar last, without trailing unrelated numbers. For count tools that normally exit nonzero on findings, use a harness that parses their structured output, distinguishes findings from execution/parse errors, prints the count and exits 0 **only after a successful scan**. Do not mask failures with a blanket `|| true`, unchecked pipeline or an unconditional counter exit. Keep benchmark input and correctness references fixed outside candidate worktrees.

Run CORRECT_CMD in the measurement checkout before B0; it must pass. Measure each optimize target three times for B0, recording values, median, spread and elapsed runtime. In stdout mode, time the complete call and divide by its run count for a conservative runtime estimate. If UI targets exist, run EVIDENCE_CMD once through the runner (`stdout`, shared lock), inspect the images and record capture time `ev`. EVIDENCE_CMD must clean up its app/server, including on failure. A screenshot count alone is insufficient evidence.

### Repetitions and concurrency

Let `run` be a target's median command runtime; budgets below are seconds:

- Lock on: experimenters measure only the candidate and receive base Bk runs measured under the same shared lock. S = 1 side.
- Lock off: experimenters measure both base and candidate in their own worktree. S = 2 sides.
- For a locked track, L is the simultaneous experimenter allocation of all pillars with locked tracks or UI build items, plus their active researchers. Count actual host capacity, not requested profile capacity. For an unlocked track, L = 1.
- `R = clamp(min(floor(T_TEST / run), floor(T_ITER / (2 * S * L * run))), 1, 5)`. In the second term, use the longest runtime among all locked tracks and UI capture time `ev` when relevant. Keep enough time for editing, correctness, lock wait and reporting.
- If all three B0 values are equal, treat the metric as provisionally deterministic: R = 1 and spread = 0. Revisit if later samples vary.
- Before clamping to 1, check feasibility: if `2 * S * L * run > T_ITER`, reduce simultaneous workers for the affected pillars and recompute. If one worker still cannot fit, report that track blocked by the budget; do not fake a feasible R. Changing the test or iteration budget needs existing authorization or a user decision.
- At most `floor(T_ITER / (2 * ev))` simultaneous experimenters may perform UI builds. If that is zero, report the evidence-budget problem. Redistribute unused slots to other pillars where feasible; otherwise reduce effective N.

When moving slots, never increase total N, exceed host limits or invalidate a locked/UI track's measurement budget. An idle pillar may lend slots to an unlocked non-UI pillar. Return its confirmed share as borrowed tasks finish. To increase a locked/UI pillar's share, recompute its lock/capture budget first and report the adjustment.

## Dispatch and queues

Before each experiment, record current MAIN's SHA and baseline Bk. Create a fresh branch/worktree with `git -C REPO worktree add -b opt/<run-id>/<idea-id> <owned-path> MAIN`, then SETUP_CMD. Give the role one idea, its target/kind, other targets, fixed command/criteria, gaming rules and deadline. Use a fresh worker for each idea; sequential mode uses a fresh role context/worktree with the same inputs.

For locked optimize targets, supplied Bk must correspond to BASE_SHA. For unlocked targets, the experimenter measures base before edits and candidate with the same command afterward. Store baseline identity and raw runs with the result. Send complete prequoted runner commands in the role placeholders; do not ask workers to reconstruct escaping.

A researcher uses its detached checkout, current baseline and history. Refresh the checkout to current MAIN only between research rounds, rerunning SETUP_CMD if MAIN changed. Research is read-only except for profiling/evidence output in its assigned external directory. With a locked target, allow at most one locked profile per research round; never profile beside another timed run. Researchers send each idea promptly through real messaging when supported; otherwise consume their final idea list. They do not create code commits.

Relative expected gain is `expected improvement / base value`; build value and confidence use high=1, medium=0.6, low=0.3. Handle a zero baseline with an explicit absolute improvement or consider that target satisfied; do not divide by zero. Deduplicate ideas across pillars, including differently worded changes to the same code for the same gain.

Do not split an idea merely because a researcher predicts a long task. Split an actual timeout into independently useful, testable increments; queue the first and record later increments. If an authorized finite user item is clearly larger than T_ITER during setup, propose its increments before dispatch. A successor enters the queue only when its predecessor reaches MAIN.

## Deadlines and events

Record dispatch time, deadline, real worker/process handles and whether the host supports cancellation. The clock and deadline use the same time zone. Enforce individual process deadlines; a message cannot interrupt a blocked shell. Time spent preparing a fresh worktree must fit the overall scheduling budget.

Use completion events or bounded waits and check the nearest deadline before waiting. A yielded shell session or interim worker message is not a completed report. At T_ITER (research: T_RESEARCH), send `TIME UP: stop editing, end the current command and report what you have`. Allow grace `G = min(120, max(30, T_ITER/5))` seconds for a report and cleanup. At grace expiry, cancel the actual role and its owned commands, mark timeout and verify they stopped before removing the worktree. A command timeout stops its measurement without automatic retry.

If the host cannot enforce whole-role deadlines/cancellation, use sequential execution with bounded commands and clock checks; disclose this limitation. Do not launch an unattended worker you cannot stop within the agreed budget. A timeout-partial result can be accepted only if its complete commit and all required evidence already exist; otherwise reject it and consider a split.

After each event, update STATE, decide results, integrate when appropriate, refill free slots and check idle/exhaustion. User input changes new dispatches; changes to metric, command, harness, input or environment invalidate comparability. Establish a new baseline series and retest affected results rather than mixing incompatible numbers. A user stop takes precedence over dispatching more work.

## Integration and regressions

Inspect `git diff BASE_SHA..IDEA_BRANCH`, changed checks/configuration and actual evidence before accepting. New tests are allowed; editing/deleting existing tests or altering the measured benchmark to improve the score is not. Compare medians and run-to-run spread on both sides, with risk proportional to the diff. Keep criterion-by-criterion evidence for builds. Record the reason for every decision.

An accepted result from an older MAIN remains tied to its original base. Do not label its gain as measured on current MAIN. If subsequent changes overlap its implementation or materially affect correctness/metric comparability, retest it from current MAIN before integrating; otherwise final combined remeasurement still decides whether it stays.

Create one run-owned batch branch/worktree from current MAIN. In review mode, first hold a concrete approved item list with evidence/diff sizes; new acceptances wait for the next batch. Cherry-pick one accepted commit at a time. Resolve conflicts only when both changes' intent is clear; regenerate conflicting lockfiles with the package manager. Abort an unresolvable cherry-pick and mark that item skipped. Rerun SETUP_CMD after dependency changes, then CORRECT_CMD per item and once on the whole batch. Discard a failed item only in the owned batch worktree; never reset the main checkout. If skipped items are prerequisites, leave their dependent increments blocked.

Before fast-forward, verify REPO still has MAIN checked out, is clean and can fast-forward. If the user or another process moved/edited it, stop integration and report the external blocker while other isolated experiments may continue. Never force, reset or rebase MAIN. Only the integrator runs `git -C REPO merge --ff-only BATCH_BRANCH`.

Refresh the detached measuring checkout to MAIN and rerun SETUP_CMD. Measure every optimize target into Bk (three repetitions if all target measurements fit T_ITER; otherwise the target's R), run CORRECT_CMD and refresh/inspect UI evidence. Never publish a claimed successful batch before these checks.

If any optimize target is worse beyond noise, attribute the regression by measuring the batch's commits in the measuring checkout. If correctness fails, use the failing checks to identify the cause. Revert offending commits newest first through an integrator revert batch, preserving dependent behavior and checking correctness. Remeasure **all** targets after the revert too; the recovered state becomes the next baseline. Requeue affected ideas as retest with the regression reason. If attribution or reverting is blocked, stop further integration, retain the evidence and clearly report the unresolved MAIN regression.

If combined gain is less than the product of item ratios, note overlapping gains; only a real regression requires reversal. A build target is done when its finite list or authorized cap is reached. After a changed valid MAIN baseline, clear exhausted research and reconsider within-noise ideas and unsplittable timeouts once per new baseline, with a distinct retest record.

### Publishing, when authorized

Record the remote, original BASE branch, run MAIN branch and publishing authorization before creating a PR. Find the branch's upstream remote, otherwise origin. Verify authentication and access through the available GitHub tool or git/gh; do not treat a read-only connection or a dry run as permission to publish.

After successful post-batch checks (including necessary reverts), regenerate `RUN_DIR/patchnote.md` from STATE: surviving changes by batch, each target/result/baseline, reversions and reasons, B0 versus current measurements, acceptance evidence and counts. Push the run branch and create or update its PR into BASE with the available connector or git/gh. Prefer structured tool bodies; with gh, use `--body-file` pointing at the actual multiline file. Store the PR URL. A publication error does not erase local results: report it, continue authorized local work and retry at the next publishing event. Never merge the PR without separate authorization.

## Shutdown

On explicit stop or budget expiry, stop new work and cancel active research/experiments and their commands. Auto may integrate already accepted items as a final verified batch if the stop instruction and remaining authorized budget allow it. Review holds those items for approval. An immediate stop forbids a final migration. Verify any already-started integration's actual git outcome before reporting.

Before recursive cleanup, resolve the paths and verify that they are exact recorded children of this run's RUN_DIR, are registered worktrees of REPO, and no role/process still uses them. Remove owned worktrees with `git -C REPO worktree remove --force PATH` only after their results are recorded. Delete only this run's rejected/superseded/migrated temporary branches; accepted unmigrated branches survive. Cherry-picked branches may require `git branch -D`; use it only on these verified run-owned branches. Never glob-delete other `opt/*` branches or unrelated files. Keep the PR's run branch, STATE and evidence.

If publishing is enabled, push the final verified run branch and update the patch note/PR, recording failures. The final report includes actual measurements with named baselines, correctness/acceptance results, unfinished/blocked tracks, retained branches and the PR URL. If the host cannot continue, save a checkpoint and report that execution has ended; do not claim ongoing unattended optimization.
