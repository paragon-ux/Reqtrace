# Reqtrace Docs Patch Summary

This patch updates the Reqtrace Markdown documentation for MkDocs.

## Changed files

- `README.md`
- `docs/index.md`
- `docs/concept.md`
- `docs/syntax.md`
- `docs/rules.md`
- `docs/edge-cases.md`
- `docs/requirements.md`

## New files

- `docs/workflow.md`

## Main documentation changes

- Made the mandatory trace-ledger pass more explicit.
- Clarified that ordinals are implementation ordinals, not sub-requirements.
- Clarified that code comments keep `@file` literal and documentation ledgers store resolved paths.
- Added a workflow page for implementation pass, ledger pass, and PR review.
- Expanded edge cases with paired **Incorrect** and **Correct** examples for duplicate ordinals, hardcoded paths, ledger drift, renames, file moves, generated files, and test/source role inference.
