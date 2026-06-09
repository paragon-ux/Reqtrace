# Reqtrace

Reqtrace is a minimal convention for tracing implementation evidence back to an existing requirement.

It starts after a requirement handle already exists. The requirement source remains upstream: a spec, ticket, PRD, issue, SDD artifact, or documentation page. Reqtrace only adds grep-able implementation trace handles and a resolved trace ledger.

Reqtrace is deliberately small:

```txt
requirement handle + implementation ordinal + @file + grep + trace ledger
```

## The Loop

1. Start from an existing requirement handle.
2. Add `@reqtrace` handles near implementation or test evidence.
3. Grep the requirement handle after the implementation pass.
4. Validate each occurrence against the existing requirement.
5. Append each validated expanded trace to the requirement's trace ledger.

Reqtrace does not define, rewrite, split, supersede, or interpret requirements.

## Start Here

- [Concept](concept.md) explains why Reqtrace avoids graph servers and reverse indexes.
- [Syntax](syntax.md) defines the handle grammar.
- [Workflow](workflow.md) shows the implementation pass and mandatory ledger pass.
- [Rules](rules.md) defines the mechanical rules for trace handles and ledgers.
- [Edge Cases](edge-cases.md) shows incorrect and correct trace patterns.
- [Example Requirement](requirements.md) shows a complete trace ledger.
