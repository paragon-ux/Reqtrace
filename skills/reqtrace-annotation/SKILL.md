---
name: reqtrace-annotation
description: Suggest and place valid Reqtrace evidence annotations after implementing code or tests. Use when a change may satisfy a registered requirement, ADR, security control, policy, or test-spec handle and the user wants trace placement assistance.
---

# Reqtrace Annotation

Use the repository's CLI as the source of truth; do not copy its grammar or ledger logic into this skill.

1. Read `AGENTS.md` and the relevant upstream artifact or task context.
2. Run `python scripts/reqtrace.py scan` to inspect nearby existing evidence, then inspect `docs/handle-registry.jsonl` for the intended handle.
3. Suggest one `@reqtrace <HANDLE>` comment per relevant source or test evidence line. Do not add an ordinal, `@file`, role-specific hook, claim, parent field, wiki link, or JSON reference.
4. Explain why each suggested location is evidence, and ask for human confirmation before writing annotations.
5. After confirmation, add the comments and tell the caller to use the audit skill or run `generate`, `render`, and `check --strict`.

Never invent, rename, or silently register a handle. If the handle is missing, ambiguous, or not supplied by an upstream source, stop and surface that question.
