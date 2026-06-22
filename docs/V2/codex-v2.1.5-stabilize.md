# Reqtrace v2.1.5 "Stabilized" — Codex Prompt

**Purpose:** Minimal stabilization for unconditional agentic usage. Fix incomplete
JSON outputs, add the one missing command (`register`), add a machine-readable
schema contract. No new features beyond these. Do not expand scope.

After each task, run:
```bash
python -m pytest tests/ -v
python scripts/reqtrace.py check --strict
```
Stop if either fails before proceeding.

---

## Task 1 — Fix `scan --format json` (missing fields)

Currently `scan --format json` emits:
```json
{"handle": "AUTH-LOGIN", "path": "src/auth.py", "line": 42}
```

The ledger already stores `kind` and `id` for every occurrence. Surface them in
the scan JSON output so agents get a complete annotation object.

**Required output shape:**
```json
{"handle": "AUTH-LOGIN", "path": "src/auth.py", "line": 42, "kind": "implementation", "id": "a1b2"}
```

**Rules:**
- If the ledger exists and contains a matching record for this path+line+handle,
  populate `kind` and `id` from the ledger record.
- If no ledger exists or no match is found, set `"kind": null, "id": null`.
- Default (non-JSON) scan output must remain unchanged.
- Field order must be: `handle`, `path`, `line`, `kind`, `id`.

**Tests:**
1. `scan --format json` on a repo with a fresh ledger → every record has `kind`
   and `id` matching the corresponding ledger entry.
2. `scan --format json` on a repo with no ledger → every record has
   `"kind": null, "id": null`.
3. Default `scan` (no `--format`) output is unchanged — no new fields in text output.

**Verification:**
```bash
python scripts/reqtrace.py generate
python scripts/reqtrace.py scan --format json | python -c "
import sys, json
records = json.load(sys.stdin)
assert all('kind' in r and 'id' in r for r in records), 'missing fields'
print('OK:', len(records), 'records, all have kind and id')
"
```

---

## Task 2 — Fix `report --format json` (add envelope)

Currently `report --format json` emits:
```json
{"zero": [...], "partial": [...], "full": [...]}
```

Agents cannot verify the schema version or extract a summary without traversing
all entries. Add a stable envelope.

**Required output shape:**
```json
{
  "schemaVersion": "2.1",
  "handles": {
    "zero": [...],
    "partial": [...],
    "full": [...]
  },
  "summary": {
    "total": 88,
    "full": 1,
    "partial": 10,
    "zero": 77
  }
}
```

**Rules:**
- `schemaVersion` is the string `"2.1"` (fixed for this release).
- `summary` counts are derived from the `handles` lists — not separately computed.
- `summary.total` = `full + partial + zero`.
- Existing per-handle object shape within `handles.full`, `handles.partial`,
  `handles.zero` is **unchanged**.
- `report --format github` output is **unchanged**.
- `report` (default text output) is **unchanged**.

**Tests:**
1. `report --format json` → top-level keys are `schemaVersion`, `handles`, `summary`.
2. `summary.total` equals `len(handles.full) + len(handles.partial) + len(handles.zero)`.
3. `summary.full` equals `len(handles.full)`.
4. `handles.full[0]` has the same fields as before (no regression).
5. `report --format github` output unchanged.

**Verification:**
```bash
python scripts/reqtrace.py report --format json | python -c "
import sys, json
d = json.load(sys.stdin)
assert d['schemaVersion'] == '2.1'
assert 'summary' in d
assert 'handles' in d
s = d['summary']
h = d['handles']
assert s['total'] == s['full'] + s['partial'] + s['zero']
assert s['full'] == len(h['full'])
print('OK: schemaVersion=2.1 total=%d full=%d partial=%d zero=%d' % (s['total'],s['full'],s['partial'],s['zero']))
"
```

---

## Task 3 — Fix `check --strict` output (machine-readable status line)

Currently `check --strict` exits 0 with no stdout/stderr on success. Agents
cannot distinguish "passed silently" from "produced no output due to error."

**Required behavior:**

