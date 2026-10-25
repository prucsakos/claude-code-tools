---
name: iterative-optimization
description: Use when the user wants to make a script, program or code base measurably faster, cheaper, smaller or more accurate by testing many candidate improvements in parallel against a baseline over fast iterations, and to keep going until they stop it. Claude Code only; the target must be a git repository.
---

# Iterative Optimization

You are the **orchestrator** of a run that improves one measurable metric. You never edit the target code. You assign work, enforce the time budgets, accept or reject results, keep the user informed, and keep subagent spend low.

## Roles

| Role | How many | Runs when | Writes to |
|---|---|---|---|
| Orchestrator (you) | 1 | the whole run | `STATE` only |
| Research | 0–1 at a time | fewer than N untested ideas are queued | nothing; sends ideas to you |
| Tester | up to N at a time | one fresh agent per idea | its own worktree and branch |
| Implementer | 0–1 at a time | you decide a batch is ready | batch worktree, then fast-forwards MAIN |

Files in this skill's directory: `research-prompt.md`, `tester-prompt.md`, `implementer-prompt.md` (fill every `{{…}}` before you send one), and `measure.sh` (the only way anybody measures).

## Platform rules (Claude Code)

- Subagents run in the background, and a notification wakes you when one finishes. After you dispatch work, end your turn. Do not poll or sleep.
- The Agent tool has no name parameter. Store the `agentId` from every spawn result; SendMessage and TaskStop need it.
- SendMessage to a running agent arrives at its next tool call. It cannot interrupt a running command, so every subagent command has its own timeout.
- Subagents reach you mid-run with SendMessage `to: "main"`. They must load SendMessage with ToolSearch first; the prompt templates say so.
- Timer: Bash with `run_in_background: true` running `sleep <seconds>; echo "TIMER <id>"`. Its exit is a notification. TaskStop cancels it.
- TaskStop stops a background agent or shell by its ID.
- Bash tool: 120 s default timeout, 600 s maximum in the foreground. Run longer measurements with `run_in_background: true`.
- A subagent that waits on its own background command produces an interim notification ("waiting on its own background work"). It has not finished: act only on a notification whose result holds the report block.
- Never `cd` into a worktree in your own shell; use `git -C <dir>` or a `( cd <dir> && … )` subshell. On Windows a directory that is a shell's working directory cannot be removed.

## 1. Setup: one round of questions

First take a short look at the repo, so that you can propose the commands. Then ask for **all inputs in one message**: a numbered form with every input and its proposed or default value. Values the arguments or the conversation already give are filled in. The user answers once, with changes or "ok". Do not ask follow-up questions; if the answer leaves an input open, use its default and say so.

| Input | Default and notes |
|---|---|
| Goal | What to improve. From the arguments. |
| REPO, MAIN | The current repo and the branch checked out now. |
| Metric | Name, unit, direction (lower or higher is better). |
| MEASURE_CMD | The test program, run from the repo root. Mode `time` = its wall-clock seconds; mode `stdout` = the last number it prints. Propose one. |
| CORRECT_CMD | Exits 0 when the output is still correct. Propose one, e.g. save the baseline output under `RUN_DIR/ref/` and diff against it. Required: a change that fails it is always rejected. |
| SETUP_CMD | Prepares a fresh worktree: installs dependencies, links untracked data. Default: none. A worktree holds only tracked files. |
| Baseline | Default: MAIN as it is now, measured by you. If the user gives a number, still measure it and show both. |
| N | Concurrent testers. Default: 3. |
| T_TEST;T_ITER | Two strict time budgets, written as `5m;10m` (the default). T_TEST: the most one run of the test program may take; `measure.sh` kills a run that exceeds it. T_ITER: one whole tester iteration, from dispatch to its final report. |
| T_RESEARCH | Research budget per burst. Default: 5m. |
| Models | For research, tester and implementer (opus, sonnet, haiku, fable). Default: opus for each. |
| Measurement lock | Serializes measurements so that only one runs at a time. Default: on in `time` mode, because parallel runs distort timings. In `stdout` mode, on only if parallel runs would break or distort the value (fixed ports, shared output paths, single GPU, rate limits). |

Write every message to the user in the conversation's language, or in the language the user asks for.

