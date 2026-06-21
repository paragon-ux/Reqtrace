# Reqtrace v2 — Design Requirements Document (DRD)

**Document type:** Design Requirements Document
**Depends on:** BRD (business rationale and goals)
**Feeds:** TRD (literal specs), ARD (component/data-flow architecture)

This document defines *what the convention looks like and why*, at the level a developer or agent experiences it — the annotation shape, the workflow, the ledger's conceptual model, and the agent guidance. It does not define exact regexes, file formats, or CLI flags; that is the TRD's job. Every DRD item maps to one or more BRD goals.

---

## 1. Design Principles (Carried Forward, Unchanged)

- **DRD-1 — One hook.** `@reqtrace` remains the only reserved marker. v1's prohibition on adding `@implements`, `@verifies`, or other hook names (`AGENTS.md`, `rules.md`) is retained without modification. Role (implementation vs. verification vs. documentation evidence) continues to be inferred from file path, not from a second hook name.
- **DRD-2 — Mechanical, not interpretive.** Reqtrace still does not create, rename, split, supersede, or interpret the upstream artifact a handle refers to (BRD-9). v2 generalizes the *type* of artifact a handle may belong to, not the tool's authority over it.
- **DRD-3 — The upstream source stays upstream.** A handle must already exist before it can be annotated — this rule, currently scoped to "requirements," generalizes unchanged to any handle type (BRD-G6).
- **DRD-4 — Grep is always sufficient on its own.** Per BRD-8, every design decision below must leave plain `grep` capable of finding every trace without the validator installed. Automation is additive, never a precondition for findability.

## 2. Annotation Design

**DRD-5 — Drop `@file`.** The annotation becomes:

```
@reqtrace <HANDLE>
```

Rationale: the file path is already known at the moment a developer (or agent) writes the comment — it is the file being edited. v1's own validator confirms `@file` is informationally inert: it resolves the path from `Path.relative_to(root)` during the scan, never from the literal token. Removing it removes the two-state annotation (unresolved-in-code / resolved-in-ledger) entirely — there is now only one state. There is no "ledger pass" step where a human types or pastes a path; the path is always read from where the marker physically sits.

**DRD-6 — Drop the manual ordinal.** v1's `[0-9]{3}` ordinal required a developer to know what numbers were already in use for a handle before picking a new one (BRD-3). v2 disambiguates multiple occurrences of the same handle by their natural, already-unique location: `(file path, line number)`. No developer-facing number is assigned at all — the tool derives a short display identifier from that location automatically (see TRD for the exact algorithm). This removes coordination overhead in parallel development entirely; two developers on two branches annotating the same handle in different files (or even the same file, different lines) cannot collide, because they are never asked to pick a number.

**DRD-7 — One marker per line.** To keep location-based disambiguation unambiguous, a single comment line may contain at most one `@reqtrace` marker. (v1 already follows this pattern in practice; v2 makes it an explicit, validator-enforced rule rather than an implicit convention.)

## 3. Handle Grammar Design

**DRD-8 — One grammar, defined once.** v1 has two different grammars in production: the documented one (`docs/syntax.md`, alphanumeric segments) and the implemented one (`validate_reqtrace.py`, letters-only segments). v2 defines the grammar exactly once, in the TRD, and both the validator and any documentation reference that single definition rather than restating it. The corrected grammar must permit digits within a segment (`ADR-0012`, `SEC-CONTROL-7`, `TRD-12`) — letters-only was never a deliberate design choice, it was an unreviewed implementation gap (BRD-5).

## 4. Handle Scope Design

**DRD-9 — Generalize handles via a registry, not via syntax changes.** The annotation syntax already works identically for any named handle; nothing about `@reqtrace AUTH-SESSION-ROTATION` versus `@reqtrace ADR-0012` requires different parsing. What v1 lacks is a place to declare *what a handle is* (a requirement, an ADR, a security control, a test spec) and *where it's defined upstream*. v2 introduces a handle registry — a flat, human- or auto-maintained list of `{handle, type, source}` triples — as the only new concept needed to unlock multi-type tracing (see TRD for format). This is a documentation/registration concern, not a grammar concern, matching the diagnosis's finding that "the restriction is naming and documentation, not design."

