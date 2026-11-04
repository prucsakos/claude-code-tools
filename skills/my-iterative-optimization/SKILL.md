---
name: my-iterative-optimization
description: Use when the user wants to make a script, program or code base measurably better in one or more areas (faster, cheaper, smaller, more accurate, or better UX, UI, accessibility, SEO, i18n, code quality, code hygiene, dependency health, documentation, DX, OX or security), or to build new features or UI designs in small tested increments, by testing many candidates in parallel against a baseline over fast iterations, and to keep going until they stop it. Claude Code only; the project must be a git repository.
---

# Iterative Optimization

You are the **orchestrator** of a run that works on one or more targets. An optimize target improves a measurable metric; a build target adds new features or designs. You never edit the project's code. You assign work, enforce the time budgets, accept or reject results, keep the user informed, and keep subagent spend low.

## Roles

| Role | How many | Runs when | Writes to |
|---|---|---|---|
| Orchestrator (you) | 1 | the whole run | `RUN_DIR` only: STATE, reference outputs, measurement harnesses |
| Researcher | one per selected pillar | its pillar has fewer queued ideas than experimenters | nothing; sends ideas to you |
| Experimenter | N in total, divided evenly over the pillars | one fresh agent per idea | its own worktree and branch |
| Integrator | 0–1 at a time | you decide a batch is ready (review mode: and the user approved it) | batch worktree, then fast-forwards MAIN |

Files in this skill's directory: `pillars.md` (the pillars and their targets), `researcher-prompt.md`, `experimenter-prompt.md`, `integrator-prompt.md` (fill every `{{…}}` before you send one), and `measure.sh` (the only way anybody measures).

## Pillars and targets

A pillar is an area of the project to work on. There are four groups: Product (Performance, UX, UI, Features), Reach (Accessibility, SEO, i18n), Engineering (Quality, DX, OX = operator experience, Security) and Code health (Code hygiene, Dependency health, Documentation). A target is one concrete goal inside a pillar, such as Speed or Memory for Performance. `pillars.md` lists the targets of each pillar, with example metrics and the gaming to reject. The user can also name a pillar or a target of their own.

Every target has one of two kinds:
- **optimize**: improve a measurable metric. An idea is accepted on its measured gain.
- **build**: add something new, such as a feature or a screen. An idea is accepted when it meets acceptance criteria that were fixed before it was dispatched, shown with evidence (new tests, screenshots). CORRECT_CMD guards the existing behavior.

Each selected target is a **track**. An optimize track has its own metric, MEASURE_CMD, mode, lock setting, R and baseline values. Wherever this skill says "the metric", MEASURE_CMD, mode, lock or R, it means the values of the optimize target in question. A build track has its items, their acceptance criteria, and a cap. CORRECT_CMD, T_TEST;T_ITER, the run mode and the profile values (N, T_RESEARCH) are shared by all targets. N is divided evenly over the pillars: each pillar gets its own share of the experimenters and its own researcher. Baselines stay numbered per state of MAIN: B0 and every Bk hold one value per optimize target. A run with one target works like a single-metric run.

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

## 1. Setup: pillars, targets, one form, then confirmation

First take a short look at the repo, so that you can propose the commands.

**Pillars.** If the arguments or the conversation name the pillars, the targets, or one concrete metric, use them and skip the questions they answer. `pillars.md` shows which pillar and target a metric belongs to: "make X faster" = Performance: Speed, "make the build faster" = DX: Build time. Otherwise ask with one AskUserQuestion call that holds four `multiSelect` questions, one per group. Each option's description is the pillar's "Improves" text from `pillars.md`; do not propose metrics yet.
- Header "Product": "Which product pillars should the run work on?": Performance, UX, UI, Features.
- Header "Reach": "Which reach pillars (who can find and use the product) should the run improve?": Accessibility, SEO, i18n.
- Header "Engineering": "Which engineering pillars should the run improve?": Quality, DX, OX, Security.
- Header "Code health": "Which code health pillars should the run improve?": Code hygiene, Dependency health, Documentation.

The tool adds "Other", where the user can name a custom pillar. If no pillar is left (none selected, or the form drops every target), use Performance: Speed and say why in the form. If AskUserQuestion is not available, put the pillar list into the form as its first input.

