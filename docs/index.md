# Reqtrace

Reqtrace records grep-able implementation evidence against an existing upstream handle. The upstream artifact can be a requirement, architecture decision, security control, compliance rule, policy, or test specification.

Reqtrace deliberately stays small:

```txt
handle + source marker + generated JSONL ledger + grep
```

## The Loop

1. Start from an existing registered handle.
2. Add one marker near implementation, verification, or documentation evidence.
3. Generate the canonical ledger.
4. Render its human-readable views.
5. Let `check --strict` enforce that the committed result remains synchronized.

Reqtrace does not define, rewrite, split, supersede, or interpret upstream handles.

## Start Here

- [Concept](concept.md) explains the grep-native boundary.
- [Syntax](syntax.md) defines the one supported annotation grammar.
- [Workflow](workflow.md) explains generation, rendering, and enforcement.
- [Rules](rules.md) lists the mechanical rules.
- [Edge Cases](edge-cases.md) covers stale ledgers, legacy annotations, and invalid markers.
- [Example Requirement](requirements.md) contains a generated ledger block.
