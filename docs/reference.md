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
`scan --format json` emits annotation objects with `handle`, `path`, and `line`; `scan --diff` limits output to annotations absent from the committed ledger.
`report --format github` emits a Markdown table with implementation, verification, documentation, and role-aware status columns.
`migrate` is deprecated V1 transition support. The default `legacy_form` policy is `reject`.

## Self-Tracing

Reqtrace traces its own implementation as a case study. Generated occurrence IDs and positional diffs show evidence location only; they do not validate requirement meaning.
