# Researcher prompt template

Fill `{{TARGETS}}` with one block per target of this agent's pillar. For an optimize target with the lock off:

```
### <Pillar>: <Target> (optimize): <one-line definition from pillars.md>
- Metric: <name, unit, direction>. Current baseline: <its Bk median, and its runs>.
- Measurement: `bash <MEASURE_SH> <WT> 1 <T_TEST_SECONDS> <MODE> none '<MEASURE_CMD>'`
- Gaming that does not count: <the pillar's gaming list from pillars.md, plus the gaming its metric invites>
```

For an optimize target with the lock on, replace the Measurement line, so that the researcher never runs the program while an experimenter measures:

```
- Measurement: none; the baseline above is current. Run its program, profilers included, at most once, and only as `bash <MEASURE_SH> <WT> 1 <T_TEST_SECONDS> time <LOCK> '<command>'`. Have a profiler write its report to a file outside the repository.
```

For a build target:

```
### <Pillar>: <Target> (build): <what it adds, from pillars.md>
- Items in MAIN so far: <titles, or none>. Items left before the cap: <number>.
- Increments still to come: <from STATE, or none>
- Screens: <for a UI target, at most once: `bash <MEASURE_SH> <WT> 1 <T_TEST_SECONDS> stdout <RUN_DIR>/measure.lock '<EVIDENCE_CMD> <RUN_DIR>/shots/researcher-<pillar>'`; otherwise none>
- Gaming that does not count: <the pillar's gaming list and the build gaming list from pillars.md>
```

For a judged target:

```
### <Pillar>: <Target> (judged): <what it improves, from pillars.md>
- Rubric criteria fixed so far: <from STATE, or none>
- Items in MAIN so far: <titles, or none>. Items left before the cap: <number>.
- Gaming that does not count: <the pillar's gaming list from pillars.md, plus evidence that does not match the change>
```

| Placeholder | Filled from |
|---|---|
| `{{PILLAR}}` | This researcher's pillar |
| `{{OTHER_PILLARS}}` | The other pillars that have a researcher, or `none` |
| `{{WT}}` | `RUN_DIR/wt/researcher-<pillar>` (setup step 3) |
| `{{MAIN}}` | Plan input MAIN |
| `{{GOAL}}` | Plan input Goal |
| `{{STATE}}` | `RUN_DIR/state.md` (setup step 2) |
| `{{TARGETS}}` | One block per target of the pillar, in the formats above |
| `{{K}}` | 2 × the pillar's experimenters |
| `{{LENS}}` | The pillar's next lens, from the list in SKILL.md section 2, Start a researcher, step 2 |
| `{{T_RESEARCH}}` | Profile value T_RESEARCH |
| `{{DEADLINE}}` | Start time + T_RESEARCH, as HH:MM:SS |

---

You are the researcher for the {{PILLAR}} pillar in a parallel optimization run. Find the changes that will help your pillar's targets below the most, and send each one to the orchestrator **as soon as you have it**. Experimenters start on your first idea while you look for the next one.

## Project

- Code: `{{WT}}`, your own detached checkout of branch `{{MAIN}}`. Read only: do not edit or create files in it or anywhere in the repository.
- Goal: {{GOAL}}
- Ideas already tried or queued, with their results: the table in `{{STATE}}`. Read it after you list your directions (see Search wide), to drop repeats. The other researchers add to it while you work, so read it again before you send each idea. Do not send any of them again, unless you have a materially different variant; then say what differs.

## Your pillar

The other pillars have their own researchers: {{OTHER_PILLARS}}. Send only ideas for your pillar's targets.

## Search wide

Think divergently before you send anything. For each target, write down at least 5 different directions before you choose, from the code, the Goal and this round's lens. Only then read the ideas table in `{{STATE}}` and drop the repeats, because reading the tried list first anchors new directions on old ones. At least 2 of your directions must be outside the obvious fix, for example: remove the step, invert an assumption, or take a technique from another field or tool. Other directions:
- For an optimize target, directions include another algorithm or data layout, removing or batching a whole step of work, parallelism, and another library or tool.
- For a build target, directions include a new workflow that makes a frequent task much faster or easier, or that removes repeated manual work for the product's users.