On success, print one line to stdout:
```
REQTRACE OK registered=12 full=1 partial=10 zero=77
```

On failure, the existing error lines remain. Append one summary line to stderr:
```
REQTRACE FAIL checks=3
fix: python scripts/reqtrace.py generate && python scripts/reqtrace.py check --strict
```
Where `checks` is the count of distinct error codes emitted.

**Rules:**
- Exit codes are unchanged (0 = pass, 1 = fail).
- `--format json` flag: if provided, emit a JSON object to stdout instead of
  the text line. On success:
  ```json
  {"status": "ok", "registered": 12, "full": 1, "partial": 10, "zero": 77}
  ```
  On failure:
  ```json
  {"status": "fail", "errors": ["E_STALE_LEDGER", "E_HANDLE_NOT_REGISTERED"]}
  ```
- Do not change any existing error message text or error codes.
- The fix hint line is always the same string regardless of which checks failed.

**Tests:**
1. `check --strict` on a passing repo → stdout contains `REQTRACE OK`, exit 0.
2. `check --strict` on a failing repo → stderr contains `REQTRACE FAIL`, exit 1.
3. `check --strict --format json` on a passing repo → stdout is valid JSON with
   `{"status": "ok", ...}`, exit 0.
4. `check --strict --format json` on a failing repo → stdout is valid JSON with
   `{"status": "fail", "errors": [...]}`, exit 1.
5. `REQTRACE OK` counts match what `report --format json` summary reports.

**Verification:**
```bash
python scripts/reqtrace.py check --strict | grep "^REQTRACE OK"
python scripts/reqtrace.py check --strict --format json | python -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok'
print('OK: check --format json works, status=ok')
"
```

---

## Task 4 — Add `register` command

Add a `register` subcommand that appends a validated entry to
`docs/handle-registry.jsonl` and prints a paste-ready marker.

**Interface:**
```bash
python scripts/reqtrace.py register <HANDLE> [--type TYPE] [--source PATH]
```

`<HANDLE>` is a positional argument.

**Behavior:**
- Load config to resolve registry path.
- Create the registry file if it does not exist.
- If `<HANDLE>` already exists in the registry, exit 1 with:
  ```
  E_DUPLICATE_HANDLE: AUTH-LOGIN is already registered
  ```
- Validate `<HANDLE>` is non-empty and matches `[A-Za-z0-9_-]+` (same constraint
  as the scanner — reject handles with spaces or special characters).
- If `--source` is provided, validate the path exists relative to project root.
  If missing, exit 1 with:
  ```
  E_REGISTRY_SOURCE_MISSING: docs/missing.md not found
  ```
- Append the new record to the registry JSONL. Written fields: `handle`
  (required), `type` (if provided), `source` (if provided). Omit keys
  entirely when not provided — do not write `null` values.
- Print to stdout:
  ```
  REQTRACE REGISTERED AUTH-LOGIN
  marker:   @reqtrace AUTH-LOGIN
  registry: docs/handle-registry.jsonl
  ```
- Exit 0.

**Rules:**
- Do not sort the registry on append — append only.
- Do not read file contents to determine anything — registry lookup only.
- Do not require `--type` (optional, for forward compatibility with `--strict=full`).

**Tests:**
1. Register a new handle with no flags → exits 0, entry in registry, output
   contains `REQTRACE REGISTERED` and `marker:   @reqtrace <HANDLE>`.
2. Register same handle twice → exits 1, `E_DUPLICATE_HANDLE` in stderr.
3. Register with `--type requirement` → entry includes `"type": "requirement"`.
4. Register with `--source docs/reference.md` (exists) → exits 0, source in entry.
5. Register with `--source docs/nonexistent.md` → exits 1, `E_REGISTRY_SOURCE_MISSING`.
6. Register without `--type` → `"type"` key absent from written JSONL (not `null`).
7. Handle with space → exits 1 with validation error.
8. After registering, `check --strict` still passes (new untraced handle is not
   an error under `--strict=ledger`).

