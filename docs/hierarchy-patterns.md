# Hierarchy Patterns

## Why Reqtrace Does Not Ship Presets

Reqtrace does not ship hierarchy presets in v2.1.5. Teams use document trees,
typed docs-as-code objects, artifact-coverage chains, tracker-native issue
hierarchies, and flat ADR logs. Reqtrace provides `handle`, `type`, `source`,
`parent`, `links`, `@reqtrace <handle>`, ledger records, and JSON reports; teams
and downstream tools apply those primitives to their own model. Doorstop owns
document trees; Sphinx-Needs/Open-Needs owns typed docs-as-code; OpenFastTrace
owns artifact coverage chains; Jira and Azure Boards own tracker hierarchies.
Reqtrace coexists with each by using its IDs as handles. See
[`adr/0001-v2.1.5-core-boundaries.md`](adr/0001-v2.1.5-core-boundaries.md) for
the v2.1.5 delegation rationale.

## Overview

The registry may carry two reserved relationship fields: `parent` for vertical
hierarchy and `links` for horizontal peer relationships. In v2.1.5 they may be
present in `docs/handle-registry.jsonl` and are preserved, but are not written by `register`;
`check` does not validate them. Users, agents, and downstream
tools may add them directly when they need graph traversal.

## How To Wire A Hierarchy

1. Register handles with `register <HANDLE> --type <TYPE>`.
2. Add `parent` and `links` in `docs/handle-registry.jsonl`, or use downstream tooling that writes registry records.
3. Run `check --strict` for normal evidence validation; v2.1.5 does not validate hierarchy semantics.

Future releases may add `register --parent` and `register --link`, but v2.1.5
does not implement either flag.

```jsonl
{"handle": "SRS-1", "type": "system-requirement"}
{"handle": "SDS-1", "type": "design-spec", "parent": "SRS-1"}
{"handle": "TC-1", "type": "test-case", "parent": "SDS-1"}
```

Reqtrace preserves these records; it does not decide whether their chain is
complete, valid, sufficient, or semantically correct.

## Vertical Hierarchy Patterns

These observed patterns are suggestions, not universal standards.

| Pattern | Layers (top -> bottom) | Suggested prefixes | Notes |
| --- | --- | --- | --- |
| Regulated / medical | System Req -> Software Req -> Design Spec -> Test Case | `SYS-N`, `SRS-N`, `SDS-N`, `TC-N` | Common in regulated and medical-device workflows. |
| Systems engineering | Feature -> Requirement -> Architecture -> Design -> Impl | `FEAT-N`, `REQ-N`, `ARCH-N`, `DSN-N`, `IMPL-N` | Matches an OpenFastTrace-style artifact chain. |
| Classic enterprise | Business Req -> Architecture Req -> Technical Req | `BRD-N`, `ARD-N`, `TRD-N` | Common in enterprise teams; sub-item IDs have no dominant standard. |
| Agile spec-first | Constitution -> Plan -> Spec | `CONST-N`, `PLAN-N`, `SPEC-N` | Matches GitHub Spec Kit and AI-native workflows. |
| ADR log | Flat; no parent | `ADR-NNN` | Peer decisions; use `links` for supersedes relationships. |

## Horizontal Peer Patterns

**Supersedes (ADR evolution):**

```jsonl
{"handle": "ADR-002", "type": "architecture-decision", "links": ["ADR-001"]}
```

**Cross-cutting concern (security requirement spanning features):**

```jsonl
{"handle": "SEC-1", "type": "security-requirement", "links": ["SRS-3", "SRS-7", "SRS-12"]}
```

**Same-level dependency (one TRD depends on another):**

```jsonl
{"handle": "TRD-4", "type": "technical-requirement", "parent": "ARD-2", "links": ["TRD-2"]}
```

## Agent Traversal

Agents can build the hierarchy graph by reading `docs/handle-registry.jsonl`
and following `parent` and `links`. The `register` output and report contracts
are documented in [`schema.md`](schema.md).
