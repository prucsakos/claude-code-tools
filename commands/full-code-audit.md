---
description: Load all production source code from a folder into context, verbatim and unanalyzed, excluding comments, tests, docs, generated files, and vendor directories
argument-hint: "path to the folder to load"
---

# Load Code Context

Load all production source code from: `$ARGUMENTS`

## Rules

- Recursively read every source-code file in the target folder.
- Load the actual code into the model context.
- Exclude:
  - comments
  - tests/specs
  - documentation
  - generated files
  - build artifacts
  - dependencies/vendor directories
- Preserve file paths and boundaries between files.
- Do not summarize, analyze, modify, or omit production code.
- Do not replace code with descriptions.
- Continue until all eligible code in the folder has been loaded.

If everything cannot fit in context, report that explicitly instead of silently dropping files.
