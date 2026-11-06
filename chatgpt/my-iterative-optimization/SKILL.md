---
name: my-iterative-optimization
description: Improve a git project through measured optimization experiments or build features and UI in small verified increments. Use for iterative improvements to performance, UX, UI, accessibility, SEO, i18n, quality, DX, operations, security, code health or documentation. ChatGPT fork of the Claude Code skill; uses parallel workers when available and sequential experiments otherwise. Execution requires a writable checkout and command tools.
metadata:
  variant: "ChatGPT fork; not the original Claude Code version"
  upstream: "https://github.com/prucsakos/claude-code-tools/tree/52b89bd27e0864fdf725dbbf44c0743a9510275e/skills/my-iterative-optimization"
---

# Iterative Optimization — ChatGPT fork

This is a **fork**, adapted from prucsakos's Claude Code skill. The original remains in `skills/my-iterative-optimization/`. See [FORK.md](FORK.md) for the pinned source and the changes made for ChatGPT.

Run experiments against a baseline, accept changes on evidence, integrate them in batches, and check for regressions across all selected targets. Continue within the user's scope and budget until stopped, the work is exhausted, or the host cannot continue.

## Execution capabilities

Inspect the actual tools before promising a run:

- **Execution:** a writable git checkout, git, Python 3.9+ and a shell that can run the project's checks. A read-only GitHub connection alone cannot run benchmarks or create worktrees. Without execution access, inspect the available source and provide a concrete experiment plan or patch, marking every unrun check and measurement as unverified. State the missing capability once.
- **Delegation:** use the host's real worker, messaging, waiting and cancellation tools when available. In Codex, use its available collaboration tools. Do not assume Claude's Agent/SendMessage/TaskStop tools or a particular model exist. Use the current/default model unless the user specifies one.
- **Concurrency:** profiles express requested experimenter capacity, not permission to exceed host limits. Report the effective capacity. Schedule researchers and the integrator within the same host limit; release/reserve a slot for integration. Queue and rotate pillars when they outnumber available slots. Recompute measurement budgets for the actual allocation.
- **Sequential fallback:** without delegation, perform the researcher, experimenter and integrator roles in order, with one isolated experiment at a time. Explain this once. The same measurement, acceptance and integration rules apply; parallel runs must never be simulated in prose.
- **Continuation:** use actual completion events or bounded host waits while work runs. Check deadlines and user messages between waits; give meaningful progress at least once a minute while active. Do not end the turn expecting a future wake-up unless the host explicitly supports it. If the host must yield, checkpoint STATE and report what has stopped or is still running; never imply that a plain chat will keep working unattended.
- **Deadlines:** keep full timestamps with time zone and real process handles. A tool's wait/yield interval is not a process timeout. Use enforceable command timeouts and the bundled runner for measurements. Do not invent timeout parameters. See [workflow.md](references/workflow.md#deadlines-and-events).

## Roles and resources

| Role | Responsibility | Write ownership |
|---|---|---|
| Orchestrator | Configure, queue, inspect results, accept/reject, report | External RUN_DIR and STATE; project edits only when performing a sequential role |
| Researcher | Find conservative and bold ideas for one pillar | No code edits; designated external profiling output only |
| Experimenter | Implement one idea on one fresh base | Its assigned worktree and branch only |
| Integrator | Apply accepted commits; revert regressions | One batch worktree, then fast-forward MAIN |

Workers are not alone in the repository. Give each its explicit ownership and tell it to preserve others' work. Never run two integrators or let experimenters edit MAIN.

Read [pillars.md](references/pillars.md) when choosing targets and their anti-gaming rules. Read [workflow.md](references/workflow.md) before executing setup or dispatching work. Load the appropriate role template only when needed:

- [researcher-prompt.md](references/researcher-prompt.md): one research round for one pillar.
- [experimenter-prompt.md](references/experimenter-prompt.md): one implementation and its evidence.
- [integrator-prompt.md](references/integrator-prompt.md): migration or revert of a batch.

Fill every template placeholder with actual values, retain only the relevant kind/mode sections, and send the text below its separator as the task. Prepare complete commands with paths and shell quoting already resolved. Do not paste the entire state history into a worker prompt; point to STATE when shared file access exists, otherwise send only the necessary state excerpt.

## 1. Configure the run

Take a short read-only look at the repo to identify its checks, build tools and potential measurement commands. Reuse the user's existing choices and authorization; do not ask questions they have answered.

