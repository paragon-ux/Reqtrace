# Reqtrace v2 — Business Requirements Document (BRD)

**Document type:** Business Requirements Document
**Subject system:** Reqtrace v2, successor to `paragon-ux/Reqtrace`
**Audience:** Codex (implementing agent), engineering stakeholders
**Companion documents:** DRD (design), TRD (technical), ARD (architecture)
**Source basis:** Independent feature-by-feature diagnosis of Reqtrace v1, cross-checked against the actual v1 source: `README.md`, `AGENTS.md`, `scripts/validate_reqtrace.py`, `docs/{index,concept,syntax,workflow,rules,edge-cases,requirements}.md`, and the `examples/refresh-token` fixture.

---

## 1. Purpose

This document defines why Reqtrace v2 should exist, what business problem it solves, what must survive unchanged from v1, and what "done" looks like. The DRD, TRD, and ARD that follow all trace back to a goal or constraint defined here. Codex should treat this document as the source of intent — the TRD tells Codex *what to build*, this document tells Codex *why*, which matters whenever a technical decision is ambiguous.

## 2. Background: What Reqtrace v1 Is

Reqtrace is a grep-native convention for tracing implementation evidence back to an existing requirement. It does not generate, own, or interpret requirements — it starts after a requirement handle already exists (from a spec, ticket, PRD, or doc) and adds exactly one structural marker:

```
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

placed in a code comment near the evidence, expanded by a two-stage loop (implement, then a manual "ledger pass") into a resolved line in `docs/requirements.md`:

```
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

v1 ships as a demo: one example requirement (`AUTH-SESSION-ROTATION`), one optional validator script, and a 16-line `AGENTS.md`. It has no CI, no schema, and one requirement type.

## 3. Problem Statement

An independent diagnosis evaluated every v1 feature on necessity, friction, and value-vs-steps. The findings, cross-checked against the source, identify a single root cause with four visible symptoms.

**Root cause (BRD-1):** v1 declares the ledger pass "mandatory" (README.md, AGENTS.md) while the only tool that could enforce it is documented as "optional" (`## Optional Validation`, README.md), is not wired into CI, and checks against a ledger that has no schema. A convention that requires a manual step but supplies no automated verification of that step is enforced entirely by discipline — which is the exact failure mode a convention is supposed to remove.

**Symptom 1 — silent failure via `@file` (BRD-2):** The annotation exists in an unresolved state (`@file` literal) until a human runs the ledger pass. If that pass is skipped, forgotten, or done carelessly, the codebase contains annotations that look complete but are not, with no automated signal that anything is wrong. Inspection of `validate_reqtrace.py` confirms the placeholder carries no information the tool needs: `scan_code_traces()` derives the resolved path from `Path.relative_to(root)` at scan time and never reads the literal string `@file` for data — it is used only as a regex anchor confirming the marker is "complete," then discarded. The tool already knows the path without the placeholder; the placeholder adds a failure mode for a value it never collects.

**Symptom 2 — manual ordinal collisions (BRD-3):** The ordinal (`[0-9]{3}` in code, `001`, `002`, ...) requires a developer to know what ordinals already exist before assigning a new one, with no protection against two developers picking the same number on parallel branches. `edge-cases.md` documents this exact failure mode as expected and resolvable only by manual renumbering during review.

**Symptom 3 — unschematized ledger (BRD-4):** `docs/requirements.md` mixes human-authored requirement prose with manually appended bullet lines in one free-form file. `validate_reqtrace.py`'s `LEDGER_RE` parses it with a single regex against a markdown bullet convention that is not declared or versioned anywhere; there is no machine-checkable schema. This blocks every form of automated reporting, including the coverage report that would make the convention valuable at scale.

**Symptom 4 — undocumented grammar divergence (BRD-5):** `docs/syntax.md` documents the requirement-handle grammar as `[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*` (alphanumeric segments), but the shipped `validate_reqtrace.py` implements `[A-Z]+(?:-[A-Z]+)*` (letters only, no digits permitted in any segment). This means handle styles the diagnosis explicitly recommends supporting for scope expansion — `ADR-0012`, `SEC-CONTROL-7` — would be silently rejected by the real tool today, despite being valid per its own documentation.

