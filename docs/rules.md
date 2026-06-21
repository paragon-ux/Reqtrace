# Rules

1. A handle must already exist in an upstream source or task context.
2. Reqtrace never creates, renames, splits, supersedes, or interprets handles.
3. Use only the `@reqtrace` marker; do not add role-specific hook names.
4. Put at most one valid marker on a line.
5. Keep the annotation payload to the handle: no ordinal and no `@file` placeholder.
6. Treat `docs/trace-ledger.jsonl` and Markdown ledger blocks as generator-owned.
7. Run `generate`, `render`, and `check` after changing evidence.
8. Use `check --strict` before merging; it rejects stale ledgers and unregistered or unknown handles.
9. For a moved file, regenerate rather than editing the ledger path by hand.
10. For an invalid trace, remove the source marker rather than relabeling it silently.
11. Keep the convention grep-native: no claims, parent fields, wiki links, JSON references, custom hook names, server, daemon, database, or graph resolver.

## Role Inference

The first matching `role_map` pattern in `.reqtrace.json` determines the generated `kind`. The defaults cover common source, test, documentation, migration, infrastructure, and deployment paths; repositories can override the map without changing the parser.

## Registry

`docs/handle-registry.jsonl` contains one JSON object per known handle with a `handle`, `type`, and optional upstream `source`. `generate --register-unknown` is an on-ramp for discovery, but an `unknown` type does not satisfy `check --strict`.