**Verification:**
```bash
python scripts/reqtrace.py register TEST-REG-001 --type test-handle
python scripts/reqtrace.py check --strict | grep "^REQTRACE OK"
# Clean up:
python -c "
import json, pathlib
p = pathlib.Path('docs/handle-registry.jsonl')
lines = [l for l in p.read_text().splitlines() if json.loads(l)['handle'] != 'TEST-REG-001']
p.write_text('\n'.join(lines) + '\n')
print('cleaned up TEST-REG-001')
"
python scripts/reqtrace.py check --strict | grep "^REQTRACE OK"
```

---

## Task 5 — Add `docs/schema.md` (stable JSON contracts)

Create `docs/schema.md` documenting the four stable JSON shapes. This is the
single reference an agent or downstream tool reads to consume Reqtrace output
without experimenting.

**Content requirements:**

### Section 1: Overview
One paragraph: Reqtrace exposes four stable JSON contracts. All are produced
by the CLI with `--format json`. Field names and types will not change within
a schemaVersion.

### Section 2: Annotation (`scan --format json`)
Document the per-occurrence object:

| Field | Type | Description |
|---|---|---|
| `handle` | string | Upstream handle identifier |
| `path` | string | Repo-relative file path |
| `line` | integer | 1-based line number |
| `kind` | string\|null | Role: `implementation`, `verification`, `documentation`, `migration`, `operational`. `null` if no ledger exists. |
| `id` | string\|null | 4-char occurrence ID from ledger. `null` if no ledger exists. |

### Section 3: Ledger record (`docs/trace-ledger.jsonl`)
Document the per-occurrence ledger line:

| Field | Type | Description |
|---|---|---|
| `handle` | string | Upstream handle identifier |
| `id` | string | 4-char occurrence ID (stable per handle+path+line) |
| `path` | string | Repo-relative file path |
| `line` | integer | 1-based line number |
| `kind` | string | Role |

### Section 4: Coverage report (`report --format json`)
Document the envelope and per-handle object.

Envelope:
| Field | Type | Description |
|---|---|---|
| `schemaVersion` | string | `"2.1"` |
| `handles` | object | Keys: `full`, `partial`, `zero`. Each is an array of handle objects. |
| `summary` | object | Keys: `total`, `full`, `partial`, `zero` (integer counts). |

Per-handle object:
| Field | Type | Description |
|---|---|---|
| `handle` | string | Upstream handle identifier |
| `type` | string | From registry |
| `source` | string\|null | From registry |
| `occurrences` | integer | Total annotation sites |
| `kinds` | array | Unique role strings observed |
| `kind_counts` | object | Count per role string |
| `implementation` | boolean | Has at least one implementation occurrence |
| `verification` | boolean | Has at least one verification occurrence |
| `documentation` | boolean | Has at least one documentation occurrence |
| `status` | string | `"full"`, `"partial"`, `"zero"` |

### Section 5: Registry record (`docs/handle-registry.jsonl`)
Document the per-handle registry line:

| Field | Type | Description |
|---|---|---|
| `handle` | string | Unique upstream handle identifier |
| `type` | string\|absent | Handle type (e.g., `requirement`, `security-control`) |
| `source` | string\|absent | Repo-relative path to source document |
| `parent` | string\|absent | Reserved relationship field. Handle of the immediate parent in a vertical hierarchy, when supplied manually or by downstream tooling. Preserved by Reqtrace tools when present, but not validated by `check` in v2.1.5. |
| `links` | array\|absent | Reserved relationship field. Handles of peer records this handle relates to horizontally, when supplied manually or by downstream tooling. Preserved by Reqtrace tools when present, but not validated by `check` in v2.1.5. |

Notes:
- Fields are absent, not `null`, when not provided.
- In v2.1.5, `register` writes `handle`, plus `type` and `source` when provided.
- `register` does not write `parent` or `links` in v2.1.5.
- `parent` and `links` are reserved relationship fields. Reqtrace preserves them
  when present in `docs/handle-registry.jsonl`, but does not enforce or validate
  their semantics in `check --strict`.
- Tools, agents, or users MAY add `parent` and `links` directly to registry
  records today. Reqtrace must not strip or reject them.