A **pillar** is an area of work. Groups are Product (Performance, UX, UI, Features), Reach (Accessibility, SEO, i18n), Engineering (Quality, DX, OX/operator experience, Security), and Code health (Code hygiene, Dependency health, Documentation). The user may name custom pillars or targets.

Each target is a track of one kind:

- **optimize:** one metric with a unit, direction, command, measurement mode, lock and repetitions. Accept on measured gain beyond noise.
- **build:** one feature/design or independently useful increment, with acceptance criteria fixed before dispatch. Accept on evidence for every criterion, including screenshots for UI.

Infer an explicit goal's pillar/target: "make it faster" selects Performance: Speed; "faster builds" selects DX: Build time. If the goal is broad, offer the pillar groups and then any unresolved targets in a compact form. Use the available question tool or ordinary chat; do not assume multiselect support, a four-question limit, or an automatically added Other option. Keep custom choices possible. Never silently replace an unmeasurable requested goal: propose a proxy/harness, or explain that it remains blocked.

### Profiles and modes

| Profile | Requested experimenters N | Research round T_RESEARCH |
|---|---|---|
| low | 5 | 3 minutes |
| medium (default) | 10 | 5 minutes |
| high | 15 | 10 minutes |

Profiles set only these values. Respect explicit overrides and actual host capacity. Divide experimenters evenly over pillars, distributing the remainder in group order. A pillar fed only by a finite user list needs no more workers than remaining items and no researcher.

**auto** (default): decide acceptance and batches autonomously after setup. **review**: keep testing while each concrete batch awaits the user's approval; accepted work is not approval to integrate it. Both modes respect the user's scope and any platform-required permissions.

Collect all remaining inputs together, with proposed defaults:

| Input | Value to establish |
|---|---|
| Goal and scope | User's words, selected pillars/targets and optimize/build kind |
| Profile, mode, allocation | Requested N, effective experimenters and researchers under host limits |
| REPO, MAIN | Checkout and current branch; with PR enabled, original branch is BASE and MAIN is a new `optimize/<timestamp>` run branch |
| Each optimize target | Metric, unit, direction; MEASURE_CMD; `time` or `stdout`; lock setting |
| Each build target | User's items or researched items; acceptance criteria per item; cap for researched items (default 5) |
| CORRECT_CMD | Required, direct correctness checks and full applicable test suite, not a changeable build wrapper; preserve existing behavior without freezing what the requested build intentionally changes |
| SETUP_CMD | Fresh-worktree dependencies/data preparation; default none |
| EVIDENCE_CMD | UI only: start the app from the worktree, capture relevant phone/desktop screens into an explicit external output directory, print screenshot count, and clean up the server |
| Budgets | T_TEST per measurement run and T_ITER per whole experiment, default `5m;10m`; any user-specified total time, cost or iteration limit |
| Baseline | Measure current MAIN even if the user supplied an expected number; show both |
| Publishing | Default off unless the request already authorizes pushing/creating a PR and the available remote/authentication supports it; name REMOTE, BASE and run branch when enabled |

Time metrics default to locking. Other metrics lock when ports, files, a GPU, rate limits or parallel load would distort them. All locked measurements, profiles and UI captures use the same `RUN_DIR/measure.lock` **file**.

Show one setup table with target-specific choices and the shared inputs below it. Ask once for unresolved material choices and confirmation of the concrete setup; say this is the skill's setup gate. Do not request another approval when the user has already authorized these exact choices. Do not create RUN_DIR/worktrees or run setup/benchmarks before the setup is authorized. Respect an actual review gate without treating elapsed time as approval.

## 2. Establish B0 and dispatch