**Symptom 5 — artificial scope restriction (BRD-6):** The annotation, grammar, and validator logic are scope-agnostic — they would work identically for an ADR, a security control, or a test spec. Only the name ("Reqtrace"), the documentation, and the file naming (`requirements.md`) restrict the convention to requirement handles. This is a naming and packaging constraint, not a design constraint, and it costs adopters who need to trace non-requirement artifacts (security controls, compliance rules, ADRs) the choice of either misusing the convention or not adopting it for that purpose.

## 4. Business Goals

| ID | Goal | Resolves |
|---|---|---|
| BRD-G1 | Eliminate the two-state (unresolved/resolved) annotation so a trace cannot exist in a silently broken intermediate state. | BRD-2 |
| BRD-G2 | Eliminate manual developer coordination as a precondition for adding a trace (no more pre-assigned ordinals). | BRD-3 |
| BRD-G3 | Give the ledger a versioned, machine-parseable schema without introducing a server, database, or non-stdlib dependency. | BRD-4 |
| BRD-G4 | Make "mandatory" mean something: an automated gate (pre-commit and CI) that fails a change with unresolved or out-of-sync traces. | BRD-1 |
| BRD-G5 | Resolve the documented-vs-implemented grammar divergence with one grammar, defined once, used by both docs and code. | BRD-5 |
| BRD-G6 | Allow any named upstream handle (requirement, ADR, security control, compliance rule, test spec) without changing the annotation syntax. | BRD-6 |
| BRD-G7 | Deliver a coverage report ("N of M handles have zero/partial/full implementation evidence") as the feature that makes the rest of the system worth adopting. | — (net-new value) |
| BRD-G8 | Sequence delivery so automation (CI, agent skills) is built on top of the simplified, schema'd convention — never ahead of it. | BRD-1 |

## 5. What Must Be Preserved (Non-Negotiable)

The diagnosis identified two v1 decisions as unambiguously strong. v2 must not regress either:

- **BRD-7 — The `@reqtrace` marker itself.** A single reserved token placed in a code comment, traveling with the code through merges and renames, readable without tooling. The marker survives into v2 unchanged in spirit (only the payload after it simplifies — see DRD).
- **BRD-8 — Grep-native as a hard constraint.** Every trace must remain findable with plain `grep`, with zero tooling installed, in any environment including air-gapped and legacy codebases. This is the project's competitive differentiator against heavyweight tools (Jama, Polarion, DOORS) and database-backed alternatives. Automation may be added *on top of* this constraint; nothing in v2 may make grep insufficient on its own.
- **BRD-9 — "Reqtrace is not a requirements process."** It must continue to refuse to create, rename, split, supersede, or interpret the upstream artifact it traces. This boundary is what keeps the tool mechanical and small; v2 generalizes *what kind* of upstream artifact it can reference (BRD-G6) without weakening this boundary.
- **BRD-10 — Zero runtime dependencies.** The validator must remain plain Python 3 standard library, runnable with no install step, consistent with v1's "dependency-free" design.

## 6. Scope

### 6.1 In scope for v2
- Annotation simplification (remove `@file`, remove manual ordinal) — BRD-G1, BRD-G2
- Unified, corrected handle grammar — BRD-G5
- Structured, auto-generated ledger with a defined schema — BRD-G3
- Promoted validator: pre-commit hook + CI workflow templates — BRD-G4
- Handle-scope generalization (registry of typed handles, not requirement-only) — BRD-G6
- Coverage reporting — BRD-G7
- Migration path for the existing `examples/refresh-token` fixture and `docs/requirements.md` ledger
- Updated `AGENTS.md` covering annotation, validator interpretation, and stale-trace audit scenarios
- Two narrowly scoped agent skills (annotation placement, ledger audit) — see DRD/ARD

### 6.2 Out of scope for v2
- Any server, daemon, database, or hosted service of any kind (excluded permanently, not deferred — see BRD-8)
- Semantic validation of whether a trace is *actually* correct evidence for a requirement (remains a human/reviewer judgment — automating this is explicitly rejected, see DRD)
- A rename of the project (see Open Decision OD-1 below — deferred, not rejected)
- Cross-repository or cross-project trace aggregation
- IDE plugins or editor integrations (CLI and CI only for v2)

## 7. Stakeholders & Users

