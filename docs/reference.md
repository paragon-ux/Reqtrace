# Reference

## Handle Grammar

<code>@reqtrace &lt;HANDLE&gt;</code>

`HANDLE` matches uppercase alphanumeric segments separated by hyphens, such as `ADR-0012` and `SEC-CONTROL-7`.
Use one marker per line. IDs, paths, and line numbers are derived during generation.

## Role Inference

The first matching `role_map` path pattern determines each ledger record's `kind`.
The default map covers source, test, documentation, migration, infrastructure, and deployment paths.
Configure or override patterns in [`.reqtrace.json`](https://github.com/paragon-ux/Reqtrace/blob/main/.reqtrace.json).

## Registry

`docs/handle-registry.jsonl` lists known handles with a type and optional source.
Registry metadata is optional for ledger generation and `check` freshness validation.
`check --strict` uses the configured policy, which is `ledger` by default; `check --strict=ledger` forces freshness-only validation.
Use `check --strict=full` to also reject missing or `unknown` registry types.

## Edge Cases

Multiple markers on a line fail validation. Legacy annotations are warned or rejected by `legacy_form`.
For moved files, run `generate` and `render`; do not edit the ledger manually.
`check` reports stale or malformed ledgers, and generation expands occurrence IDs if a short hash collides.

## Commands

`init` writes a starter `.reqtrace.json`, empty registry, and empty ledger after detecting `src/`, `tests/`, `docs/`, `lib/`, and `app/` directories. It does not create handles.
`scan --format json` emits annotation objects with `handle`, `path`, `line`, `kind`, and `id`; the last two are `null` without a matching ledger record. `scan --diff` limits output to annotations absent from the committed ledger.
`report --format github` emits a Markdown table with implementation, verification, documentation, and role-aware status columns.
`report --format json` emits the versioned coverage envelope documented in [`schema.md`](schema.md). `check --format json` emits a machine-readable pass or failure status.
`register <HANDLE> [--type TYPE] [--source PATH]` appends one validated registry record and prints a paste-ready marker.
`migrate` is deprecated V1 transition support. The default `legacy_form` policy is `reject`.

## Self-Tracing

Reqtrace traces its own implementation as a case study. The `TRD-*` markers in `scripts/reqtrace.py` demonstrate the evidence convention on the tool's own codebase. Generated occurrence IDs and positional diffs show evidence location only; they do not validate requirement meaning. This self-tracing is a demonstration, not a recommendation for production self-tracing without meaningful upstream requirements.

## Document Hierarchy Enforcement

When `doc_hierarchy` is set in `.reqtrace.json` (e.g.
`["BRD", "ARD", "DRD", "TRD"]`), `check` enforces two additional rules on
`implementation`-kind records:

**`E_OFFLEAF_HANDLE`** - fires when an implementation annotation's handle
prefix is not the last entry in `doc_hierarchy`. Implementation code must
trace to the leaf document only.

```
E_OFFLEAF_HANDLE BRD-1 at src/widget.py:4 (expected leaf: TRD)
```

**`E_MULTI_HANDLE_EVIDENCE`** - fires when two or more consecutive
implementation annotations in the same file reference different handles
(gap between line numbers ≤ 1). Each evidence block must name exactly one
handle.

```
E_MULTI_HANDLE_EVIDENCE src/widget.py:10-11 has 2 handles: TRD-4, TRD-5
```

Both rules fire regardless of `--strict` level. An empty `doc_hierarchy`
list disables enforcement entirely.

## Registry Source Validation

`check --strict=full` also validates that every registry entry with a
`source` field points to a file that exists on disk.

**`E_REGISTRY_SOURCE_MISSING`** - fires when a registry entry's `source`
path does not resolve to a real file relative to the project root. Entries
with no `source` field are exempt.

```
E_REGISTRY_SOURCE_MISSING TRD-99 (source: docs/missing.md not found)
```

Fix by updating the `source` field in `docs/handle-registry.jsonl` to a
file that exists, or by removing the `source` field if the handle has no
authoritative document yet.
