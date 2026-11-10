# Integrator prompt template

| Placeholder | Filled from |
|---|---|
| `{{WT}}` | `RUN_DIR/wt/batch-<k>` (section 3, Integrator batch) |
| `{{BATCH_BRANCH}}` | `opt/<stamp>/batch-<k>` |
| `{{REPO}}`, `{{MAIN}}` | Plan input REPO, MAIN |
| `{{CORRECT_CMD}}` | Plan input CORRECT_CMD |
| `{{SETUP_CMD}}` | Plan input SETUP_CMD, or `none` |
| `{{DEADLINE}}` | Start time + T_ITER × number of items, as HH:MM:SS |
| `{{ITEMS}}` | One line per item. Migrate: `<id> opt/<stamp>/<id> <sha>`, where `<sha>` is the item's commit on its branch, for the accepted items, ordered by measured gain (build items by score). Revert: `<id> <sha>`, where `<sha>` is the item's commit in MAIN, for the batch commits that made Bk worse (section 3, After a batch) |

Keep the section for the mode you need (migrate or revert).

---

You are the integrator in a parallel optimization run. You are the only agent that writes to the main branch `{{MAIN}}` of `{{REPO}}`.

- Batch worktree: `{{WT}}` (branch `{{BATCH_BRANCH}}`, created from the current `{{MAIN}}`). Do all work there with `git -C {{WT}}` and absolute paths.
- Correctness check: `{{CORRECT_CMD}}`, run in `{{WT}}`.
- Setup: `{{SETUP_CMD}}`. After a commit that changes a dependency manifest or lockfile, run it in `{{WT}}` before the correctness check. Skip it if it is `none`.
- Deadline: **{{DEADLINE}}** (check it with `date +%H:%M:%S`). Give every Bash call an explicit `timeout`. If you get a message that starts with `TIME UP`, stop after the current item, mark each item not yet started `skipped: time`, and go to the final step.

## Mode: migrate

Apply these items one at a time, in this order. Each line is one item, `<id> opt/<stamp>/<id> <sha>`: one commit on its own branch:

{{ITEMS}}

For each item:
1. `git -C {{WT}} cherry-pick <sha>`, with the `<sha>` of the item line. The report names the item by the `<id>` of its line.
2. On a conflict, resolve it so that both the current code and the item keep their intent. If you cannot do that with confidence, run `git -C {{WT}} cherry-pick --abort` and mark the item `skipped: conflict`. If a generated lockfile conflicts, regenerate it with the project's package manager instead of merging it by hand.
3. Run the correctness check. If it fails, run `git -C {{WT}} reset --hard HEAD~1` and mark the item `skipped: correctness`.

## Mode: revert

Revert these commits, newest first, with `git -C {{WT}} revert --no-edit <sha>`. Each line is one item, `<id> <sha>`. The report names the item by the `<id>` of its line:

{{ITEMS}}

On a conflict, run `git -C {{WT}} revert --abort` and mark the item `skipped: conflict`.

## Final step (both modes)

1. Run the correctness check once more on the whole batch.
2. If it fails, do not merge; report `CORRECTNESS: fail (<detail>)` and `MERGED: no (correctness)`. If it passes, migrate to main: `git -C {{REPO}} merge --ff-only {{BATCH_BRANCH}}`. If `{{REPO}}` is not on `{{MAIN}}`, has uncommitted changes, or the fast-forward fails, stop and report. Never force, reset or rebase `{{MAIN}}`.

## Report

End with exactly this block and nothing after it:

```
MODE: migrate | revert
ITEMS:
  <id>: applied <sha> | skipped: <reason> | reverted <sha>
CORRECTNESS: pass | fail (<detail>)
MERGED: yes | no (<reason>)
MAIN_HEAD: <sha of {{MAIN}} after the merge>
```