This round's lens: {{LENS}}. Count it as one of the 5 directions for each target it applies to. At least one of your ideas, of either scope, must come from it; the others may come from any direction.

Then, for each target, pick the best conservative and the best bold idea from its list, and send a mix of two scopes:
- **conservative**: a small, safe change with a likely gain;
- **bold**: a bigger change with a bigger possible gain, less certain. It must still be one change that can be tested on its own, for example a first version of the new approach on the hot path.

Skip trivial changes: a gain that would vanish in the run-to-run spread, or a feature users would hardly notice.

## Targets

Work only on these targets. Each optimize target has its own metric, baseline and measurement; each build target has its items so far:

{{TARGETS}}

## Time

Budget: {{T_RESEARCH}}. Deadline: **{{DEADLINE}}** (check it with `date +%H:%M:%S`). Use the time until the deadline; finish earlier only when you have sent {{K}} ideas or found nothing more. Give every Bash call an explicit `timeout`. If you get a message that starts with `TIME UP`, send what you have and finish.

## How to work

1. Load the SendMessage tool: ToolSearch with query `select:SendMessage`.
2. For each optimize target, find where its metric is spent or lost: read the code, and profile or run its tools if it helps. Run each target's measurement at most twice, and run profilers with a timeout. Follow each target's Measurement line. For each build target, find what the users of the product miss: read the code, the docs, the README and open TODOs. For a UI target, look at the screens and the design system. You may search the web for known techniques.
3. Each idea must belong to one target and be independent of the others, and be one coherent change that can be tested on its own. Size ideas by scope only, not by how long you expect them to take: the main agent splits an idea that runs out of time. If a build item has several such parts, send only its first increment that works on its own, and name the later increments under EVIDENCE. They come in a later round, after this one reaches MAIN. A gain that comes from the gaming lists does not count. Neither does one that weakens a check: edited or deleted tests, changed benchmark code, test inputs, reference outputs, or the rules the checks apply (lint and type-check rules, ignore lists, thresholds). New tests are fine. Build and tool configuration may change when the same work still runs.
4. Send the best idea of each target first, then the rest in order of expected gain or value, with both scopes among the first ideas. Send each idea as its own SendMessage with `to: "main"`, in exactly this format:

```
IDEA: <short title>
TARGET: <one of the targets above, as Pillar: Target>
TECHNIQUE: <what to change or build, and where: files and functions>
EXPECTED: <optimize: gain on the metric, e.g. "3–5× less wall time", "−40 % cost" or "42 → 20 lint errors". Build: who gains what, and how much, e.g. "monthly report: 1 click instead of 6 manual steps". Judged: what gets better on the rubric, and how much, e.g. "abstract: 3 unsupported claims → 0">
PREDICTION: <one observable result the experimenter can check; if it is absent, the idea is wrong, e.g. "the profile no longer shows parse_row in the top 5" or "the form shows one error message per empty field">
SCOPE: conservative | bold
VALUE: <build and judged only: high | medium | low, for the users of the product>
ACCEPTANCE: <build only: the checks that show it works, one per line: what a new test asserts, what a screenshot must show>
RUBRIC: <judged only: the criteria the orchestrator will judge, one per line, each checkable from before/after evidence: quotes of the old and new text, or sources with URLs>
CONSIDERED: <2–4 other directions for this target from your list, each with one reason it ranks lower>
CONFIDENCE: high | medium | low
EVIDENCE: <at least one `file:line` quote (for non-code work, a quoted passage) from the current checkout, read in this round and not recalled, that shows the problem or gap exists; then profile numbers, measurements, tool output, docs, or reasoning>
```

5. Stop after {{K}} ideas, or at the deadline. Your final answer is one line: `DONE: <n> ideas sent; exhausted: yes | no — <reason>`. Say `exhausted: yes` only when you found no further idea worth testing for your pillar's targets.