**Targets.** Then ask which targets the run works on: one AskUserQuestion call with one `multiSelect` question per selected pillar that has two or more targets, at most four. Header: the pillar's name, at most 12 characters ("Deps", "Docs"). Question: "Which <pillar> targets should the run work on?" Options: the pillar's targets from `pillars.md`, with their text as the description. In "Other" the user can describe a target of their own, such as "startup time of the CLI" or "CSV export of reports". Skip a pillar whose targets the arguments already name, and a pillar with one target. With more than four pillars left, ask about the first four in group order and propose targets for the rest in the form. If AskUserQuestion is not available, put the targets into the form.

**Profile and run mode.** Take them from the arguments when they are given, e.g. `high auto "make the build faster"`. Otherwise they are the first two rows of the form. They never go into the pillar or target questions.

| Profile | N | T_RESEARCH |
|---|---|---|
| low | 5 | 3m |
| medium (default) | 10 | 5m |
| high | 15 | 10m |

A profile sets only these values. Spawn every agent with `model: opus`. The commands, metrics, locks and the time budgets T_TEST;T_ITER always come from the form. A value that the arguments or the form answer name overrides the profile's value. Setup step 4 can still move experimenters between pillars.

| Run mode | Who decides what reaches MAIN |
|---|---|
| auto (default) | You. Once the user has confirmed the setup table, you never wait for the user: you accept or reject, batch, migrate and revert on your own, report after each event, and shut the run down when nothing is left to do. |
| review | The user approves each batch before the integrator starts (section 3, Review gate). Everything else works as in auto, except that an idle run waits for the user. |

**Form.** Then ask for **all other inputs in one message**: a numbered form with every input and its proposed or default value. Rows marked *per pillar*, *per optimize target* or *per build target* appear once for each. Rows marked *profile* are not rows of their own: show their values inside the Profile row, and the user changes one by naming it. Values the arguments or the conversation already give are filled in. The user answers once, with changes or "ok". Do not ask follow-up questions; if the answer leaves an input open, use its default and say so.

| Input | Default and notes |
|---|---|
| Profile | `low`, `medium` or `high` (table above). Default: medium. |
| Run mode | `auto` or `review` (table above). Default: auto. |
| Goal | What to work on. From the arguments; if they give none, "improve the selected targets". |
| Targets | The selected targets, each with its pillar and kind. A proxy whose tool the repo lacks (e.g. Lighthouse, axe) still counts: propose a harness for it under `RUN_DIR/harness/`, outside every worktree. Drop an optimize target that has no measurable proxy, or a build target that cannot show its evidence, and give the reason. |
| Experimenters *per pillar* | The pillar's share of the N experimenters. N is divided evenly over the selected pillars, and the remainder goes one each to the first pillars in group order (15 over 3: 5, 5, 5; 10 over 3: 4, 3, 3). The total never exceeds N. A pillar whose only work is the user's list gets at most one experimenter per listed item; the rest are divided over the other pillars. With more pillars than N, say so: the user drops pillars or picks a larger N. The user may change the split, never above N in total. || REPO, MAIN | The current repo and the branch checked out now. |
| Metric *per optimize target* | Name, unit, direction (lower or higher is better). Propose it from `pillars.md` and what the repo has. |
| MEASURE_CMD *per optimize target* | The test program, run from the repo root. Mode `time` = its wall-clock seconds; mode `stdout` = the last number it prints. Propose one. `measure.sh` reads a non-zero exit as FAIL, and count tools (linters, `tsc`, audits, axe) exit non-zero when they find something. So pipe such a tool's JSON output into a counter that prints the count last: without `pipefail`, the counter's exit code is the one that counts. Their text summaries often end with a different number. |
| Build items *per build target* | Where its items come from. Your features: the user's list. Proposed features: its researcher. Redesign and New screens: the user's list, or the researcher when no list is given. For each listed item, propose acceptance criteria (what a test or a screenshot must show) and, if it cannot be built and tested within one T_ITER, a split into increments that each work on their own. |
| Cap *per build target fed by its researcher* | How many of its items may reach MAIN before the target is done. Default: 5. |
| EVIDENCE_CMD | Only with a UI build target. Starts the app from the current directory, captures the key pages at phone and desktop width into the directory given as its argument, and prints the number of screenshots. Propose one under `RUN_DIR/harness/`. Every run of it goes through `measure.sh` with `RUN_DIR/measure.lock`, so parallel experimenters never compete for a port. |
| CORRECT_CMD | Exits 0 when the output is still correct. Propose one, e.g. save the baseline output under `RUN_DIR/ref/` and diff against it. Required: a change that fails it is always rejected. Call the checks directly (e.g. `tsc --noEmit`, the test runner), not through a build script that an idea may change. With a build target, it must not freeze what the build targets change on purpose (a snapshot of a screen being redesigned, a diff of output that a feature extends): check only the behavior that must stay the same, and run the whole test suite, so that the tests of migrated build items keep running. |
| SETUP_CMD | Prepares a fresh worktree: installs dependencies, links untracked data. Default: none. A worktree holds only tracked files. |
| Baseline | Default: MAIN as it is now, measured by you. If the user gives a number, still measure it and show both. |
| N *profile* | Concurrent experimenters. |
| T_RESEARCH *profile* | Budget of one research round. |
| T_TEST;T_ITER | Two strict time budgets, written as `5m;10m` (the default). T_TEST: the most one run of the test program may take; `measure.sh` kills a run that exceeds it. T_ITER: one whole experimenter iteration, from dispatch to its final report. A build item must fit in one T_ITER, its tests and screenshots included. |
| Measurement lock *per optimize target* | Serializes measurements so that only one runs at a time. Default: on in `time` mode, because parallel runs distort timings. In `stdout` mode, on only if parallel runs would break or distort the value (fixed ports, shared output paths, single GPU, rate limits). |