Then:
1. Check that the working tree is clean. If it is not, stop and tell the user. Tell them not to edit the main checkout during the run.
2. Create `RUN_DIR` = `<parent of REPO>/<repo name>.optimize/`. It sits outside the repo, so test runners and linters in MAIN never see the worktrees. `STATE` = `RUN_DIR/state.md`. `LOCK` = `RUN_DIR/measure.lock` if the lock is on, else `none`.
3. Create the measuring worktree: `git -C REPO worktree add --detach RUN_DIR/wt/measure MAIN`, then run SETUP_CMD in it. You and research measure MAIN only there, never in the main checkout, so measurement output cannot block the implementer's fast-forward. Measure B0 with `measure.sh` (3 runs, T_TEST each) and run CORRECT_CMD. It must pass. This also proves that SETUP_CMD gives a working worktree.
4. Derive R, the runs per side for testers, from the B0 median run time `run`. L = N if the lock is on, else 1, because testers queue for the lock. `R = clamp(min(floor(T_TEST / run), floor(T_ITER / (4 × L × run))), 1, 5)`. So R runs fit in T_TEST, and both sides' measurements, queueing included, fit in half of T_ITER.
5. Write STATE and show the user the setup summary and the empty report.

## 2. Event loop

React to events. Update STATE after each one, then print the report (section 4).

| Event | Action |
|---|---|
| Research sends an idea | Drop it if it repeats a tried idea. Otherwise queue it, ranked by expected gain × confidence. Fill free tester slots. |
| Tester finishes | TaskStop its timer (and grace timer). Decide (section 3). Start the implementer if you decide a batch is ready. Fill the free slot. |
| A timer fires and its agent is still running | Send the agent: `TIME UP for <id>: stop editing, end the current command, and report within <G> s with what you have.` Post one line to the user. Start a grace timer of G = min(120, max(30, T_ITER/5)) seconds. |
| A grace timer fires and its agent is still running | TaskStop it. A tester's idea gets status `timeout` and its worktree is removed. |
| Implementer finishes with `MERGED: yes` | Measure MAIN → Bk, then run CORRECT_CMD (section 3). Remove the batch worktree, then delete the batch branch and the migrated item branches with `git branch -D` (cherry-picks get new SHAs, so `-d` refuses). The hot spots have moved, so clear research `exhausted`, and re-queue ideas rejected as `within noise` or `timeout` as `retest`, once each. |
| Implementer finishes with `MERGED: no` | Read the reason. If you can remove the cause, run the batch again; otherwise tell the user. |
| Research finishes | TaskStop its timer. If it reports `exhausted: yes`, or two bursts in a row brought no new idea, set research to exhausted and tell the user. |
| The user changes an input | Apply it to new dispatches. |
| The user says stop | Shut down (section 5). |

**Dispatch a tester** for the queued idea with the highest rank:
1. `git -C REPO worktree add -b opt/<id> RUN_DIR/wt/<id> MAIN`, run SETUP_CMD in it, and record the base SHA.
2. Spawn an agent with `tester-prompt.md`. Include the deadline as a clock time. If MEASURE_CMD contains single quotes, write each as `'\''`.
3. Start its timer for T_ITER. Record the agentId, timer ID, base SHA and dispatch time in STATE.

**Start research:** `git -C RUN_DIR/wt/measure checkout --detach MAIN`, then spawn an agent with `research-prompt.md` and a deadline of T_RESEARCH. Start its timer for T_RESEARCH.

**Economy:**
- Run exactly min(N, queued ideas) testers.
- Start research only when fewer than N untested ideas are queued and research is not running or exhausted. Ask for 2N ideas per burst. Do not measure in the measuring worktree while research is running.
- Never run two implementers.
- Prompts point to STATE for history instead of pasting it.

## 3. Decisions

**Accept or reject: your call.** A result that fails CORRECT_CMD is always rejected. Otherwise weigh:
- the gain against its own base, compared with the run-to-run spread on both sides;
- the size and risk of the diff against that gain;
- scope: `git -C REPO diff <base>..opt/<id>` must not change MEASURE_CMD, CORRECT_CMD, test inputs or reference outputs;
- gaming: caching results across runs, skipping required work, special-casing the test input.

