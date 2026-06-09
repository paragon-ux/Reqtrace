# Agent Guidance

Reqtrace is intentionally small. Keep it grep-native.

## Rules

- Do not invent new canonical requirements in code.
- Use existing requirement handles from docs or task context.
- Use `@reqtrace <REQUIREMENT>/<ORDINAL>/@file` near implementation evidence.
- Do not add claims, parent fields, wiki links, JSON refs, or custom hook names.
- Resolve the filepath from the current file.
- After implementation, grep the requirement handle.
- Validate every occurrence against the requirement.
- Append validated expanded traces to `docs/requirements.md`.
- Remove invalid or accidental traces.
- Keep Reqtrace grep-native.
