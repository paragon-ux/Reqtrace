# Workflow

Reqtrace is a two-stage loop that starts from an existing requirement handle.

## Before Reqtrace

Some upstream process supplies a requirement handle, such as:

```txt
AUTH-SESSION-ROTATION
```

That process may be a spec, ticket, PRD, issue, SDD toolkit, or documentation page. Reqtrace does not create or judge the requirement.

## Stage 1: Implementation Pass

Implement normally. Near important implementation or test evidence, add unresolved Reqtrace handles:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Use new ordinals for distinct occurrences:

```js
// @reqtrace AUTH-SESSION-ROTATION/002/@file
```

The ordinal is only an implementation ordinal. It is not a new requirement and not a sub-requirement.

## Stage 2: Mandatory Ledger Pass

After implementation, grep the requirement handle:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTATION" .
```

For each result:

1. Read the surrounding code.
2. Validate that the occurrence is relevant to the existing requirement.
3. Expand `@file` to the repo-relative file path.
4. Append the resolved trace to the requirement's trace ledger.
5. Remove or fix invalid traces.

Example grep result:

```txt
examples/refresh-token/src/validation.js:// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Resolved ledger entry:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## PR Review Checklist

A reviewer or PR agent should check:

- Does every new `@reqtrace` handle use an existing requirement handle?
- Does every ordinal identify one distinct implementation occurrence?
- Are duplicate ordinals accidental? If so, renumber or remove them.
- Does every valid occurrence appear in the trace ledger?
- Did behavior change in a way that should add, update, or remove trace evidence?
- Did the upstream requirement handle change? If so, are code handles and ledger entries updated together?

## Minimal Command Set

Reqtrace does not require custom commands. These are enough:

```bash
grep -R "@reqtrace" .
grep -R "@reqtrace AUTH-SESSION-ROTATION" .
grep -R "@reqtrace AUTH-SESSION-ROTATION/003" .
```