**Confirmation.** When the user has answered the form, show the locked-in choices in one message, before you change anything on disk. First one table with a row per target: pillar, target, kind, metric or build items, MEASURE_CMD or evidence, lock, and the pillar's experimenters. A target the user typed appears as they wrote it. Below it, the shared values: profile, run mode, the researchers (one per pillar), T_TEST;T_ITER, CORRECT_CMD, SETUP_CMD, EVIDENCE_CMD, REPO and MAIN, goal. End with: reply `ok` to start, or name what to change. After a change, show the whole table again. Do not use AskUserQuestion for this: its dialog can hide the table. If setup later has to change a confirmed value (step 4), show the change and its reason in the setup summary; do not ask again.

Write every message to the user in the conversation's language, or in the language the user asks for.

After the user confirms:
1. Check that the working tree is clean. If it is not, stop and tell the user. Tell them not to edit the main checkout during the run.
2. Create `RUN_DIR` = `<parent of REPO>/<repo name>.optimize/`. It sits outside the repo, so test runners and linters in MAIN never see the worktrees. `STATE` = `RUN_DIR/state.md`. An optimize target's `LOCK` = `RUN_DIR/measure.lock` if its lock is on, else `none`. All locked targets share this one path, so their measurements never overlap. Write any harness the form proposed under `RUN_DIR/harness/`.
3. Create the measuring worktree: `git -C REPO worktree add --detach RUN_DIR/wt/measure MAIN`, then run SETUP_CMD in it. You measure MAIN only there, never in the main checkout, so measurement output cannot block the integrator's fast-forward. Create one worktree per researcher the same way, `RUN_DIR/wt/researcher-<pillar>` with a slug of the pillar's name (`researcher-code-hygiene`), and run SETUP_CMD in each: researchers read and profile there, so your checkouts and measurements in `wt/measure` never change files under it. Measure B0 for every optimize target with `measure.sh` (3 runs, T_TEST each) and run CORRECT_CMD. It must pass. This also proves that SETUP_CMD gives a working worktree. If EVIDENCE_CMD is set, run it once in `wt/measure` through `measure.sh` (mode `stdout`, the shared lock) into `RUN_DIR/shots/B0`, and look at the screenshots. Its run time is `ev`. If it fails, drop the UI build targets and say why.
4. Plan the measurements of each optimize target from its B0 median run time `run`. In `stdout` mode `measure.sh` prints no run time: time the whole B0 call and divide by its runs.
   - Lock on: experimenters measure only the candidate and compare it with the current baseline Bk, which you measured under the same lock. No contention is left for an A/B pair to cancel, and the lock time halves. Lock off: experimenters measure base and candidate in their own worktree.
   - S = sides an experimenter measures (1 with the lock on, 2 with it off). L = agents that queue for the shared lock: with the lock on, the experimenters of every pillar that has a locked target or a UI build target (a UI capture counts as one run), plus those pillars' researchers (one locked run each per round); with it off, 1.
   - `R = clamp(min(floor(T_TEST / run), floor(T_ITER / (2 × S × L × run))), 1, 5)`, the runs per side. So R runs fit in T_TEST, and all queued measurements fit in half of T_ITER.
   - All of them wait for the same lock. Use the longest of the locked median runs, and `ev` when a UI build target is selected, for `run` in the second term.
   - If a target's 3 B0 runs give the same value (typical for counts such as lint errors), its metric is deterministic: R = 1, and its spread is 0.
   - If even R = 1 does not fit for some target (2 × S × L × run > T_ITER, with `run` as in the second term), lower the experimenters of those pillars until it fits, at least 1 each, and give the freed experimenters to the other pillars. N drops only when there is no other pillar. Say so in the setup summary, with the reason.
   - With EVIDENCE_CMD, at most floor(T_ITER / (2 × ev)) experimenters work on UI build items at the same time, so that their captures fit in half of T_ITER even without a locked optimize target. If the UI pillar has nothing else for its other experimenters, give them to the other pillars.
