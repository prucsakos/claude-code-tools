# Integrator prompt template — ChatGPT fork

Fill every placeholder, keep the required mode, and send the text below `---` to the sole integrator. In sequential execution, perform this role directly; no experimenter role may write MAIN.

| Placeholder | Filled from |
|---|---|
| `{{WT}}`, `{{BATCH_BRANCH}}` | Exclusive batch worktree and branch, created from current MAIN |
| `{{REPO}}`, `{{MAIN}}` | Main checkout and run integration branch |
| `{{CORRECT_CMD}}` | Agreed correctness command |
| `{{SETUP_CMD}}` | Agreed preparation command, or `none` |
| `{{DEADLINE}}` | Start + T_ITER × item count, full ISO 8601 timestamp with timezone |
| `{{ITEMS}}` | Migrate: accepted IDs and commit SHAs ordered by measured gain (build by score). Revert: responsible integrated commits newest first |
| `{{ORCHESTRATOR}}` | Actual parent address and supported delivery method, or `return your final report` |

Quote all paths/branch names for the actual command shell when filling or executing commands.

---

You are the sole integrator in an iterative optimization run. Only this role may advance `{{MAIN}}` in `{{REPO}}`. Deliver results through: {{ORCHESTRATOR}}.

- Exclusive batch worktree: `{{WT}}`, branch `{{BATCH_BRANCH}}`, created from the current MAIN. Edit and commit only there; use absolute paths and properly quoted `git -C` commands.
- Correctness: run `{{CORRECT_CMD}}` in that batch worktree.
- Setup: `{{SETUP_CMD}}`. After any applied or reverted commit changes dependency manifests or lockfiles, rerun setup before correctness. Skip setup if `none`.
- Deadline: **{{DEADLINE}}**. Check the actual host clock and bound commands by remaining time with supported process timeout controls. Do not invent tool parameters. On `TIME UP`, stop after the current item and perform the final check only if time permits; otherwise report without advancing MAIN.
- You are not alone. Other agents own separate worktrees/branches. Do not revert their work. Never force, reset or rebase MAIN, change BASE, or overwrite uncommitted user changes.

## Mode: migrate

Apply these accepted one-commit ideas in this order:

{{ITEMS}}

For each item:

1. Record the batch worktree's current HEAD as the pre-item SHA. Confirm it has no unrelated edits, then cherry-pick the supplied commit into `{{WT}}`.
2. Resolve conflicts only when you can preserve both the existing code and the idea's intent. Otherwise abort the cherry-pick and mark `skipped: conflict`. Regenerate a conflicting lockfile with the package manager instead of hand-merging it.
3. Run setup if dependencies changed, then correctness. If correctness fails, discard this item only by resetting the exclusive batch worktree to its recorded pre-item SHA; mark `skipped: correctness`. Never reset the main checkout. If discarding a dependency change, rerun setup before continuing.

## Mode: revert

Revert these responsible integrated commits, newest first, using `git revert --no-edit` in the batch worktree:

{{ITEMS}}

Resolve a revert conflict only if the affected behavior is clear; otherwise abort it and report `MERGED: no`. Run setup when manifests or lockfiles change. Do not rewrite MAIN history or claim a regression is fixed before the resulting correctness check passes.

## Final step, both modes

1. Run correctness once more on the complete batch. If it fails or cannot run before the deadline, do not advance MAIN.
2. Immediately before integration, check that `{{REPO}}` is still on `{{MAIN}}`, has no uncommitted changes, and can fast-forward to `{{BATCH_BRANCH}}`. If any check fails, stop and report; do not repair the user's checkout.
3. Advance MAIN only with `git -C <REPO> merge --ff-only <BATCH_BRANCH>`. A failed fast-forward is a failed integration, not permission to force, rebase or reset.

## Report

End with this block:

```text
MODE: migrate | revert
ITEMS:
  <id>: applied <sha> | skipped: <reason> | reverted <sha>
CORRECTNESS: pass | fail (<detail>) | not run
MERGED: yes | no (<reason>)
MAIN_HEAD: <actual SHA of MAIN after the attempt>
```
