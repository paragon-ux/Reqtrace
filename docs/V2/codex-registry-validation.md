# Reqtrace V2 — Registry Source Validation Feature

## Context

Registry entries carry a `source` field pointing to the document that
defines the handle. Currently `check` never validates this field — when a
document moves or is deleted, the registry rots silently. This feature makes
the `source` field load-bearing.

---

## New error: `E_REGISTRY_SOURCE_MISSING`

### Behaviour

During `check --strict=full`, for every registry entry that has a `source`
field, resolve the path relative to the project root. If the file does not
exist on disk, emit:

    E_REGISTRY_SOURCE_MISSING {handle} (source: {source} not found)

This counts as a failure (exit 1). Entries with no `source` field (e.g.
handles registered by `generate --register-unknown` which default to
`type: unknown`) are exempt — they have no document to validate.

### Implementation location

Inside `command_check`, within the `strict_level == "full"` block, after the
existing `E_HANDLE_NOT_REGISTERED` loop.

    if strict_level == "full":
        registry, registry_errors = read_registry(...)
        ...
        for entry in registry:
            source = entry.get("source")
            if source and not (root / source).exists():
                print(
                    f"E_REGISTRY_SOURCE_MISSING {entry['handle']} "
                    f"(source: {source} not found)",
                    file=sys.stderr,
                )
                failures = True

---

## Document lifecycle behaviour

| Event | Errors fired |
|---|---|
| Document moves | E_REGISTRY_SOURCE_MISSING |
| Document deleted, handles retired | E_REGISTRY_SOURCE_MISSING + E_HANDLE_NOT_REGISTERED |
| Document replaced by new doc with new identity | Both errors fire on old handles, forcing cleanup |
| Document updated in place | No error |
| Entry has no source field | No error (exempt) |

---

## Tests

Add to `tests/test_edge_cases.py` or a new `tests/test_registry_source.py`:

- Registry entry has source pointing to an existing file -> check --strict=full exits 0
- Registry entry has source pointing to a non-existent file -> check --strict=full exits 1, E_REGISTRY_SOURCE_MISSING in stderr
- Registry entry has no source field -> check --strict=full exits 0 (exempt)
- Multiple entries, one missing source -> only that handle is reported, others pass

---

## Current repo cleanup required

After implementing, run `check --strict=full`. Every registry entry whose
source document was moved out of the repo will fire E_REGISTRY_SOURCE_MISSING.
For each:

- If the document now lives elsewhere in the repo: update the `source` field
  in `docs/handle-registry.jsonl` to the new path.
- If the document is gone permanently: remove the entry from the registry and
  remove any corresponding annotations from source files.

---

## Summary

| File | Change |
|---|---|
| scripts/reqtrace.py | Add E_REGISTRY_SOURCE_MISSING check inside the strict=full block of command_check |
| tests/ | Add tests covering present source, missing source, and no source field |
| docs/handle-registry.jsonl | Update or remove stale source paths after implementation |