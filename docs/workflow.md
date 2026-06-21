# Workflow

Reqtrace has two mechanical stages.

## 1. Annotate

Implement normally and place one marker near valid evidence using an existing upstream handle. Do not choose ordinals, copy file paths, or update a ledger by hand.

## 2. Generate and Verify

Run:

```bash
python scripts/reqtrace.py generate
python scripts/reqtrace.py render
python scripts/reqtrace.py check --strict
```

`generate` scans source and rewrites `docs/trace-ledger.jsonl`. `render` rewrites only the content inside Markdown ledger markers. `check` compares a fresh scan with the committed ledger and, in strict mode, requires every handle to be explicitly registered.

## Review Boundary

The tool records every marker mechanically. Reviewers decide whether a marker is genuinely relevant evidence for its upstream artifact. Remove invalid markers from source, then generate and render again.

## Useful Commands

```bash
python scripts/reqtrace.py scan
python scripts/reqtrace.py report
python scripts/reqtrace.py report --format json
python scripts/reqtrace.py migrate --dry-run
```

The supplied pre-commit hook and GitHub Actions workflow run `check --strict` so a stale generated ledger cannot merge unnoticed.