Follow [workflow.md](references/workflow.md#setup-and-measurement-budgets) for isolation and measurement sizing:

1. Require a clean checkout; preserve uncommitted work and report the blocker without stashing or resetting it. Record the starting SHA. Use a fresh external RUN_DIR for each run and record its exact owned worktrees/branches.
2. If publishing is enabled, create MAIN as the run branch, leaving BASE unchanged. Create detached measurement and researcher worktrees; run SETUP_CMD. Keep harnesses, references, screenshots, measurements and STATE outside the project.
3. Run CORRECT_CMD and measure B0 with three runs per optimize target using [scripts/measure.py](scripts/measure.py). Capture and inspect baseline UI evidence if applicable. If required evidence fails, fix the harness or mark that track blocked; do not silently drop a requested target.
4. Compute R and feasible concurrency from observed run times, locks, capture time and actual host slots. Show any allocation change and its reason. Deterministic metrics use R=1.
5. Queue the user's items with high value/confidence, only the first increment of split items. Write STATE and start work.

Keep research queues wide and bounded. Each pillar's researcher sends at most K = twice its active experimenter allocation, with conservative and bold ideas. Start research only when its untested queue is smaller than its allocation, no researcher is running, research is not exhausted and a target remains. Two rounds without new ideas exhaust that pillar. Deduplicate across all pillars.

Rank optimize ideas by expected relative gain times confidence; build ideas by value times confidence. Map high/medium/low to 1/0.6/0.3. Balance targets within a pillar, and test its best bold idea when one is queued and none is testing. Each idea gets a fresh worktree/branch from current MAIN, its base SHA, a fresh worker or sequential role, a fixed deadline and the relevant anti-gaming list. Never run more than effective N experimenters.

## 3. Decide, integrate, remeasure

A failed CORRECT_CMD always rejects the result. Inspect the actual diff, commit and raw evidence; a worker's summary alone is insufficient. Reject weakened checks, altered benchmarks/inputs/references, test deletion, suppression tricks and each target's gaming. Build/tool/dependency configuration may change if the same required work and checks still run. Acceptance criteria belong to the orchestrator/user, never the experimenter.

For optimize ideas, weigh gain against both sides' spread, diff risk and other selected targets. Reject noise. For build ideas, require every criterion, reachable behavior, tests and inspected screenshots where applicable. Explain acceptance or rejection in one line. Supersede overlapping alternatives rather than counting the same gain twice.

Batch accepted ideas when that gets useful improvements into MAIN sooner: early for a large gain, a changed hot spot or the next waiting increment; combine small changes when appropriate. Always integrate waiting accepted items when experiments and queue are otherwise empty. In review mode, present ids, targets, evidence, measured gains/baselines, diff sizes and recent rejections, and hold the batch until approved. Continue independent work through real asynchronous tools if possible.

Only the integrator applies a batch, checking each cherry-pick and the complete batch, then fast-forwarding MAIN. Never force, reset or rebase MAIN. After integration, measure **every optimize target**, run CORRECT_CMD and refresh UI evidence. A regression beyond noise on **any** target, or failed correctness, starts attribution and a revert batch. See [workflow.md](references/workflow.md#integration-and-regressions) for conflict handling, stale results, rollback and publication.

Queue the next increment only after its predecessor reaches MAIN. After a successful baseline change, clear research exhaustion and retest noise-rejected ideas and previously unsplittable timeouts once per new baseline. Do not cycle forever on the same failed idea.

## 4. State and reporting

STATE is the source of truth. Update it after each meaningful event. Record config, requested/effective allocation, ownership, commands/shell, per-target R, baselines and raw runs, ideas/scores/reasons, fixed acceptance criteria, base/commit SHAs, worktrees/branches, real worker/process handles, deadlines, research status, remaining increments/caps, publishing authorization and PR URL. Re-read after compaction or uncertainty; inspect real processes and git state before resuming.

Report in the conversation's language. Show current MAIN against B0 per target, batch/accepted/rejected/testing counts, researchers and any awaiting approval. Keep a baseline table and an idea table with target, technique, expected result, measured result versus its named base, estimate versus B0, and status. Build tracks count completed items against list/cap and show acceptance evidence. Estimates remain labeled until the combined MAIN is measured. At zero, show absolute changes instead of an undefined ratio. Explain that unlocked absolute values were measured under parallel load.

Use statuses `queued`, `testing`, `accepted`, `rejected: reason`, `timeout`, `migrating`, `in MAIN (Bk)`, `skipped: reason`, `superseded`, `retest`, and `blocked: missing capability` where applicable. A partial report is not a completed task.

## 5. Stop and cleanup

Follow [workflow.md](references/workflow.md#shutdown). Stop dispatching at a user stop, explicit budget boundary, or exhaustion. Auto finishes when queues, active roles, accepted items and possible research are all empty; review reports idle once and awaits input. Do not claim completion while a requested track remains blocked.

Cancel real agents/processes and collect final state before deleting their worktrees. Integrate a final accepted batch only if existing authorization allows it and the stop instruction permits it; review never bypasses approval. Keep accepted unmigrated branches. Remove only verified run-owned worktrees/branches; retain STATE and evidence. Publish the final PR state only when authorized. Finish with measured changes, relevant checks, unfinished work, remaining branches and any PR URL or publication error.
