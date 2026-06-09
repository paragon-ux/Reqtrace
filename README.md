# Reqtrace

Reqtrace is a grep-native convention for tracing code implementation evidence back to existing requirements.

Reqtrace does not generate requirements, replace SDD tools, require a server, or maintain a graph index. It gives implementation work a grep-able return path to whatever requirement process you already use.

## What Reqtrace Adds

Reqtrace adds one reserved structural marker:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

That marker is placed near implementation or test evidence. The requirement remains defined elsewhere: in a spec, ticket, PRD, Markdown page, SDD artifact, or issue.

The ordinal is an **implementation ordinal**, not a sub-requirement. It identifies a validated occurrence of implementation evidence under the requirement handle.

## Two-stage Workflow

Reqtrace has two stages:

1. **Implementation pass** — implement normally and add `@reqtrace` handles near relevant implementation or test evidence.
2. **Ledger pass** — grep the requirement handle, validate each occurrence against the requirement, then append the resolved traces to the requirement documentation's trace ledger.

The second stage is mandatory. A trace is not complete until its expanded form is recorded in the ledger.

## Basic Syntax

Code comments carry an unresolved handle:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

Documentation ledgers carry the resolved trace:

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

The path returned by grep supplies the file occurrence. No custom graph lookup is required.

## What Reqtrace Is Not

Reqtrace is not:

- a requirements generator
- a replacement for SDD tools
- a wiki-link system
- a graph server
- a reverse index database
- a documentation framework

It is a tiny convention for making implementation evidence easy to find and validate.

## Optional Validation

This demo can include a dependency-free validator:

```bash
python scripts/validate_reqtrace.py
```

The validator expands `@file` to the current repo-relative file path and checks that expanded traces match the requirement ledger.
