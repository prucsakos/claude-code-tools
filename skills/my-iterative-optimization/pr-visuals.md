# PR visuals template

The "Progress" section of the patch note (SKILL.md section 3, Pull request) shows how the run changed the project: charts of the indexes and metrics per baseline, and screenshots of the UI before and after. Build it from STATE only: the baselines table, each Bk's component values and the idea rows. GitHub renders the `mermaid` blocks below in the PR body, also in a private repository, so charts need no image hosting. Fill every `<…>`; a filled chart holds only numbers and names.

## What each pillar's reviewer sees

One `### <Pillar>` heading per pillar, then the visuals of its targets in the order of this table. Each visual answers what a reviewer of that pillar approves the PR on. Leave out a chart with fewer than 2 baselines.

| The pillar has | Visual | Template |
|---|---|---|
| an index | the index per Bk, with each weighted component's score on the same scale | Index chart |
| an optimize target | its value per Bk, in its unit | Metric chart |
| EVIDENCE_CMD screenshots | each key page at B0 and at the latest Bk, side by side | Screenshots |
| build or judged targets | the items in MAIN after each Bk, one line per target | Items chart |

Under each chart, one line in words, with numbers from the baselines table: what got better or worse, and what drove it. `Index UX v1: 100 → 131 at B5, mostly from words on key screens (2.1× vs B0); load time stayed within its spread.` A reviewer can check the claim without reading the chart.

## Rules for every chart

- One y-axis per chart. Values of different units never share a chart: an index chart draws scores, which all have the index's scale, and a metric chart draws one target.
- One chart per index version. Versions are never compared, so a re-designed index starts a new chart at 100 at its base Bk.
- x-axis: the baselines in order, from the version's base (B0 for v1 and for a metric) to the latest Bk. With more than 20, keep the first, the latest and every second one between.
- The title names the series, its unit and its direction: `Performance: Speed, wall time in s (lower is better)`.
- Every chart starts with the `%%{init…}%%` line of the templates below: without it, GitHub draws the first line in a pale color that is hard to see on its light background. The five colors stay apart for color-blind readers on GitHub's light and dark backgrounds, in this order.
- Two or more lines: Mermaid draws no legend, so under the chart name each line by its color, in the order of the `line` rows.
- A count or size chart starts its y-axis at 0, so a small change does not look large. A score chart leaves the range out, so the chart fits the data.
- Values with at most 3 significant digits.

## Index chart

A component's score is its ratio against the version's base Bk, computed as in `index.sh` (capped at 4× and 1/4×), times 100. The index is the weighted geometric mean of the scores, so the chart shows which component moved it.

```mermaid
%%{init: {"themeVariables": {"xyChart": {"plotColorPalette": "#3987e5, #d95926, #199e70, #c98500, #d55181"}}}}%%
xychart-beta
    title "Index <Pillar> v<n>, score (higher is better, 100 = B<base>)"
    x-axis [<B<base>>, …, <Bk>]
    y-axis "score"
    line [<index per Bk>]
    line [<score of component 1 per Bk>]
    line [<score of component 2 per Bk>]
```

Colors: blue = index · orange = <component 1> · aqua = <component 2> · yellow = <component 3> · magenta = <component 4>.

## Metric chart

```mermaid
%%{init: {"themeVariables": {"xyChart": {"plotColorPalette": "#3987e5, #d95926, #199e70, #c98500, #d55181"}}}}%%
xychart-beta
    title "<Pillar>: <Target>, <metric> in <unit> (<lower or higher> is better)"
    x-axis [B0, …, <Bk>]
    y-axis "<unit>" 0 --> <the largest value × 1.1>
    line [<value per Bk>]
```

For a value that only goes up and down by small steps, such as a score in %, leave out `0 --> <…>`. A held-out input or a guardrail is a target of its own: give it its own chart only when STATE recorded `does not generalize` or `guardrail regressed` for it.

## Screenshots

The images load from the shots branch (SKILL.md section 3, Pull request). `<sha>` is that branch's latest commit; `<file>` is the screenshot's file name, the same in every Bk folder. One row per key page and width; with more than 6 rows, keep the pages that items in MAIN changed.

| Page and width | B0 | <Bk> |
|---|---|---|
| <page>, <phone or desktop> | ![<page> at B0](https://github.com/<owner>/<repo>/blob/<sha>/B0/<file>?raw=true) | ![<page> at <Bk>](https://github.com/<owner>/<repo>/blob/<sha>/<Bk>/<file>?raw=true) |

## Items chart

```mermaid
%%{init: {"themeVariables": {"xyChart": {"plotColorPalette": "#3987e5, #d95926, #199e70, #c98500, #d55181"}}}}%%
xychart-beta
    title "<Pillar>, items in MAIN (higher is more done)"
    x-axis [B0, …, <Bk>]
    y-axis "items" 0 --> <the largest cap or list length>
    line [<items of target 1 in MAIN per Bk>]
    line [<items of target 2 in MAIN per Bk>]
```

Colors: blue = <target 1> (cap <cap>) · orange = <target 2> (cap <cap>).
