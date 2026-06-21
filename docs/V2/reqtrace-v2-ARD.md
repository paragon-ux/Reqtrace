# Reqtrace v2 — Architecture Requirements Document (ARD)

**Document type:** Architecture Requirements Document
**Depends on:** BRD (goals), DRD (design decisions), TRD (literal specs)
**Scope:** Component model, data flow, non-functional requirements, phased rollout, and the architectural boundary around agent automation.

---

## 1. Architectural Constraints (Hard, Non-Negotiable)

- **ARD-1 — Grep-native is an architectural invariant, not a feature.** At every phase of the rollout (Section 9), the system must remain fully usable via plain `grep` with zero tooling installed. This is checked, not assumed: any new component (registry, ledger, CLI) must store data in a form `grep` can search directly (BRD-8, DRD-4) — this is why TRD §5/§6 specify JSON Lines rather than a single JSON/YAML document or a SQLite file.
- **ARD-2 — No infrastructure dependency, ever.** No server process, daemon, database, or hosted service may be introduced at any phase (BRD Section 6.2). The architecture is and remains: files in the repository, plus a stateless CLI that reads and writes those files.
- **ARD-3 — Determinism.** Given an unchanged codebase, `generate` must produce byte-identical output on every run (sorted records, TRD §5). This is an architectural requirement, not just a test case: it is what makes the ledger usable as a diffable, version-controlled artifact and what makes CI checks trustworthy (a flaky generator would make `check` unreliable).
- **ARD-4 — Idempotency of all write operations.** `generate`, `render`, and `migrate` must be safe to run repeatedly with no cumulative side effects beyond the current state of the source tree. No operation appends; every write operation fully recomputes its output from current source.
- **ARD-5 — Tool-augmented by choice, grep-native by design (DRD-4).** Nothing in the architecture may require the validator to be present for a trace to be *findable*. The validator's role is to make recording, enforcement, and reporting *automatic* — not to be a precondition for the convention's basic function.

## 2. Component Model

```
┌─────────────────────────┐
│   Source Tree            │   developer/agent writes
│   (.js, .py, etc.)        │   @reqtrace <HANDLE>  comments
└────────────┬─────────────┘
             │  read (grep-equivalent regex walk, TRD §3)
             ▼
┌─────────────────────────┐
│   Scanner                │   walks repo per excluded_dirs,
│   (reqtrace.py: scan)     │   applies TRACE_RE + LEGACY_TRACE_RE
└────────────┬─────────────┘
             │  (handle, path, line) triples
             ▼
┌─────────────────────────┐
│   ID Resolver             │   short_id(path, line) → hex id
│   (TRD §4)                 │   role_map(path) → kind
└────────────┬─────────────┘
             │  full ledger records
             ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│   Ledger Generator        │ ──▶ │  docs/trace-ledger.jsonl   │  canonical, machine-owned
│   (reqtrace.py: generate)  │      │  (ARD-1, ARD-3, ARD-4)      │
└────────────┬─────────────┘      └──────────────────────────┘
             │  reads ledger
             ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│   Renderer                 │ ──▶ │  docs/*.md ledger blocks    │  human-readable view
│   (reqtrace.py: render)     │      │  (DRD-11)                    │
└─────────────────────────┘      └──────────────────────────┘

┌──────────────────────────┐      ┌──────────────────────────┐
│  docs/handle-registry.jsonl │ ◀──▶ │  Coverage Reporter          │  reqtrace.py: report
│  (human + auto-discovered)   │      │  registry × ledger → buckets │
└──────────────────────────┘      └──────────────────────────┘

┌─────────────────────────┐
│   CI Gate                  │   pre-commit + GitHub Actions
│   (reqtrace.py: check)      │   invoke Scanner + diff vs committed ledger
└─────────────────────────┘

┌─────────────────────────┐      ┌─────────────────────────┐
│  Annotation-placement skill │      │  Ledger-audit skill         │
│  (suggests, human-confirms)  │      │  (runs check/report,         │
│  — calls scanner only         │      │   never writes a verdict)    │
└─────────────────────────┘      └─────────────────────────┘
```

Every arrow in this diagram is a file read or a file write; there is no network edge anywhere in the system (ARD-2).