**DRD-10 — Coverage reporting needs the registry, not the other way around.** The registry exists specifically so coverage reporting can answer "which known handles have zero implementation evidence" — a question that requires a canonical list independent of what currently appears in code. Designing the registry only after wanting a coverage report would get the dependency order backward; the registry is therefore introduced at the same phase as ledger auto-generation, even though the reporter itself ships later (see ARD Phased Rollout).

## 5. Ledger Design

**DRD-11 — Separate human-authored definition from machine-generated evidence.** In v1, `docs/requirements.md` mixes a human-written requirement description ("A successful refresh-token exchange must rotate...") with manually appended ledger bullets in the same free-form file — two different kinds of content with two different authors (human vs. ledger-pass) and two different update cadences, indistinguishable by format. v2 keeps requirement/handle definitions human-authored in their existing documentation location, but the trace evidence for that handle becomes a clearly delimited, machine-generated block within (or alongside) that same file — never hand-edited, always produced by the tool, and trivially regenerable without touching the human-authored prose around it.

**DRD-12 — The ledger is generated, not appended to.** v1's "ledger pass" (grep, read, assess, manually append) is replaced by a single command that scans the codebase and (re)writes the ledger deterministically. There is no longer a manual transcription step where a human or agent copies a path by hand — eliminating exactly the step where v1's silent failures originated.

**DRD-13 — Validation judgment moves to code review, not a pre-append gate.** v1 conflated two distinct activities under "ledger pass": *recording* a trace (mechanical) and *validating* that the trace is semantically correct evidence (judgment). v2 keeps recording fully mechanical and automated, and relocates the judgment call — "is this actually valid evidence for the requirement?" — to normal PR review, where a human is already reading the diff. The tool's job is to guarantee every annotation in the codebase is *recorded*; it explicitly does not, and should not, judge whether the trace is *correct*. Automating that judgment is out of scope by design (BRD Section 6.2), not an oversight.

## 6. Workflow Design

**DRD-14 — Two-stage loop, reworked.** The two stages survive, redefined:
1. **Annotate** — unchanged in spirit: write `@reqtrace <HANDLE>` near evidence while implementing. No ledger interaction at this stage at all.
2. **Generate** — run the validator's generate command. It scans the codebase and writes the ledger. This is the entire "ledger pass" — no reading, no manual transcription, no judgment exercised by the tool.

**DRD-15 — Enforcement closes the loop the workflow alone cannot.** A two-stage loop with no enforcement boundary between the stages is what made v1's "mandatory" claim toothless (BRD-1). v2's workflow is not considered complete on its own — it is paired with a CI/pre-commit gate (TRD, ARD) that mechanically verifies stage 2 actually ran and is in sync with stage 1's output before a change can merge. The workflow design and the enforcement design are two parts of one requirement; neither alone satisfies BRD-G4.

## 7. Validator Role Design

**DRD-16 — From optional demo script to mandatory infrastructure.** v1's validator is read-only, advisory, and explicitly labeled optional (README.md `## Optional Validation`). v2 promotes it to the system's central enforcement mechanism: it must be wired into pre-commit and CI by default (not as an opt-in template a team has to remember to add), and its responsibilities expand from "diff code traces against the ledger" to also include: generating the ledger (not just checking it), detecting stale paths, detecting handles not present in the registry (strict mode), and producing the coverage report. No part of the workflow should depend on a human remembering to run something the tool could run automatically.

**DRD-17 — Rename the tool to match its role.** `validate_reqtrace.py` reads as a demo/check-only script. Renaming it (TRD specifies `scripts/reqtrace.py`, structured as a small multi-command CLI) signals that it is now the primary way the convention is operated, not a secondary verification step bolted on afterward.

