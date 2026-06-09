# Reqtrace Docs Patch Summary

This ZIP contains a direct Markdown patch for the Reqtrace demo docs.

## Updated files

- `README.md`
- `docs/index.md`
- `docs/concept.md`
- `docs/syntax.md`
- `docs/rules.md`
- `docs/edge-cases.md`
- `docs/requirements.md`

## New files

- `docs/workflow.md`

## Main changes

- Made the mandatory ledger pass explicit.
- Replaced “sub-requirement” language with “implementation ordinal.”
- Clarified that `@file` remains literal in code and expands only when documented.
- Added role inference from file path instead of separate hooks.
- Added duplicate ordinal, rename, semantic replacement, file move, and missing trace edge cases.
- Added a workflow page with implementation pass, ledger pass, and PR review checklist.
