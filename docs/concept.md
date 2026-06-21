# Concept

Reqtrace avoids a second system of record. Its source markers travel with code and are always searchable with normal repository tools. Its generated JSONL ledger is deterministic, diffable, and still searchable with `grep`.

## Boundary

Reqtrace begins only after an upstream source has supplied a handle. It records evidence against that handle; it does not decide what the handle means or whether the evidence is semantically correct. That judgment belongs in code review.

## Scope

The marker grammar is the same for every handle type. A registry entry identifies the handle's type and source, so adding an ADR or security-control handle never requires a parser change.

## Why Grep Still Matters

The CLI automates generation, validation, and coverage reporting, but it is not required to find a trace:

```bash
grep -R "@reqtrace " .
grep -R "SEC-CONTROL-7" .
```

No graph server, database, daemon, or network call is involved.