## 8. Agent Guidance Design (AGENTS.md v2)

**DRD-18 — Cover all three scenarios an agent will actually face.** v1's `AGENTS.md` covers annotation well but says nothing about interpreting validator output or handling a stale/invalid trace found during an audit — gaps that let an agent comply with the letter of "append validated expanded traces" while violating its intent (e.g., appending an unresolved `@file` placeholder, which the old wording technically permits). v2's `AGENTS.md` must have one named section per scenario:
- **Annotating new code** — when and how to place `@reqtrace <HANDLE>`, and the explicit instruction not to invent a handle that isn't in the registry or task context.
- **Running and interpreting the validator** — what `check` failing means, what command fixes it, and an explicit instruction never to hand-edit the generated ledger block.
- **Auditing stale or invalid traces** — what to do when `report` surfaces a stale path or a trace with no matching registry handle, and the explicit instruction to surface ambiguous cases to a human rather than silently resolving them.

**DRD-19 — Preserve every existing prohibition.** All of v1's specific prohibitions (no claims, no parent fields, no wiki links, no JSON refs, no custom hook names) carry forward unchanged — each one exists to prevent a capable agent from "improving" the convention in a way that breaks grep-native compatibility, and removing `@file`/ordinals does not change that risk.

## 9. Skill Automation Design

**DRD-20 — Two skills, not one, with a hard boundary between them.** Per BRD Section 6.2, semantic validation is never automated. The roadmap skill is therefore split into two narrowly scoped skills rather than one broad one:
- **Annotation-placement skill** — suggests an `@reqtrace <HANDLE>` annotation when an agent has just implemented behavior matching a known handle's context, and places it only on human confirmation. This is the high-value, low-risk half: it addresses what humans are actually bad at (remembering to annotate everything relevant), not what they're good at (judging validity).
- **Ledger-audit skill** — runs the validator, reports unresolved annotations, stale paths, and handles missing from the registry, and regenerates the ledger for confirmed-valid traces. It does not decide whether a trace is semantically correct; it only reports mechanical state.

**DRD-21 — Sequencing constraint carries into design.** Per BRD-R1, neither skill may ship before the annotation simplification (DRD-5, DRD-6) and ledger auto-generation (DRD-11/12) are in place — automating placement or audit against the old `@file`/ordinal scheme would encode v1's fragilities into an automated workflow that is then harder to change than the manual one it replaced.

## 10. Migration Design

**DRD-22 — Migration must be additive-with-warnings, not silently destructive (BRD-R3).** The existing `examples/refresh-token` fixture and its four ledger entries (`AUTH-SESSION-ROTATION/001`–`004`) are the only known real data and the reference case for migration correctness. The migration design must: rewrite each legacy code comment (`@reqtrace AUTH-SESSION-ROTATION/001/@file`) to its v2 form (`@reqtrace AUTH-SESSION-ROTATION`) in place; regenerate the ledger from the rewritten code; and explicitly warn — never silently drop — on any legacy ledger entry that has no corresponding code annotation found during the scan, since that mismatch could mean either a stale ledger entry (safe to drop) or evidence the scan missed (unsafe to drop) and a human should decide which.

**DRD-23 — Legacy form remains parseable for a transition window, never indefinitely.** `check` must be able to recognize the v1 form well enough to flag it as deprecated rather than treating it as a non-match (silently invisible) or a hard failure (breaks CI on day one of migration). This is configurable per BRD OD-2, defaulting to a warning rather than a hard rejection.

## 11. Naming Design Implication

**DRD-24** Per BRD OD-1, no component specified in this document or the TRD depends on the project's display name. The marker token (`@reqtrace`), the CLI tool name, and all file names are defined independently of branding, so a future rename (if pursued) is a documentation and identifier change only, not a redesign.
