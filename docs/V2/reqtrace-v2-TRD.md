# Reqtrace v2 — Technical Requirements Document (TRD)

**Document type:** Technical Requirements Document
**Depends on:** BRD (goals), DRD (design decisions)
**Audience:** Codex — this document is the literal build spec. Where this document gives a regex, schema, or file path, that is the implementation, not an example.

---

## 1. Target Repository Layout

```
README.md                          # updated: new syntax, new workflow, drop "Optional Validation"
AGENTS.md                          # rewritten per TRD §8
mkdocs.yml                         # unchanged structurally
.reqtrace.json                     # NEW — project config, see TRD §2
.pre-commit-hooks.yaml             # NEW
.github/workflows/reqtrace.yml     # NEW
docs/
  index.md                         # updated: drop ordinal/@file references
  concept.md                       # updated
  syntax.md                        # updated: single grammar source, see TRD §3
  workflow.md                      # updated: two-stage loop per DRD-14
  rules.md                         # updated
  edge-cases.md                    # updated: ordinal-collision cases removed, new cases added
  requirements.md                  # MIGRATED: human prose + generated ledger block, see TRD §5
  handle-registry.jsonl            # NEW, see TRD §6
  trace-ledger.jsonl               # NEW — canonical machine ledger, see TRD §5
examples/refresh-token/
  src/{validation.js,rotation.js,revocation.js}   # MIGRATED annotations
  tests/rotation.test.js                          # MIGRATED annotation
scripts/
  reqtrace.py                      # RENAMED from validate_reqtrace.py, restructured as a CLI, see TRD §7
  migrate_reqtrace.py              # NEW, or a `reqtrace migrate` subcommand — see TRD §9 (subcommand preferred)
```

Codex should implement `migrate` as a subcommand of `reqtrace.py` rather than a separate script, to avoid a second tool with its own dependency/path-resolution logic.

## 2. Project Configuration File — `.reqtrace.json`

Stdlib `json`, no new dependency. All keys optional; defaults shown.

```json
{
  "marker": "@reqtrace",
  "id_length": 4,
  "legacy_form": "warn",
  "excluded_dirs": [".git", "node_modules", "dist", "build", "coverage", ".venv", "site"],
  "ledger_path": "docs/trace-ledger.jsonl",
  "registry_path": "docs/handle-registry.jsonl",
  "role_map": {
    "src/**": "implementation",
    "lib/**": "implementation",
    "app/**": "implementation",
    "tests/**": "verification",
    "spec/**": "verification",
    "docs/**": "documentation",
    "migrations/**": "migration",
    "infra/**": "operational",
    "deploy/**": "operational"
  }
}
```

- `legacy_form`: `"warn"` (default) or `"reject"`. Controls whether `check` treats a v1-form annotation as a deprecation warning or a hard failure. Implements BRD OD-2 / DRD-23.
- `excluded_dirs`: identical default set to v1's `EXCLUDED_DIRS`, with `"site"` already included (v1 already excludes it — mkdocs build output).
- `role_map`: glob pattern → role string, used for the `kind` field in ledger records (TRD §5). Order matters; first match wins. User-overridable so non-default repo layouts aren't hardcoded against, per DRD's path-based role inference principle.

If `.reqtrace.json` is absent, the tool runs with the defaults above — it must never require the config file to exist (zero-config must work for the existing demo repo as-is).

## 3. Annotation Grammar

**v2 grammar (the only grammar; documented and implemented identically):**

```
@reqtrace <HANDLE>
```

```regex
HANDLE := [A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*
TRACE_RE := r"@reqtrace\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\b"
```

This corrects the v1 doc/code divergence (BRD-5): segments now permit digits, so `ADR-0012`, `SEC-CONTROL-7`, `TRD-12` all match. There is no ordinal group and no `@file` group — `TRACE_RE` has exactly one capture group.