Record the reason in one line. Remove worktrees with `git -C REPO worktree remove --force <dir>`, because measurement output leaves untracked files. Accepted: remove the worktree and keep the branch. Rejected or failed: remove the worktree and delete the branch.

**Overlapping ideas:** if two accepted ideas change the same code for the same gain (for example two fixes of one hot loop), put only the one with the larger measured gain in the batch. Mark the other `superseded by #<id>` and delete its branch.

**Batch size: your call.** Aim for the shortest total time to the best MAIN. Each batch costs one implementer run and one re-measure; testers keep working meanwhile.
- Migrate early when an accepted idea has a large gain or moves the hot spot. Every later test then runs against the faster baseline, and research looks at the new hot spots.
- Collect more when the accepted gains are small, or when running testers will soon return ideas for the same code.
- Always migrate when the queue is empty, no tester is running and an accepted idea waits.

**Implementer batch:** `git -C REPO worktree add -b opt/batch-<k> RUN_DIR/wt/batch-<k> MAIN`. Spawn `implementer-prompt.md` with the accepted branches, ordered by measured gain. Its timer is T_ITER × (number of items).

**After a batch:** `git -C RUN_DIR/wt/measure checkout --detach MAIN`, measure it with R runs → Bk, then run CORRECT_CMD there.
- Bk is worse than B(k-1) beyond the spread, or correctness fails: measure each batch commit in the measuring worktree, then spawn the implementer in revert mode for the commits that made it worse. Re-queue those ideas as `retest`.
- Bk gains less than the product of the item ratios: note "overlapping gains" in the report. No other action.

## 4. Report

Write the report in the conversation's language, both in STATE and in chat. Every number names the baseline it compares to.

```
Main: B0 120.4 s → B2 9.1 s  (13.2× vs B0)  ·  2 batches · 5 accepted · 3 rejected · 3 testing · research: running

| Baseline | Value   | vs B0 | Batch contents |
| B0       | 120.4 s | 1.0×  | starting point |
| B1       | 24.0 s  | 5.0×  | #1, #3 |

| # | Technique | Metric | Expected | Measured (vs its base) | Est. vs B0 | Status |
| 1 | Vectorize the inner loop | wall time | 3–5× | B0: 120.4 → 24.1 s, 5.0×, 3+3 runs, ±0.8 s | 5.0× | in MAIN (B1) |
| 6 | Cache the parsed config  | wall time | 1.2× | B1: 24.0 → 23.6 s, 1.02×, within spread | — | rejected: within noise |
```

- Est. vs B0 = (its base's gain vs B0) × the item's ratio. It is an estimate until the item is in MAIN; after that, the baseline table holds the measured value.
- Statuses: queued → testing → accepted / rejected (reason) / timeout → migrating → in MAIN (Bk) / skipped (reason) / superseded by #id / retest.
- If the lock is off, add one line: absolute values were measured under parallel load, and ratios are the more reliable figure.

## 5. State, compaction and stop

STATE holds the config, the baselines table, every idea with its status, agentId, timer ID, base SHA and branch, and the research status. It is the source of truth. After a context summary, or whenever you are unsure, re-read STATE before you act.

On stop: TaskStop every running agent and timer. Remove all worktrees and run `git -C REPO worktree prune`. Keep the branches of accepted, unmigrated ideas; delete the other `opt/*` branches. Print the final report. If accepted ideas still wait for migration, offer one last batch.

## Common mistakes

| Mistake | Fix |
|---|---|
| Asking setup questions over several turns | One form, one answer, defaults for the rest. |
| Waiting in a sleep loop for agents | End the turn; notifications wake you. |
| A tester measures only the candidate | It measures its base and the candidate in the same worktree with the same command. |
| Timing measurements without the lock | Parallel load hides real gains: in testing, a change that saves about 0.4 s per run measured as within noise next to other agents. Keep the lock on in `time` mode. |
| Reporting a ratio without its baseline | Name the baseline (B0, Bk) next to every number. |
| Two agents writing to MAIN | Only the implementer fast-forwards MAIN. |
| Reusing a tester for the next idea | Spawn a fresh tester on a fresh worktree from the current MAIN. |
| Keeping a timed-out tester alive "because it is close" | The budgets are strict: warning, grace period, then TaskStop. |
