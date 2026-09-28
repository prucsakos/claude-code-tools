---
description: Review the changes and aggressively simplify the implementation and its tests, preserving behavior
argument-hint: "optional scope (files, folder, PR); defaults to the current changes"
---

Scope: $ARGUMENTS (if empty, the current changes)

Review the changes and aggressively simplify the implementation.

Goals:
- Reduce total LOC where possible.
- Delete dead, redundant, duplicated, speculative, or unnecessary code.
- Collapse unnecessary abstractions, wrappers, helpers, and indirection.
- Prefer straightforward implementations over highly modular ones when the abstraction has only one meaningful use.
- Remove defensive code for impossible/unrealistic states unless required by an external boundary.
- Consolidate repeated logic instead of adding more layers.

Tests:
- Remove tests that merely verify implementation details.
- Remove tests for trivial getters/setters, obvious language/framework behavior, and redundant permutations.
- Merge highly similar tests into representative behavioral tests.
- Prefer tests of externally observable behavior and important invariants.
- Keep regression tests for real bugs and meaningful edge cases.
- Do not optimize for test count or coverage percentage.

Constraints:
- Preserve externally observable behavior.
- Preserve public APIs unless changing them clearly simplifies the system and all consumers can be updated safely.
- Do not remove meaningful validation, security checks, concurrency protections, or important edge-case handling.

Process:
1. Identify simplification candidates.
2. Delete or consolidate code.
3. Simplify the remaining implementation.
4. Prune/consolidate tests.
5. Run the relevant test suite and static checks.
6. Review the final diff again specifically looking for code that can now be deleted.

Prefer deleting code over adding new abstractions.

Report:
- LOC before
- LOC after
- tests before
- tests after
- major things removed
- anything you deliberately kept despite appearing redundant, and why