| Stakeholder | Interest |
|---|---|
| Solo developer / small team | Low-friction annotation, no coordination overhead, works without installing anything |
| Team with parallel branches | No ordinal collisions, ledger stays correct without manual merge resolution |
| PR reviewer | A CI check that actually blocks merges with unresolved or stale traces, replacing manual ledger review |
| AI coding agents (Codex, Claude Code, etc.) | Unambiguous grammar, explicit guidance for all three workflow scenarios, no implicit judgment calls left undocumented |
| Security / compliance teams | Ability to trace controls and compliance rules using the same convention, without inventing a parallel system |
| Engineering leadership | A coverage report answering "what requirements have zero implementation evidence," usable as a real project-management signal |

## 8. Success Metrics

- **BRD-M1:** Zero manual edits to the canonical ledger file in normal operation — every entry is generator-written.
- **BRD-M2:** 100% of merged commits pass `reqtrace check --strict` in CI; the check is a required status, not advisory.
- **BRD-M3:** Regenerating the ledger from an unchanged codebase produces byte-identical output (idempotency — needed so CI doesn't show false diffs).
- **BRD-M4:** A handle defined in the registry with zero `@reqtrace` occurrences is detectable by `reqtrace report` without any custom scripting.
- **BRD-M5:** The existing `AUTH-SESSION-ROTATION` example migrates to v2 form with no loss of trace history and a passing `reqtrace check`.
- **BRD-M6:** A new handle type (e.g., `ADR-0012`) can be registered and traced with zero changes to the annotation grammar or validator code — only a registry entry.

## 9. Assumptions & Constraints

- The implementing environment has Python 3 available; no package manager step is assumed or required.
- Existing v1-annotated code (the `examples/refresh-token` fixture) is the only known production-shaped data and must remain the reference migration case.
- The project may run in CI environments without network access; nothing in v2 may require an external call.
- AI coding agents are a primary user, not an edge case — ambiguity in any spec here is a defect, not a detail to leave to interpretation.

## 10. Risks

| ID | Risk | Mitigation |
|---|---|---|
| BRD-R1 | Shipping agent skill automation before the annotation is simplified and the ledger is schema'd encodes v1's fragilities into automated workflows that are then hard to unwind. | Hard sequencing constraint — see Section 11 and ARD Phased Rollout. Skill automation is the second-to-last phase, not an early one. |
| BRD-R2 | CI enforcement shipped before the simplification work breaks CI on legitimate work (enforcing a fragile workflow is worse than no enforcement). | CI enforcement phase is explicitly ordered after grammar/annotation/ledger work, not before it. |
| BRD-R3 | Migration of the existing demo ledger loses or silently drops a trace. | `reqtrace migrate` (TRD) must be additive-with-warnings, never silently destructive — any legacy ledger entry it cannot map to a found code annotation is reported, not dropped. |
| BRD-R4 | A future-proofed handle registry is built but never adopted, leaving coverage reporting unusable. | Registry entries can be auto-discovered (`--register-unknown`) so the system is useful before full manual registration; strict mode is opt-in. |

## 11. Phased Delivery (Business View)

This is the business-level ordering; the ARD defines the corresponding architecture phases and the TRD defines the literal deliverables per phase.

1. Simplify the annotation (remove `@file`, remove manual ordinal) — unblocks everything downstream.
2. Auto-generate the ledger from annotations — removes the manual append step entirely.
3. CI and pre-commit enforcement — makes "mandatory" actually mean something.
4. Agent skill automation — split into annotation-placement and ledger-audit, only after 1–3 are stable.
5. Coverage reporting — the schema work to support this is done as part of step 2 (the report's needs constrain the ledger schema backward), but the reporter itself ships last because it depends on a populated, enforced ledger to be meaningful.

## 12. Open Decisions Requiring Sign-Off

**OD-1 — Project naming.** The diagnosis notes that since the annotation, grammar, and validator no longer constrain handles to "requirements," the name "Reqtrace" is narrower than the product. Options: (a) keep the name, broaden scope purely via the handle registry's `type` field — lowest churn; (b) rename to reflect general evidence-tracing scope. **Default if no decision is made: option (a).** Codex should not block implementation on this decision; all TRD/ARD specs are name-agnostic (the marker token, file names, and CLI tool name are defined independently of the project's display name).

**OD-2 — Legacy annotation deprecation window.** How long should `reqtrace check` accept the v1 form (`HANDLE/ORD/@file`) before rejecting it outright (`--reject-legacy`)? Recommendation: default to `warn` until an explicit project-level config flag flips it to `reject` (see TRD `.reqtrace.json`), rather than picking a hardcoded date.