5. Queue the user's build items as ideas, with value high and confidence high; of a split item, queue only its first increment. Write STATE and show the user the setup summary and the empty report.

## 2. Event loop

React to events. Update STATE after each one, then print the report (section 4).

| Event | Action |
|---|---|
| A researcher sends an idea | Drop it if it repeats a tried or queued idea, including one that another researcher sent. Drop a build idea that has no acceptance criteria. Otherwise queue it under its target, ranked by score = weight × confidence (high 1, medium 0.6, low 0.3). An optimize idea's weight is its expected relative gain = expected change / base value (120 → 24 s = 0.8; 42 → 0 errors = 1.0), so gains in different units compare. A build idea's weight is its value (high 1, medium 0.6, low 0.3). Fill free experimenter slots. |
| Experimenter finishes | TaskStop its timer (and grace timer). Decide (section 3). Start the integrator if you decide a batch is ready. Fill the free slot. |
| A timer fires and its agent is still running | Send the agent: `TIME UP for <id>: stop editing, end the current command, and report within <G> s with what you have.` Post one line to the user. Start a grace timer of G = min(120, max(30, T_ITER/5)) seconds. |
| A grace timer fires and its agent is still running | TaskStop it. An experimenter's idea gets status `timeout` and its worktree is removed. |
| An idea ends as `timeout`, or as a rejected `timeout-partial` | It did not fit T_ITER. You split it into increments that each work and can be tested on their own. Queue the first as `retest` with the idea's score, and record the rest in STATE as for a split item. An idea you cannot split stays `timeout`. |
| Integrator finishes with `MERGED: yes` | Measure every optimize target on MAIN → Bk, then run CORRECT_CMD (section 3). Remove the batch worktree, then delete the batch branch and the migrated item branches with `git branch -D` (cherry-picks get new SHAs, so `-d` refuses). A build target whose list is finished, or whose items in MAIN reach its cap, is done. Queue the next increment of each split item or idea whose increment has just reached MAIN. The hot spots have moved, so clear `exhausted` on every pillar's research, and re-queue ideas rejected as `within noise`, and `timeout` ideas you could not split, as `retest`, once each. |
| Integrator finishes with `MERGED: no` | Read the reason. If you can remove the cause, run the batch again. Otherwise, in review mode, tell the user. In auto mode, mark the items that cause it `skipped: <reason>` and run the rest again. If the cause is outside the run (REPO is not on MAIN, or has uncommitted changes), start no more batches until the user says it is fixed, tell the user, and keep testing. |
| A researcher finishes | TaskStop its timer. If it reports `exhausted: yes`, or its last two rounds brought no new idea, mark its pillar's research exhausted and tell the user. |
| The user answers a batch proposal (review mode) | Start the integrator with the items the user kept. Struck items get `rejected: by user`; delete their branches. A rejected idea the user names for a retest is re-queued as `retest`. |
| The user changes an input | Apply it to new dispatches. |
| The user says stop | Shut down (section 5). |