**Enforcement of one marker per line (DRD-7):** when scanning a line, use `re.findall` (not `finditer`-and-accept-all) to detect whether more than one match exists on a single line; if so, this is a parse error (`E_MULTIPLE_MARKERS_ON_LINE`, see TRD §10), not two traces.

**Legacy grammar (for migration and deprecation detection only — matches what `validate_reqtrace.py` actually implements today, not what `docs/syntax.md` claims):**

```regex
LEGACY_TRACE_RE := r"@reqtrace\s+([A-Z]+(?:-[A-Z]+)*)/([0-9]{3})/@file\b"
```

`check` must run both `TRACE_RE` and `LEGACY_TRACE_RE` against every scanned line. A `LEGACY_TRACE_RE` match with no corresponding `TRACE_RE` match on that line is reported per `legacy_form` config (warn/reject). A line should never match both patterns simultaneously by construction; if it does, treat it as `E_AMBIGUOUS_MARKER`.

## 4. Occurrence Identity (Replacing the Manual Ordinal)

No developer-facing ordinal is assigned. At scan time, for each `(handle, path, line)` triple found:

```python
import hashlib

def short_id(path: str, line: int, length: int = 4) -> str:
    digest = hashlib.sha256(f"{path}:{line}".encode("utf-8")).hexdigest()
    return digest[:length]
```

- Default `length` is 4 (from `.reqtrace.json`, `id_length`), matching the diagnosis's example (`AUTH-SESSION-ROTATION/a3f2/...`).
- **Collision handling:** because the id is derived from `(path, line)`, and one marker per line is enforced (TRD §3), a true collision within one handle requires two *different* `(path, line)` pairs hashing to the same truncated digest — astronomically unlikely at 4 hex chars for realistic repo sizes, but must still be handled, not assumed away. On detected collision within a handle's occurrence set, `generate` must automatically retry with `length=6`, then `length=8`, before failing with `E_ID_COLLISION` (this should never be reached in practice; it exists so a collision is a loud, recoverable error rather than silent data loss).
- The id is **not** a stable cross-time identifier and is not advertised as one — DRD-6 explicitly notes it only needs to disambiguate the current snapshot, not survive history. It is recomputed fresh on every `generate` run from current `(path, line)`.

## 5. Ledger Format — `docs/trace-ledger.jsonl`

**Format:** newline-delimited JSON (JSON Lines). One trace occurrence per line. Chosen over a single JSON/YAML document specifically because it stays grep-native (`grep '"handle": "AUTH-SESSION-ROTATION"' docs/trace-ledger.jsonl` works with zero tooling) while being trivially parseable with stdlib `json` per line — no PyYAML dependency (BRD-10).

**Schema (one JSON object per line):**

```json
{"handle": "AUTH-SESSION-ROTATION", "id": "a3f2", "path": "examples/refresh-token/src/validation.js", "line": 42, "kind": "implementation"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `handle` | string | yes | Matches `HANDLE` grammar (TRD §3) |
| `id` | string | yes | Hex string from `short_id()`, TRD §4 |
| `path` | string | yes | Repo-relative, POSIX separators always (even on Windows) |
| `line` | int | yes | 1-indexed |
| `kind` | string | yes | Derived from `role_map` (TRD §2); `"unknown"` if no pattern matches |

**File-level rule:** this file is entirely generator-owned. It must carry a non-JSON comment-style warning as its conceptual contract (enforced by tooling, not by file syntax, since JSONL has no comment syntax) — Codex should add a `docs/trace-ledger.README.md` (or a header note in `AGENTS.md`) stating: *"docs/trace-ledger.jsonl is generated by `reqtrace generate`. Do not hand-edit; changes will be overwritten."*

**Sort order:** lines sorted by `(handle, path, line)` ascending on every write, so regeneration with no code changes produces a byte-identical file (BRD-M3, idempotency).

### 5.1 Human-Readable Rendering — `docs/requirements.md` and similar

Per DRD-11, human-authored handle definitions and machine-generated ledger entries coexist in the same file but are structurally separated by markers:

```markdown
# AUTH-SESSION-ROTATION

