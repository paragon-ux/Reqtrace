# Syntax

Reqtrace has one code marker:

```txt
@reqtrace <handle>
```

Use one marker per line. The marker is placed near implementation, verification, operational, migration, or documentation evidence; its role is inferred from the configured path map.

## Handle Grammar

```txt
HANDLE = [A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*
```

This permits handles such as `ADR-0012`, `SEC-CONTROL-7`, and `TRD-12`. The validator is the single implementation of this grammar.

```python
TRACE_RE = r"@reqtrace\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\b"
```

There is no ordinal and no file placeholder. The generator derives a short ID from the repo-relative path and 1-indexed line number, then stores a JSONL record containing `handle`, `id`, `path`, `line`, and `kind`.

## Search

Search all annotations:

```bash
grep -R "@reqtrace " .
```

Search a known handle:

```bash
grep -R "$HANDLE" .
```

The legacy V1 form is recognized only for migration and deprecation reporting. Configure `legacy_form` as `warn` or `reject` in `.reqtrace.json`.
