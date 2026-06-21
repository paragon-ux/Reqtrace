---
name: reqtrace-audit
description: Audit, synchronize, and report Reqtrace ledger state using the repository CLI. Use after evidence changes, when CI reports trace drift, or when reviewing stale paths, legacy annotations, and coverage gaps.
---

# Reqtrace Audit

Delegate all scanning, ID generation, ledger comparison, and reporting to `scripts/reqtrace.py`; this skill must not duplicate that logic or decide semantic validity.

1. Run `python scripts/reqtrace.py check --strict` and `python scripts/reqtrace.py report`.
2. Report mechanical findings exactly: stale ledger, legacy form, malformed JSONL, multiple markers, ambiguous markers, collisions, or registry gaps.
3. Do not decide whether an annotation is valid evidence. Ask the human or point to the upstream artifact when that judgment is needed.
4. Only after explicit human or CI-triggered authorization, run `python scripts/reqtrace.py generate` followed by `python scripts/reqtrace.py render`, then repeat `check --strict`.
5. For stale paths, regenerate; for accidental markers, remove them from source before regeneration; for a different handle, surface the upstream decision rather than relabeling it.

Never hand-edit `docs/trace-ledger.jsonl` or a generated Markdown ledger block. Keep all output grep-native and local to the repository.