## 3. Data Flow (Sequence)

1. Developer or agent writes `@reqtrace <HANDLE>` in a source comment (no ledger interaction).
2. On commit (pre-commit hook) or push (CI), `check` invokes the Scanner, which re-derives the full set of `(handle, path, line, id, kind)` records from current source.
3. `check` diffs that in-memory result against the committed `docs/trace-ledger.jsonl`. Any difference — a new occurrence not yet generated, a removed occurrence still present in the ledger, a stale path — fails the gate (`E_STALE_LEDGER`).
4. The developer/agent runs `generate` (writes the ledger) and `render` (updates human-readable views) locally, commits the result, and `check` now passes.
5. Independently, `report` cross-references `docs/handle-registry.jsonl` against `docs/trace-ledger.jsonl` to bucket every registered handle into zero/partial/full coverage. This step has no write side effects and never blocks a merge by itself — it is informational unless paired with `check --strict`'s registry-membership check.

This sequence replaces v1's two-stage loop (implement → manual ledger pass) with implement → automated regenerate-and-verify, with the CI gate occupying the position v1 left unenforced (BRD-1, DRD-15).

## 4. Non-Functional / Quality Attribute Requirements

| ID | Attribute | Requirement |
|---|---|---|
| ARD-6 | Portability | Runs with Python 3 stdlib only, in air-gapped or legacy CI containers, with no install step (carries forward BRD-10, BRD-8). |
| ARD-7 | Auditability | Any trace can be verified by a human running plain `grep`, independent of trusting the tool's output (ARD-1). |
| ARD-8 | Determinism | Same source tree → same generated output, every time, on every machine (ARD-3). |
| ARD-9 | Idempotency | Repeated writes with no source change produce no diff (ARD-4). |
| ARD-10 | Backward compatibility | The v1 form remains parseable (not silently invisible) for the duration of the deprecation window defined by `.reqtrace.json`'s `legacy_form` (BRD OD-2, DRD-23). |
| ARD-11 | Performance | Linear-time single-pass scan over the repository; no quadratic behavior as handle count or file count grows (TRD §11). |
| ARD-12 | Fail-loud over fail-silent | Every ambiguous or unexpected state (multiple markers per line, hash collision, malformed ledger line) is a reported error, never a silently-ignored or silently-corrected case — this is the architectural antidote to v1's central failure mode (BRD-2). |

## 5. Extensibility Architecture

**ARD-13 — Handle types are data, not code.** Adding a new handle type (e.g., `compliance-rule`) requires only a new `type` value in a registry entry (TRD §6) — no change to `TRACE_RE`, the Scanner, the Ledger Generator, or the CI gate. This is the architectural expression of DRD-9: scope expansion is a registration-time decision, never a code change.

**ARD-14 — Role inference is configuration, not a hardcoded table.** `role_map` (TRD §2) is read from `.reqtrace.json` at runtime; the architecture must not hardcode `src/**` → `implementation` anywhere except as the *default value* of that configuration, so a repository with a non-standard layout can override it without modifying the tool's source.

## 6. Agent / Automation Architecture

**ARD-15 — The two skills (DRD-20) call existing CLI surface only; they do not duplicate scanning or generation logic.** The annotation-placement skill calls the Scanner (read-only) to understand existing context before suggesting a new annotation; it never writes to the ledger directly. The ledger-audit skill calls `check` and `report` (both read-only) and, only on explicit human/CI-triggered action, `generate`/`render`. Neither skill contains its own copy of `TRACE_RE`, `short_id()`, or the diff logic — all of that lives once, in `reqtrace.py`, and both skills shell out to it. This prevents the skills from drifting out of sync with the CLI's behavior, which would reintroduce exactly the kind of divergence that caused BRD-5 (docs vs. implementation disagreeing about the grammar).

**ARD-16 — Semantic validation has no component.** There is deliberately no box in the component model (Section 2) responsible for judging whether a trace is *correct* evidence — that judgment happens in PR review, outside this system's architecture entirely (DRD-13). Codex must not add one; a future request to "have the agent also confirm the trace is semantically valid" is an explicit non-goal and should be treated as a request to revisit BRD Section 6.2, not a gap to silently fill in.