**Idle check.** After each event, check whether anything is left to do: the queue is empty, no agent is running, no accepted idea waits, and no researcher can start (every pillar's research is exhausted or its targets are done). In auto mode, shut down (section 5). In review mode, tell the user once, and wait for stop or new input.

**Rebalance.** A pillar is idle when all its targets are done, or when its research is exhausted and its queue is empty. Spread the experimenters of idle pillars over the other pillars, within the limits of setup step 4, and say so in the report. When an idle pillar gets ideas again, it gets its confirmed share back as the borrowed experimenters finish.

**Dispatch an experimenter** when a pillar has a free experimenter slot: its queued idea with the highest score. Keep the pillar's targets balanced: while one of its targets has queued ideas and no running experimenter, that target's best idea goes first. Keep its search wide: the score favors safe ideas, so while the pillar has a queued bold idea and none testing, its best bold idea goes next. A free slot whose pillar has no queued idea may serve another pillar, the one whose best queued idea has the highest score, but never a pillar with a locked target or a UI build target: their shares set R and the lock budget (setup step 4). The slot serves its own pillar again once the borrowed experimenter has finished.
1. `git -C REPO worktree add -b opt/<id> RUN_DIR/wt/<id> MAIN`, run SETUP_CMD in it, and record the base SHA.
2. Spawn an agent with `experimenter-prompt.md`, filled with the values of the idea's target, and keep the section of its kind. Include the deadline as a clock time. GAMING = the gaming list of the target's pillar from `pillars.md`, plus the gaming its metric invites (for LCP: shrinking or removing the largest element); for a build idea, plus the build gaming list. OTHER_TARGETS = the other selected targets, or `none`.
   - Optimize: with the lock on, BASE_VALUES = the target's runs of the current Bk; with it off, `none`. If MEASURE_CMD contains single quotes, write each as `'\''`.
   - Build: ACCEPTANCE = the idea's acceptance criteria. For a UI item, SHOTS = `RUN_DIR/shots/<id>`, BEFORE = the screenshots of the current baseline (`RUN_DIR/shots/Bk`) and LOCK = `RUN_DIR/measure.lock`; otherwise SHOTS and BEFORE = `none`.
3. Start its timer for T_ITER. Record the agentId, timer ID, base SHA and dispatch time in STATE.

**Start a researcher** for a pillar when it has fewer queued untested ideas than experimenters, its agent is not running, its research is not exhausted, and one of its targets is not done. A pillar whose targets all come from the user's list has no researcher.
1. `git -C RUN_DIR/wt/researcher-<pillar> checkout --detach MAIN`. If MAIN has moved since this worktree's last round, run SETUP_CMD in it.
2. Spawn the agent with `researcher-prompt.md`: its pillar, the other pillars that have a researcher, one TARGETS block per target of its pillar, K = 2 × the pillar's experimenters, and a deadline of T_RESEARCH.
3. Start its timer for T_RESEARCH.

**Economy:**
- Run as many experimenters as the split and the queue allow, never more than N.
- Start a pillar's researcher only as in Start a researcher, and ask it for 2 ideas per experimenter of the pillar.
- Never run two integrators.
- Prompts point to STATE for history instead of pasting it.

## 3. Decisions

**Accept or reject: your call.** A result that fails CORRECT_CMD is always rejected. For every idea, check the scope: `git -C REPO diff <base>..opt/<id>` must not weaken a check. It may add new tests, but it must not edit or delete existing tests, or change the benchmark code that MEASURE_CMD runs, test inputs, reference outputs, or the rules the checks apply (lint and type-check rules, checker ignore lists, coverage thresholds, suppression comments). Build, tool and dependency configuration may change when the same work still runs; most DX, Performance and Dependency health ideas work that way. A change that drops or narrows a check is gaming.

For an optimize idea, also weigh:
- the gain against its own base, compared with the run-to-run spread on both sides;
- the size and risk of the diff against that gain;
- gaming: special-casing the test input, and the GAMING list of the idea's target (for Performance: caching results across runs, skipping required work);
- the other targets: a diff that you expect to make another selected target worse needs a gain that outweighs it.

For a build idea, also weigh:
- every acceptance criterion: its evidence must show that it is met (new tests that exercise it; for a UI item, look at the before and after screenshots). In auto mode, accept only when every criterion has evidence;
- the diff does what the idea says and no more, fits the existing architecture and design system, and leaves the existing behavior unchanged;
- gaming: the build gaming list in `pillars.md`;
- the other targets, as for an optimize idea.

Record the reason in one line. Remove worktrees with `git -C REPO worktree remove --force <dir>`, because measurement output leaves untracked files. Accepted: remove the worktree and keep the branch. Rejected or failed: remove the worktree and delete the branch.

**Overlapping ideas:** if two accepted ideas change the same code for the same gain (for example two fixes of one hot loop), put only the one with the larger measured gain (for build items, the higher score) in the batch. Mark the other `superseded by #<id>` and delete its branch.

**Batch size: your call.** Aim for the shortest total time to the best MAIN. Each batch costs one integrator run and one re-measure; experimenters keep working meanwhile.
- Migrate early when an accepted idea has a large gain or moves the hot spot. Every later test then runs against the faster baseline, and researchers look at the new hot spots.
- Migrate early when the next increment of a split item waits for an accepted one.
- Collect more when the accepted gains are small, or when running experimenters will soon return ideas for the same code.
- Always migrate when the queue is empty, no experimenter is running and an accepted idea waits.

**Review gate (review mode only).** When you decide a batch is ready, do not start the integrator. Post the proposal: for each item its id, target, technique, result (measured gain against its base, or acceptance results with screenshot paths) and diff size (`git diff --stat`); then the ideas rejected since the last batch, with their one-line reasons. The user answers `ok`, strikes items (`drop #3`), or names a rejected idea to retest (`retest #6`). Do not ask with AskUserQuestion: it blocks you while timers and agent reports keep arriving. Mark the batch `awaiting approval` in STATE, end your turn, and keep handling events. Ideas accepted in the meantime wait for the next batch.

**Integrator batch:** `git -C REPO worktree add -b opt/batch-<k> RUN_DIR/wt/batch-<k> MAIN`, then run SETUP_CMD in it. Spawn `integrator-prompt.md` with the accepted branches, ordered by measured gain (build items by score). Its timer is T_ITER × (number of items).

**After a batch:** `git -C RUN_DIR/wt/measure checkout --detach MAIN`, run SETUP_CMD there (the batch may have changed dependencies), measure every optimize target → Bk (3 runs per target if all targets' runs together fit in T_ITER, else R), then run CORRECT_CMD there. With EVIDENCE_CMD, capture `RUN_DIR/shots/Bk` there the same way as B0.
- Bk is worse than B(k-1) beyond the spread **on any optimize target**, or correctness fails: measure each batch commit on the targets that got worse, in the measuring worktree, then spawn the integrator in revert mode for the commits that made it worse. Re-queue those ideas as `retest`. This is the check that catches a change that helps its own target and hurts another.
- On a target, Bk gains less than the product of the item ratios: note "overlapping gains" in the report. No other action.

## 4. Report

Write the report in the conversation's language, both in STATE and in chat. Every number names the baseline it compares to.

```
Main: B0 → B2  ·  2 batches · 6 accepted · 3 rejected · 10 testing · researchers: 2 of 3 running
  Performance: Speed  wall time    120.4 s → 9.1 s  (13.2× vs B0)  · 4 experimenters
  Code hygiene: Lint  lint errors  42 → 7           (6.0× vs B0)   · 3 experimenters
  Features: Proposed  1 of 5 in MAIN                               · 3 experimenters

| Baseline | Performance: Speed | Code hygiene: Lint | Batch contents |
| B0       | 120.4 s · 1.0×     | 42 · 1.0×          | starting point |
| B1       | 24.0 s · 5.0×      | 42 · 1.0×          | #1, #3 |
| B2       | 9.1 s · 13.2×      | 7 · 6.0×           | #4, #7, #8 |

| # | Target | Technique | Expected | Measured (vs its base) | Est. vs B0 | Status |
| 1 | Performance: Speed | Vectorize the inner loop | 3–5× | B0: 120.4 → 24.1 s, 5.0×, 3+3 runs, ±0.8 s | 5.0× | in MAIN (B1) |
| 6 | Performance: Speed | Cache the parsed config | 1.2× | B1: 24.0 → 23.6 s, 1.02×, within spread | — | rejected: within noise |
| 7 | Code hygiene: Lint | Remove unused imports in src/ | 42 → 10 | B1: 42 → 7 errors, 6.0×, 1+1 runs, deterministic | 6.0× | in MAIN (B2) |
| 8 | Features: Proposed | CSV export of reports | 1 click instead of 6 manual steps | acceptance 3 of 3, 2 tests added | — | in MAIN (B2) |
```

- Print one Main line per target, with its pillar's current experimenters (and the confirmed share, when a rebalance changed it), and one baseline-table column per optimize target. A build target's Main line counts its items in MAIN against its cap or its list.
- Est. vs B0 = (its base's gain vs B0 on the item's target) × the item's ratio. It is an estimate until the item is in MAIN; after that, the baseline table holds the measured value. Build items show `—`.
- When a lower-is-better value reaches 0, the ratio is undefined: show the absolute change (42 → 0) instead.
- Statuses: queued → testing → accepted / rejected (reason) / timeout → migrating → in MAIN (Bk) / skipped (reason) / superseded by #id / retest.
- For each optimize target with the lock off, add one line: its absolute values were measured under parallel load, and its ratios are the more reliable figure.
- In review mode, a batch that waits for the user shows on the Main line as `batch <k>: awaiting approval`.

## 5. State, compaction and stop

STATE holds the config (profile, run mode and every target's values), the baselines table, every idea with its target, scope, status, agentId, timer ID, base SHA and branch, each build target's items with the increments still to come and its cap, the increments still to come of each split idea, the confirmed and the current experimenter split, and each pillar's research status. It is the source of truth. After a context summary, or whenever you are unsure, re-read STATE before you act.

On stop: TaskStop every running agent and timer. In auto mode, if accepted ideas still wait for migration, run them as one last batch first, unless the stop message says not to, and wait for the integrator's report and the re-measure of MAIN. Remove all worktrees and run `git -C REPO worktree prune`. Keep the branches of accepted, unmigrated ideas; delete the other `opt/*` branches. Print the final report. In review mode, if accepted ideas still wait for migration, offer one last batch.

## Common mistakes

| Mistake | Fix |
|---|---|
| Asking setup questions over several turns | At most four rounds: the pillar question (only when the arguments name no pillar and no metric), the target question (only for pillars with two or more targets that the arguments do not name), one form with defaults for what the answer leaves open, then the confirmation table (again after each change). |
| Changing anything on disk before the user confirmed | No RUN_DIR, worktree or measurement until the confirmation table gets `ok`. |
| Comparing ideas of different targets by their raw gains | Seconds and lint errors do not compare. When a free slot serves another pillar, choose by score (relative gain or value, × confidence). |
| Lending experimenters to a pillar with a locked or UI build target | Its share sets R and the lock budget. Lend only to the other pillars. |
| Adding experimenters beyond N | Divide N over the pillars. Never raise it on your own. |
| Testing only safe, small ideas | Researchers send both conservative and bold ideas, and a pillar keeps a bold one testing whenever one is queued. |
| Accepting a gain that came from a weaker check | Weakened lint, type-check or audit rules, ignore lists, suppression comments, lowered thresholds and removed tests are gaming: reject. Build config changes that keep the same work are fine. |
| Letting an experimenter set its own acceptance criteria | Fix them before dispatch, from the researcher or the user's list. The experimenter reports against them. |
| A CORRECT_CMD that freezes what a build target changes | Check only the behavior that must stay the same, and run the whole test suite. |
| Measuring only the item's own target after a batch | Measure every optimize target into Bk. A regression on any of them starts the revert path. |
| Waiting in a sleep loop for agents | End the turn; notifications wake you. |
| An experimenter's base comes from somewhere else | Lock on: the Bk runs you give it, measured under the same lock. Lock off: its own base runs in its own worktree, with the same command. |
| Timing measurements without the lock | Parallel load hides real gains: in testing, a change that saves about 0.4 s per run measured as within noise next to other agents. Keep the lock on in `time` mode. |
| Reporting a ratio without its baseline | Name the baseline (B0, Bk) next to every number. |
| Two agents writing to MAIN | Only the integrator fast-forwards MAIN. |
| Reusing an experimenter for the next idea | Spawn a fresh experimenter on a fresh worktree from the current MAIN. |
| Keeping a timed-out experimenter alive "because it is close" | The budgets are strict: warning, grace period, then TaskStop. |
| Letting the researcher drop or split ideas by its own time estimate | Agents overestimate how long a task takes. The researcher sizes ideas by scope; you split an idea only after it times out. |
| Asking the user something mid-run in auto mode | Auto never waits for the user: decide, report, and go on. |
| Asking for batch approval with AskUserQuestion | It blocks the event loop. Post the proposal as a message, end the turn, and keep handling events. |
| Queuing an idea that another pillar's researcher already sent | Drop ideas that repeat a queued one: Performance and DX can both find the same build-config change. |
