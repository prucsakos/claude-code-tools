---
description: Audit all production code in a folder for duplication, inconsistent patterns, and architectural problems
argument-hint: "path to the folder to audit"
---

# Full-Code Audit

Audit all production code inside: `$ARGUMENTS`

## Instructions

1. Recursively load all production source code in the target folder into context.
2. Exclude:
   - tests/specs
   - comments
   - generated/vendor/build files
   - documentation
3. Preserve file paths and code structure.
4. Do not modify code.

Analyze the codebase globally, comparing implementations across files.

Find:
- duplicated or redundant implementations
- inconsistent patterns or conventions
- unnecessary complexity
- poor abstractions
- architectural inconsistencies
- dependency/layering problems
- obsolete or competing approaches
- opportunities to consolidate or simplify

Infer the project's dominant conventions from the code itself rather than imposing arbitrary style preferences.

For every finding provide:
- files/locations
- what is inconsistent or suboptimal
- evidence/comparison
- recommended canonical approach
- confidence

Prioritize high-impact findings and avoid cosmetic issues.

If the code does not fit in context, process coherent modules separately, build a compact architectural index, then perform the same cross-module analysis.