## 7. Deployment / Environment Requirements

**ARD-17** The system must function identically in: a developer's local machine, a pre-commit hook execution context, a CI runner with no network access, and an air-gapped enterprise environment with no package registry access. Because the only runtime dependency is Python 3 stdlib (ARD-6), no environment-specific branching should exist in `reqtrace.py` beyond standard path-separator normalization (`path.as_posix()` for cross-OS-consistent ledger entries, per TRD §5).

**ARD-18 — Graceful degradation.** If `reqtrace.py` is entirely unavailable in an environment (not installed, stripped from a vendored copy, etc.), traces remain findable via the documented `grep` commands (`docs/syntax.md` "Search Levels" section, carried forward from v1's `concept.md`/`syntax.md`). The system must never reach a state where the validator is the *only* way to find a trace — only the only way to *generate, verify, or report on* one.

## 8. Migration Architecture

**ARD-19** The migration (TRD §9) must never pass through a state where `grep -R "@reqtrace AUTH-SESSION-ROTATION"` returns nothing for the existing fixture — i.e., the rewrite of code comments and the regeneration of the ledger should be designed as a single atomic operation (`migrate` writes all changed source files and the new ledger/registry files in one pass, with `--dry-run` as the only way to preview without writing) rather than a multi-step manual process that could leave the repository in a partially migrated, partially grep-able state.

## 9. Phased Rollout Architecture

This is the architectural sequencing referenced by BRD Section 11, stated in terms of what must exist before the next phase can safely start.

| Phase | Deliverable | Preconditions | Architectural reason for this position |
|---|---|---|---|
| 0 | Unified grammar (TRD §3), `.reqtrace.json` | none | Everything downstream parses source text; the grammar must be correct and singular first (BRD-5). |
| 1 | Annotation simplification + `migrate` subcommand | Phase 0 | Removes the two-state annotation (BRD-2) before anything is built that would otherwise need to handle both states forever. |
| 2 | Ledger Generator + Handle Registry + JSONL schema | Phase 1 | The schema is designed backward from the coverage report's needs (DRD-10) even though the reporter ships in Phase 5 — this phase exists specifically to avoid building a ledger shape that later blocks reporting, as v1's free-form ledger did. |
| 3 | CI Gate (`check`, pre-commit hook, GitHub Actions workflow) | Phase 2 | Enforcing a gate against an unschematized, manually-appended ledger would enforce a fragile workflow and break CI on legitimate work (BRD-R2) — the gate must point at something deterministic and generated first. |
| 4 | Agent skills (annotation-placement, ledger-audit) | Phase 3 | Automating against a convention that isn't yet enforced would encode v1's fragilities into the automation itself (BRD-R1) — the CI gate must already be the safety net before agents are automating the workflow on top of it. |
| 5 | Coverage Reporter (`report`) | Phase 2 (schema) functionally complete; Phase 3 recommended for the report to be acted on with teeth | The reporter is the system's "killer feature" but is only meaningful once the ledger it reads is enforced (Phase 3) and trustworthy — shipping it earlier would produce a coverage number nobody can rely on. |

Phases 4 and 5 may proceed in parallel once Phase 3 is complete; both depend on Phase 3 but not on each other.

## 10. Architectural Risk Register

| ID | Risk | Architectural mitigation |
|---|---|---|
| ARD-R1 | A future contributor adds a second ledger format (e.g., a SQLite cache for performance) "for speed," reintroducing an infrastructure dependency. | ARD-2 is stated as a hard constraint with no exception clause; any such proposal is out of architecture by definition, not a performance trade-off to weigh case by case. |
| ARD-R2 | The registry (Phase 2) goes unmaintained, making `report` and `check --strict` unreliable. | `--register-unknown` (TRD §6) keeps the system functional in non-strict mode without full manual registration; strict mode is opt-in per repository, not forced globally. |
| ARD-R3 | Two skills (Phase 4) drift in behavior from the CLI they wrap, reintroducing a docs-vs-implementation divergence like BRD-5. | ARD-15 — skills contain no duplicated parsing/generation logic; they shell out to the single CLI implementation. |
