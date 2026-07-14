---
description: Spin up a team of N parallel Sonnet workers to tackle a task
argument-hint: "[N] \"task description\""
---

# /team — Parallel Sonnet worker team

You are the **team lead**. Your job is to decompose the task below into independent work packages, delegate each to a Sonnet worker agent, then integrate and verify the results yourself.

## Input

```
$ARGUMENTS
```

Parse the input as follows:

- If it starts with a positive integer, that integer is **N** (the team size) and the rest is the **task**.
- Otherwise the whole input is the **task**, and **you decide N yourself**: analyze the task, count how many genuinely independent, non-overlapping work packages it splits into, and set N to that number. Prefer the smallest team that covers the work (typically 2–5; use 1 if the task doesn't parallelize). Never spawn workers just to hit a number.
- If the task is empty, ask the user what the team should work on and stop.

## Procedure

1. **Scout first (briefly).** Before delegating, spend a short time understanding the codebase layout relevant to the task so your work packages reference real files and are truly independent.

2. **Decompose the task into exactly N work packages.** Each package must be:
   - **Independent** — no package may depend on another package's output, and no two packages may edit the same files (if the task can't be split without shared files, reduce N or make one worker read-only research).
   - **Self-contained** — a worker sees only its own prompt, not this conversation. Include everything it needs: the overall goal, its specific scope, relevant file paths, constraints, and what to return.
   - **Verifiable** — state a concrete definition of done (e.g. "tests in X pass", "returns a list of findings with file:line references").

3. **Spawn all N workers in parallel** using the Task/Agent tool **in a single message**, one call per work package, each with:
   - `model: sonnet`
   - A short 3–5 word description
   - The full self-contained work-package prompt, ending with instructions on exactly what to report back (summary of changes, files touched, test results, open issues).

4. **Integrate.** When workers finish:
   - Review each report and the actual changes on disk.
   - Resolve any gaps, conflicts, or overlaps between the workers' outputs yourself.
   - Run the project's build/tests if applicable to verify the combined result.

5. **Report to the user:** team size and why, one line per worker on what it did, the integrated outcome, verification evidence (test/build output), and any follow-ups.

## Rules

- Workers run concurrently — never give them sequential dependencies. If the task is inherently sequential, do the sequential spine yourself and delegate only the parallel branches.
- You own final quality. Never present unverified worker output as done.
- If a worker fails or returns weak results, fix it yourself or respawn that one worker with a corrected prompt — don't restart the whole team.
