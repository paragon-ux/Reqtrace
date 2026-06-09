# Reqtrace

Reqtrace is a grep-native convention for tracing code implementation evidence back to existing requirements.

Reqtrace does not generate requirements, replace SDD tools, require a server, or maintain a graph index. It gives implementation work a grep-able return path to whatever requirement process you already use.

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

The requirement name remains unchanged. The ordinal is an implementation ordinal, not a sub-requirement.

## Grep First

Reqtrace works with normal repository tools:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTAsTION" .
grep -R "@reqtrace AUTH-SESSION-ROTATION/003" .
```

After implementation, the second stage is mandatory: validate every expanded trace against the requirement, then append the validated expanded traces to the requirement documentation's trace ledger.

--- 

> ### Reqtrace does not replace your requirements process; it gives implementation work a grep-able return path to whatever requirement process you already use.

--- 

## Optional Validation

This demo includes a dependency-free validator:

```bash
python scripts/validate_reqtrace.py
```

The validator expands `@file` to the current repo-relative file path and checks that the expanded traces match `docs/requirements.md`.
