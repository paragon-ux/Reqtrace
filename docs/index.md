# Reqtrace

Reqtrace records source evidence against an existing upstream handle. It scans one marker syntax and generates a sorted JSONL ledger; it does not define or interpret handles.

## 60-Second Quickstart

Add one marker near source or test evidence. Use a handle that already exists upstream.

```txt
@reqtrace <HANDLE>
```

Generate the ledger, then validate freshness:

```bash
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict
```

`render` refreshes Markdown ledger blocks. `report` summarizes observed evidence roles. `scan` is diagnostic output, not a workflow step.

## Complete Workflow

```bash
python scripts/reqtrace.py generate
python scripts/reqtrace.py render
python scripts/reqtrace.py check --strict
python scripts/reqtrace.py report
```

## Search

```bash
grep -R "@reqtrace " .
```
