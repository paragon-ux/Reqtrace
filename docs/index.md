# Reqtrace

Reqtrace is a minimal convention for tracing implementation evidence back to an existing requirement.

The existing requirement remains the source of truth. Code comments contain only structural trace handles. Grep resolves backward references from code to requirement handles. The documentation ledger stores validated expanded handles after implementation work has been checked.

Reqtrace is deliberately small:

```txt
requirement handle + implementation ordinal + @file + grep + trace ledger
```

## The Loop

1. Start from an existing requirement.
2. Add `@reqtrace` handles near implementation or test evidence.
3. Grep the requirement handle after the implementation pass.
4. Validate each occurrence against the requirement.
5. Append each validated expanded trace to the requirement's trace ledger.

## Start Here

- [Concept](concept.md) explains why Reqtrace avoids graph servers and reverse indexes.
- [Syntax](syntax.md) defines the handle grammar.
- [Workflow](workflow.md) shows the two-stage pass.
- [Rules](rules.md) defines what must be true for a trace to count.
- [Edge Cases](edge-cases.md) covers renames, duplicate ordinals, file moves, and ledger drift.
- [Example Requirement](requirements.md) shows a complete trace ledger.
