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
`check --strict` rejects handles that are absent from the registry or still typed as `unknown`.
`generate --register-unknown` is available for discovery, not strict validation.

## Edge Cases

Multiple markers on a line fail validation. Legacy annotations are warned or rejected by `legacy_form`.
For moved files, run `generate` and `render`; do not edit the ledger manually.
`check` reports stale or malformed ledgers, and generation expands occurrence IDs if a short hash collides.
