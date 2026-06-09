# Reqtrace

Reqtrace is a grep-native convention for tracing implementation evidence back to an existing requirement.

Reqtrace starts **after** a requirement handle already exists. That handle may come from a spec, ticket, PRD, issue, SDD artifact, or plain Markdown documentation. Reqtrace does not create, rename, split, supersede, or interpret requirements.

## What Reqtrace Adds

Reqtrace adds one reserved structural marker:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

The marker is placed near implementation or test evidence. The requirement remains defined upstream.

The ordinal is an **implementation ordinal**, not a sub-requirement. It identifies one validated implementation occurrence under the requirement handle.

## Two-stage Loop

1. **Implementation pass** — implement normally and add `@reqtrace` handles near relevant implementation or test evidence.
2. **Ledger pass** — grep the requirement handle, validate each occurrence against the existing requirement, then append the resolved traces to the requirement's trace ledger.

The ledger pass is mandatory. A trace is not complete until its expanded form is recorded in the ledger or the unresolved handle is removed.

## Basic Syntax

Code comments carry unresolved handles:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

Documentation ledgers carry resolved traces:

```txt
<REQUIREMENT>/<ORDINAL>/<repo-relative-file-path>
```

For example, this code comment:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

in `examples/refresh-token/src/validation.js` resolves to:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Grep First

Reqtrace works with normal repository tools:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTATION" .
grep -R "@reqtrace AUTH-SESSION-ROTATION/003" .
```

The path returned by grep supplies the file occurrence. No graph lookup is required.

## What Reqtrace Is Not

Reqtrace is not:

- a requirements generator
- a replacement for SDD tools
- a requirement-governance process
- a wiki-link system
- a graph server
- a reverse index database
- a documentation framework

It is a small convention for making implementation evidence easy to find, validate, and record.

## Optional Validation

This demo can include a dependency-free validator:

```bash
python scripts/validate_reqtrace.py
```

The validator expands `@file` to the current repo-relative file path and checks that expanded traces match the requirement ledger.