A successful refresh-token exchange must rotate the refresh token and prevent reuse of the old token.

This requirement is the source of truth for the demo. The entries below are validated implementation traces, not requirement definitions.

## Trace Ledger

<!-- reqtrace:ledger:start handle=AUTH-SESSION-ROTATION -->
- AUTH-SESSION-ROTATION/a3f2/examples/refresh-token/src/validation.js:42
- AUTH-SESSION-ROTATION/7c19/examples/refresh-token/src/rotation.js:18
- AUTH-SESSION-ROTATION/0e44/examples/refresh-token/src/revocation.js:9
- AUTH-SESSION-ROTATION/b201/examples/refresh-token/tests/rotation.test.js:31
<!-- reqtrace:ledger:end -->
```

`reqtrace render` (TRD §7) rewrites only the content strictly between the `<!-- reqtrace:ledger:start ... -->` / `<!-- reqtrace:ledger:end -->` markers for the matching `handle=`, leaving everything else in the file untouched. This is how the existing `docs/requirements.md` prose ("A successful refresh-token exchange must...") survives migration unchanged while its ledger section becomes generated.

## 6. Handle Registry — `docs/handle-registry.jsonl`

Same JSONL rationale as the ledger (grep-native, stdlib-parseable).

```json
{"handle": "AUTH-SESSION-ROTATION", "type": "requirement", "source": "docs/requirements.md"}
{"handle": "ADR-0012", "type": "adr", "source": "docs/adr/0012-token-rotation.md"}
{"handle": "SEC-CONTROL-7", "type": "security-control", "source": "docs/security/controls.md"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `handle` | string | yes | |
| `type` | string | yes | Free-form but conventionally one of: `requirement`, `adr`, `security-control`, `compliance-rule`, `test-spec`, `policy`, `unknown` |
| `source` | string | no | Repo-relative path or URL to the upstream artifact; informational only, never resolved by the tool |

- `reqtrace generate --register-unknown` auto-appends an entry with `type: "unknown"` for any handle found in code but absent from the registry, so the system is useful before full manual registration (BRD-R4).
- `reqtrace check --strict` fails if any code handle has no registry entry at all (including `"unknown"` — strict mode requires explicit registration, `--register-unknown` is the on-ramp, not a permanent substitute).

## 7. CLI Specification — `scripts/reqtrace.py`

Single entry point, subcommand-based, stdlib `argparse` only.

```
python scripts/reqtrace.py scan
python scripts/reqtrace.py generate
python scripts/reqtrace.py render
python scripts/reqtrace.py check [--strict]
python scripts/reqtrace.py report [--format text|json]
python scripts/reqtrace.py migrate [--dry-run]
```

| Subcommand | Behavior | Exit codes |
|---|---|---|
| `scan` | Read-only. Walks the repo per `excluded_dirs`, applies `TRACE_RE` and `LEGACY_TRACE_RE`, prints grouped occurrences. Equivalent to v1's default `print_grouped_traces()` output, extended with `(path, line, id, kind)`. | 0 always (informational) |
| `generate` | Re-scans the codebase, recomputes `(id, kind)` for every occurrence, writes `docs/trace-ledger.jsonl` (sorted, TRD §5). Also auto-appends `"unknown"` registry entries if `--register-unknown` is passed. Idempotent. | 0 on success, 2 on I/O error |
| `render` | Rewrites all `reqtrace:ledger:start/end` blocks found in any `*.md` file under `docs/` from the current `docs/trace-ledger.jsonl`. Does not touch content outside those markers. | 0 on success, 2 on I/O error |
| `check` | Read-only CI gate. Runs the same scan as `generate` in memory, diffs the result against the committed `docs/trace-ledger.jsonl`. Reports legacy-form annotations per `legacy_form` config. With `--strict`, additionally fails on any handle not present in the registry. | 0 = clean; 1 = drift or strict violations found; 2 = usage/I-O error |
| `report` | Reads the registry and the ledger; for every registered handle, computes occurrence count; prints zero/partial/full coverage buckets. `--format json` emits machine-readable output. | 0 always (informational; never blocks CI on its own — pair with `check --strict` for blocking behavior) |
| `migrate` | One-time tool: finds all `LEGACY_TRACE_RE` matches, rewrites each in place to `TRACE_RE` form (drops `/ORDINAL/@file`), then runs the equivalent of `generate`. Cross-references the pre-migration ledger and **warns** (never silently drops) on any legacy ledger entry with no matching post-migration code occurrence. `--dry-run` reports planned changes without writing. | 0 = migrated cleanly; 1 = migrated with warnings requiring human review; 2 = usage/I-O error |

`check`'s drift/diff logic is the direct successor of v1's bidirectional set comparison (`missing_from_ledger` / `missing_from_code` in `validate_reqtrace.py`'s `main()`), generalized from string-set comparison to structured-record comparison.

## 8. Target `AGENTS.md` (literal content to write)

```markdown
# Agent Guidance

Reqtrace is intentionally small. Keep it grep-native.

## Scenario 1: Annotating New Code
- Do not invent new canonical handles in code.
- Use existing handles from `docs/handle-registry.jsonl` or task context.
- Use `@reqtrace <HANDLE>` near implementation or test evidence. One marker per line.
- Do not add ordinals, `@file`, claims, parent fields, wiki links, JSON refs, or custom hook names.
- If no registry entry exists for the handle, ask before annotating; do not silently register it.

## Scenario 2: Running and Interpreting the Validator
- After implementation, run `python scripts/reqtrace.py check`.
- If `check` reports drift, run `python scripts/reqtrace.py generate` and `render`, then re-run `check`.
- Never hand-edit `docs/trace-ledger.jsonl` or the generated block inside any `docs/*.md` file.
- A non-zero exit from `check --strict` blocks the change; do not bypass it.

## Scenario 3: Handling Stale or Invalid Traces
- Run `python scripts/reqtrace.py report` to see zero/partial coverage handles.
- For a stale path (file moved or renamed), re-run `generate` and `render`; do not manually patch the ledger.
- For an invalid or accidental trace, remove the `@reqtrace` comment from source, then re-run `generate`.
- Do not silently rewrite a handle to a different one; surface the question to a human or the upstream requirement source.

## Boundary
- Reqtrace does not create, rename, or interpret handles.
- Reqtrace does not require a server, daemon, database, or graph resolver.
- Keep Reqtrace grep-native.
```

## 9. Migration Specification

Applies to the existing fixture: `examples/refresh-token/{src,tests}/*` and `docs/requirements.md`.

1. For each file under `examples/refresh-token/`, replace every `LEGACY_TRACE_RE` match with `@reqtrace <HANDLE>` (drop `/<ORDINAL>/@file`). Example: `// @reqtrace AUTH-SESSION-ROTATION/001/@file` → `// @reqtrace AUTH-SESSION-ROTATION`.
2. Run `generate` against the migrated tree to produce `docs/trace-ledger.jsonl`.
3. Diff the four resulting records against the four legacy ledger lines currently in `docs/requirements.md`. All four should map 1:1 by `(handle, path)` (line numbers may shift; that's expected and fine — `id` is recomputed, not preserved, per TRD §4).
4. Wrap the original requirement description in `docs/requirements.md` unchanged; replace its manual `## Trace Ledger` bullet list with the marker block from TRD §5.1; run `render` to populate it.
5. Create `docs/handle-registry.jsonl` with one entry: `{"handle": "AUTH-SESSION-ROTATION", "type": "requirement", "source": "docs/requirements.md"}`.
6. Run `check --strict`; it must exit 0 on the migrated tree before migration is considered complete.

## 10. Error Handling & Failure Modes

| Code | Condition | Behavior |
|---|---|---|
| `E_MULTIPLE_MARKERS_ON_LINE` | More than one `@reqtrace` match on a single source line | `check`/`generate` fail with file:line reference |
| `E_AMBIGUOUS_MARKER` | A line matches both `TRACE_RE` and `LEGACY_TRACE_RE` | `check`/`generate` fail with file:line reference |
| `E_LEGACY_FORM` | `LEGACY_TRACE_RE` match found | warn (default) or fail, per `legacy_form` config |
| `E_HANDLE_NOT_REGISTERED` | Handle found in code, absent from registry | fail only under `check --strict` |
| `E_STALE_LEDGER` | Ledger on disk differs from a fresh in-memory scan | `check` fails (this is v1's core drift check, generalized) |
| `E_ID_COLLISION` | Two distinct `(path, line)` pairs produce the same id after escalation to 8 hex chars | `generate` fails loudly — should not occur in practice (TRD §4) |
| `E_LEDGER_PARSE` | A line in `trace-ledger.jsonl` is not valid JSON or missing a required field | `check`/`report` fail, naming the offending line number |

`check` (without `--strict`) exits 1 on `E_STALE_LEDGER`, `E_MULTIPLE_MARKERS_ON_LINE`, `E_AMBIGUOUS_MARKER`, `E_LEDGER_PARSE`, and `E_LEGACY_FORM` (if `legacy_form=reject`). `--strict` additionally includes `E_HANDLE_NOT_REGISTERED`.

## 11. Performance & Dependency Constraints

- Python 3 standard library only: `re`, `hashlib`, `json`, `pathlib`, `argparse`, `sys`. No PyYAML, no third-party packages, consistent with BRD-10 and v1's existing dependency-free design.
- Single-pass directory walk per invocation (`Path.rglob`, matching v1's existing approach), excluding `excluded_dirs` early to avoid descending into large generated trees (`node_modules`, `dist`, `build`, `coverage`, `.venv`, `site`).
- All operations must be linear in repository size; no operation may require holding more than one file's contents in memory at a time during the scan phase.

## 12. Testing Requirements

- **Grammar tests:** confirm `TRACE_RE` matches `ADR-0012`, `SEC-CONTROL-7`, `TRD-12` (regression test for BRD-5) and that `LEGACY_TRACE_RE` still matches the exact form currently shipped in `examples/refresh-token`.
- **Golden fixture test:** migrate a copy of `examples/refresh-token` + `docs/requirements.md` end-to-end (TRD §9) and assert `check --strict` exits 0.
- **Idempotency test:** run `generate` twice with no source changes between runs; assert byte-identical `docs/trace-ledger.jsonl` (BRD-M3).
- **One-marker-per-line test:** a fixture line with two `@reqtrace` tokens must raise `E_MULTIPLE_MARKERS_ON_LINE`.
- **Collision-escalation test:** synthetic test that forces a 4-char collision (e.g., by monkeypatching `short_id`) and asserts escalation to 6 then 8 chars before `E_ID_COLLISION`.
- **Registry/coverage test:** a registry with one handle that has zero ledger occurrences must appear in `report`'s zero-coverage bucket; one with partial occurrences in the partial bucket.
- **Migration warning test:** a legacy ledger entry with no matching code occurrence must produce a warning from `migrate`, not a silent drop (BRD-R3).

## 13. Self-Hosting Requirement

Per the principle that this convention should prove itself on its own implementation: every requirement ID in this document set (`BRD-#`, `DRD-#`, `TRD-#`, `ARD-#`) is itself a valid v2 handle. Codex must register them in `docs/handle-registry.jsonl` (`type: "business-requirement"` / `"design-requirement"` / `"technical-requirement"` / `"architecture-requirement"`) and annotate the new code implementing each requirement with `@reqtrace <ID>` — e.g., the `short_id()` function (TRD §4) should carry `// @reqtrace TRD-4`. `reqtrace check --strict` run against this repository's own implementation is the acceptance test for the whole v2 build: if it doesn't pass against its own source, the build is not done.
