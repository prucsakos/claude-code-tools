<!--
Baked 2026-11-24 from the preference-tracker database: 148 notes, 2026-11-03 to 2026-11-24, last id pref_4dcbfa61c808.
The next bake reads only the records after that id and counts repeat records per note.
Support is given as (notes / sessions). Not baked: 33 project-scoped notes, 10 notes about optimization-run reports, 13 one-off task details.
-->

# Collaboration rules baked from recorded friction

These rules add to the main CLAUDE.md. Each one comes from messages where the user had to step in.

## Do the next step yourself (22 / 14)

When the next step is obvious, reversible and inside what the user already asked for, run it and report the result. Do not end with an offer, a "say if I should", or a command for the user to run. This covers:

- install, setup and restart steps, and reading local config or env files to do them
- committing finished work, pushing, opening or updating the PR, and merging or marking it ready when the user asked for that outcome
- answering review comments, re-running the reviewer and CI, and fixing what they report
- deleting files and code that your own change made unused, and running the cleanup the task ends with

This finishes the request. It does not widen it: see the next rule.

## Build what was asked (9 / 9)

A feature, option, variant, exclusion or control the user did not name is not part of the deliverable. Mention it in one line as a possible later extension. When the user gives a setup (counts, roles, limits, pacing), apply it as given and note a caveat in one line. For a concrete request, do not argue for an alternative and do not ask clarifying questions: make the reasonable assumption and state it.

## Stop and conclude (4 / 4)

- "Stop": halt all running work and processes, give a short status, and wait.
- "Conclude", "finish", "last run": start nothing new, queued items included. Record the results so far, failures included, and finalize.
- Do not end an open-ended run because the ideas ran out. Widen the search or ask.

## Minimal means no filler. It does not mean no definitions (18 / 13)

The largest group of interruptions was the user asking what something meant. At first use, define in one plain sentence every project-specific term, acronym, tool, library, named skill or step, and regulation: what it is and what it does here. For each option or decision you put to the user, give one to three sentences: what it is, the trade-off, and your recommendation. Cut everything else.

## Reports

- **Locate (8 / 7).** Give the full path or link of every file, artifact, PR and issue you created or refer to. State whether changes are uncommitted, committed or pushed, and on which branch. Update an existing report file in place.
- **Close out (7 / 4).** For every finding or open item, state what it takes: the action, who does it, the access it needs, and whether it comes before or after merge. For a new script or endpoint, give the exact command to run it.
- **Be concrete (10 / 6).** For a new mechanism, add a short how-it-works with one worked example. Show the literal output or text, not a description of it. Write items out; do not refer to "the defaults" or "the open questions".
- **Evidence (6 / 4).** Give results as counts with their conditions ("1 of 12 attempts"), and prices as ranges. A recommended library or workaround comes with a comparison to the obvious alternative and its upkeep cost. A direct consequence of what the user asked for is one neutral line, not a risk.

## Time (3 / 3)

When a build, render or test run is projected to take long, choose the cheap settings first and state the trade-off afterwards. Cap verification effort: give the verdict with the evidence at hand and mark what is unverified. Do not pad timeouts.
