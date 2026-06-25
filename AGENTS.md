# Agent Guidance

Reqtrace is intentionally small. Keep it grep-native.

## Scenario 1: Annotating New Code

- Do not invent new canonical handles in code.
- Use existing handles from `docs/handle-registry.jsonl` or task context.
- Use `@reqtrace <HANDLE>` near implementation or test evidence. One marker per line.
- Do not add ordinals, `@file`, claims, parent fields, wiki links, JSON refs, or custom hook names.
- If no registry entry exists for the handle, ask before annotating; do not silently register it.
- When adding a `@reqtrace` marker, preserve existing explanatory comments. Do not use a marker as a substitute for comments that explain intent, invariants, edge cases, tradeoffs, or security assumptions.
- If the target function has nontrivial logic and no existing explanatory comment, note that an explanatory comment is also needed alongside the marker.

## Scenario 2: Running and Interpreting the Validator

- After implementation, run `python scripts/reqtrace.py check`.
- If `check` reports drift, run `python scripts/reqtrace.py generate` and `render`, then re-run `check`.
- Never hand-edit `docs/trace-ledger.jsonl` or the generated block inside any `docs/*.md` file.
- A non-zero exit from `check --strict` blocks the change; do not bypass it.

## Scenario 3: Handling Stale or Invalid Traces

- Run `python scripts/reqtrace.py report` to see zero, partial, and full coverage handles.
- For a stale path (file moved or renamed), re-run `generate` and `render`; do not manually patch the ledger.
- For an invalid or accidental trace, remove the `@reqtrace` marker from source, then re-run `generate`.
- Do not silently rewrite a handle to a different one; surface the question to a human or the upstream artifact source.

## Scenario 4: Adding a New Requirement Handle

- Confirm the canonical handle exists in its upstream artifact before using it; Reqtrace does not create it.
- Add its `handle`, `type`, and optional `source` to `docs/handle-registry.jsonl` when registry metadata is required.
- Annotate evidence, run `generate` and `render`, then use `check --strict=full` to verify the registry entry.

## Boundary

- Reqtrace does not create, rename, or interpret handles.
- Reqtrace does not require a server, daemon, database, or graph resolver.
- Keep Reqtrace grep-native.