- Do not write `null` for reserved fields. Omit the field if not applicable.
- Future releases may add optional CLI support and validation for these fields
  once real-world usage shows which relationship semantics belong in core.

> **Reserved relationship fields:** `parent` and `links` are intentionally reserved
> but not enforced in v2.1.5. This lets downstream tools traverse hierarchy and peer
> relationships without forcing Reqtrace core to choose a hierarchy model prematurely.
> Reqtrace preserves these fields when present; it does not validate them, infer
> them, or require them.

### Section 6: Exit codes
| Exit code | Meaning |
|---|---|
| 0 | Command succeeded. `check` passes, `generate` wrote ledger, etc. |
| 1 | Command failed. `check` found violations; `register` found duplicate or missing source. |

### Update `mkdocs.yml`
Add `Schema: schema.md` to the nav list after Reference.

**Verification:**
```bash
test -f docs/schema.md && echo "schema.md exists"
grep "schema" mkdocs.yml
```

---

## Task 6 — Add `docs/hierarchy-patterns.md` (cross-linking reference)

Create `docs/hierarchy-patterns.md` documenting how teams apply `parent` and
`links` registry fields to common document hierarchy patterns. This is the
reference an agent or user reads to understand how Reqtrace supports hierarchical
traceability without imposing a fixed handle convention.

No CLI changes. No presets. No new code.

**Why no presets:** Evidence from real-world traceability tools and team practices
shows no dominant prefix convention. Regulated teams use SRS/SDS/VVP; systems
teams use feat/req/arch/dsn; agile teams use tracker-native IDs; AI-native teams
use folder-based feature IDs. Locking in preset handle names would feel wrong to
most teams. The `parent`/`links` fields are the primitive — this document shows
how to apply them.

**Content requirements:**

### Section 1: Why Reqtrace does not ship presets

One section (not buried — at the top) explaining the delegation decision:

- Reqtrace does not ship hierarchy presets in v2.1.5. Real teams use different
  hierarchy models: document trees, typed docs-as-code, artifact-coverage chains,
  tracker-native issue hierarchies, and flat ADR logs.
- Reqtrace provides primitives: `handle`, `type`, `source`, `parent`, `links`,
  `@reqtrace <handle>`, ledger records, and JSON report contracts. Teams and
  downstream tools apply those primitives to their own hierarchy pattern.
- If a full hierarchy manager is needed today, list the delegated tools:
  **Doorstop** (document-tree), **Sphinx-Needs / Open-Needs** (docs-as-code
  typed needs), **OpenFastTrace** (artifact-type coverage chains), **Jira /
  Azure Boards** (tracker-native hierarchy). Reqtrace coexists with any of these
  by using their IDs as handles.
- Forward reference: "For the rationale behind this and other v2.1.5 deferral
  decisions, see `docs/adr/0001-v2.1.5-core-boundaries.md`."

### Section 2: Overview
One paragraph: Reqtrace's registry can carry two reserved relationship fields:
`parent` for vertical hierarchy and `links` for horizontal peer relationships.
In v2.1.5, these fields may be present in `docs/handle-registry.jsonl` and are
preserved by Reqtrace tools, but they are not written by `register` and are not
validated by `check`. Users, agents, and downstream tools may add them directly
when they need hierarchy traversal.

### Section 3: How to wire a hierarchy

In v2.1.5, hierarchy wiring is explicit and file-native:

1. Register handles with `register <HANDLE> --type <TYPE>`.
2. Add `parent` and `links` by editing `docs/handle-registry.jsonl` directly,
   or by using downstream tooling that writes registry records.
3. Run `check --strict` to validate the normal Reqtrace evidence contract.
   `check` does not validate hierarchy semantics in this release.

Future releases may add `register --parent` and `register --link`, but
v2.1.5 does not implement those flags.

Example:
```jsonl
{"handle": "SRS-1", "type": "system-requirement"}
{"handle": "SDS-1", "type": "design-spec", "parent": "SRS-1"}
{"handle": "TC-1", "type": "test-case", "parent": "SDS-1"}
```

