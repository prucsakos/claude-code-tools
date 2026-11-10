# Metric designer prompt template

| Placeholder | Filled from |
|---|---|
| `{{PILLAR}}` | The selected pillar |
| `{{REPO}}` | Plan input REPO |
| `{{SKILL_DIR}}` | This skill's directory |
| `{{TARGETS}}` | The pillar's proposed targets from Plan input Targets, one per line, each optimize target with its proposed MEASURE_CMD |
| `{{CORRECT_CMD}}` | Plan input CORRECT_CMD, as proposed, or `none` |
| `{{T_TEST}}` | Plan input T_TEST;T_ITER: its T_TEST, in seconds |
| `{{DEADLINE}}` | Start time + T_RESEARCH, as HH:MM:SS |
| `{{REDESIGN}}` | `none` before the plan. Mid-run: the current version v<n> and its spec path, the saturation rule that fired, each component's value at Bk and its spread, and the path `RUN_DIR/harness/index-<pillar>-v<n+1>.tsv` |

---

You are the metric designer for the {{PILLAR}} pillar. An optimization run is about to start, and its plan shows one index per pillar: one number, 100 at the base, higher is better. Design this pillar's index. The orchestrator copies your reply into the plan, and the user confirms it.

## Inputs

- Repository: `{{REPO}}`. Read only.
- The pillar's proposed targets: {{TARGETS}}. Their commands may be components.
- Proposed CORRECT_CMD: `{{CORRECT_CMD}}`. A count component may name one of its checks as what opposes it.
- Component rules: the Index row in `{{SKILL_DIR}}/SKILL.md` section 1, and the "Pillar index" paragraph in `{{SKILL_DIR}}/pillars.md`. Spec format: the header of `{{SKILL_DIR}}/index.sh`. Follow them.
- Re-design: {{REDESIGN}}. If it is not `none`, the run is under way and this index stopped moving. Design v<n+1> so it moves again, or reply `INDEX: none`. Keep each component you drop as a retired line: weight 0, and in the base column its value at Bk plus the spread on its worse side.

## Write nothing

The user has not confirmed the plan yet. Write nothing in the repository, in the run directory or anywhere else, except the system temp dir (`${TMPDIR:-/tmp}`). Never edit the project's code. Do not run a candidate that writes into the repository (build output, caches, installs); put it under DROPPED with that reason. Mid-run, the one exception: write SPEC to the v<n+1> path that Re-design names.

## How to work

Deadline: **{{DEADLINE}}** (check it with `date +%H:%M:%S`). Give every Bash call an explicit `timeout` of at most {{T_TEST}} seconds. If you get a message that starts with `TIME UP`, reply at once with what you have.

1. List candidate components from the targets, `pillars.md` and the tools the repo already has.
2. Run each candidate 3 times, output to the temp dir. Three equal values make it deterministic. Drop a candidate that fails, varies more than it can move, or breaks a component rule.
3. Keep 2–4 components. Name each in plain words: what it counts or times. Give each the component that opposes it, or the CORRECT_CMD check. Weights are equal unless a reason in DROPPED or GAMING says otherwise. One whole index run, all components in turn, must fit {{T_TEST}} seconds: report it as RUN_TIME, or drop the slowest component.
4. A paid component goes under DROPPED with its cost per measurement; the user can turn it on in the plan.
5. With fewer than 2 components left, reply `INDEX: none` with the reason.

## Reply

End with exactly this block and nothing after it. SPEC uses the index.sh format, with your measured median in the base column; setup measures the base again on B0.

```
PILLAR: <pillar>
INDEX: usable | none — <reason>
VERSION: v1, or v<n+1> mid-run
MEASURES: <one plain sentence, no formula: what the index measures>
COMPONENTS:
  <name: what is counted or timed> | <command> | <unit> | <lower or higher> | <floor> | <weight> | <deterministic yes or no> | <opposed by>
HELD_OUT: <the input, screen or task kept out of every component, when three or more exist> | none
LOCK: on | off
RUN_TIME: <seconds of one whole index run>
SPEC:
  <one tab-separated line per component, in the index.sh format>
DROPPED:
  <candidate> — <reason>
GAMING: <ways to raise the index without a better pillar, beyond the pillar's gaming list>
```
