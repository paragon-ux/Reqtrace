# Reqtrace

Reqtrace records implementation evidence against an existing upstream handle. It scans source markers and generates a JSONL trace ledger; it does not define or interpret handles.

## Marker

<code>@reqtrace &lt;HANDLE&gt;</code>

Place one marker per line near source, test, or documentation evidence. There are no ordinals and no `@file` placeholder.

## Workflow

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