Reqtrace preserves these records as registry data. It does not yet decide
whether the chain is complete, valid, sufficient, or semantically correct.

### Section 4: Vertical hierarchy patterns

A table of five observed patterns with their layer names, suggested handle
prefixes, and parent chain. Drawn from real-world traceability tools and
team evidence. Do not claim these are universal standards.

| Pattern | Layers (top → bottom) | Suggested prefixes | Notes |
|---|---|---|---|
| Regulated / medical | System Req → Software Req → Design Spec → Test Case | `SYS-N`, `SRS-N`, `SDS-N`, `TC-N` | Common in regulated / medical-device-style workflows |
| Systems engineering | Feature → Requirement → Architecture → Design → Impl | `FEAT-N`, `REQ-N`, `ARCH-N`, `DSN-N`, `IMPL-N` | Matches OpenFastTrace artifact chain |
| Classic enterprise | Business Req → Architecture Req → Technical Req | `BRD-N`, `ARD-N`, `TRD-N` | Common in enterprise software teams; no dominant standard for sub-item IDs |
| Agile spec-first | Constitution → Plan → Spec | `CONST-N`, `PLAN-N`, `SPEC-N` | Matches GitHub Spec Kit / AI-native workflows |
| ADR log | *(flat — no parent)* | `ADR-NNN` | Peer decisions; use `links` for supersedes relationships |

### Section 5: Horizontal peer patterns

Describe the three most common peer-link uses with registry examples:

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

### Section 6: Agent traversal

Short paragraph: agents that consume the registry can build the full hierarchy
graph by reading `docs/handle-registry.jsonl` and following `parent` and `links`
pointers. The `register` command output and `report --format json` schema are
documented in `docs/schema.md`.

### Update `mkdocs.yml`
Add two entries to the nav list after Schema:
- `Hierarchy Patterns: hierarchy-patterns.md`
- `ADR: adr/0001-v2.1.5-core-boundaries.md`

### Update `README.md`
Add a short **"What Reqtrace delegates"** section after the existing CLI reference
or before "Contributing":

```md
## What Reqtrace delegates

Reqtrace v2.1.5 stabilizes the evidence convention. It does not replace every
surrounding workflow.

- **Search / command compression:** use `grep`, `rg`, or RTK.
- **Hierarchy presets:** use Doorstop, Sphinx-Needs/Open-Needs, OpenFastTrace,
  Jira, or Azure Boards. Reqtrace coexists with any of these — use their IDs as handles.
- **HTML dashboards:** generate from `report --format json`.
- **Blame / provenance:** join `scan --format json` and `trace-ledger.jsonl` in
  downstream tooling.
- **Graph visualization:** build from the registry and ledger JSONL files.

Reqtrace owns the portable evidence layer. See `docs/adr/0001-v2.1.5-core-boundaries.md`
for the full delegation rationale.
```

**Verification:**
```bash
test -f docs/hierarchy-patterns.md && echo "hierarchy-patterns.md exists"
grep "hierarchy-patterns" mkdocs.yml
grep "0001-v2.1.5" mkdocs.yml
grep "What Reqtrace delegates" README.md
grep "register does not write" docs/schema.md
grep "not written by" docs/hierarchy-patterns.md
grep "register --parent" docs/adr/0001-v2.1.5-core-boundaries.md
grep "register --link" docs/adr/0001-v2.1.5-core-boundaries.md
```

---

## Final verification

```bash
test -f docs/adr/0001-v2.1.5-core-boundaries.md
python -m pytest tests/ -v
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict | grep "^REQTRACE OK"
python scripts/reqtrace.py check --strict --format json | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'; print('check JSON OK')"
python scripts/reqtrace.py scan --format json | python -c "import sys,json; d=json.load(sys.stdin); assert all('kind' in r for r in d); print('scan JSON OK')"
python scripts/reqtrace.py report --format json | python -c "import sys,json; d=json.load(sys.stdin); assert d['schemaVersion']=='2.1'; print('report JSON OK')"
python examples/calibration/run.py
```

All commands must exit 0. This completes **Reqtrace v2.1.5 "Stabilized"**.
