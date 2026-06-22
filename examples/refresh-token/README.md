# Refresh Token Example

Demonstrates Reqtrace tracing a single requirement (`AUTH-SESSION-ROTATION`)
across implementation and test files.

## Structure

```
src/revocation.js    — Token revocation logic
src/rotation.js      — Token rotation logic
src/validation.js    — Token validation logic
tests/rotation.test.js — Rotation test coverage
```

## Usage

From the repo root:

```bash
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict
python scripts/reqtrace.py report
```

The ledger block in `docs/requirements.md` is rendered by `reqtrace render`.
