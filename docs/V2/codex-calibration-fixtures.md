# Reqtrace v2.1 "Verified" — Calibration Fixtures

## Version

This release is **Reqtrace v2.1 "Verified"**.

V2 introduced the simplified grammar, CLI toolchain, and JSONL ledger. v2.1
adds:

- Bug fixes making the CLI reliable at its edge cases
- `doc_hierarchy` enforcement ensuring annotations are leaf-only
- Self-consistent annotation cleanup (scripts/reqtrace.py traces only its TRD leaf)
- Calibration fixtures proving every documented claim against a live project structure

The epithet "Verified" reflects the theme: Reqtrace now enforces its own
correctness rather than only recording evidence.

---

## Context

The existing `examples/refresh-token/` demonstrates a single-handle, two-role
happy path. The calibration fixtures extend this to cover every distinct
claim made in the README and reference docs: the full/partial/zero coverage
model, both strict levels, `scan --diff`, `doc_hierarchy` violation detection,
multi-handle evidence detection, and legacy-form migration.

These fixtures are **not part of the automated test suite**. They live in
`examples/calibration/` as self-contained mini-projects. A runner script
`examples/calibration/run.py` executes each scenario and asserts the expected
outcome, producing a human-readable report. Running it is optional but should
produce zero failures on a correctly installed v2.1.

---

## Directory layout to create

```
examples/calibration/
  run.py                         ← runner: executes all scenarios, reports pass/fail
  01-full-coverage/
    .reqtrace.json
    docs/handle-registry.jsonl
    src/widget.py
    tests/test_widget.py
  02-partial-impl-only/
    .reqtrace.json
    docs/handle-registry.jsonl
    src/widget.py
  03-strict-full-vs-ledger/
    .reqtrace.json
    docs/handle-registry.jsonl   ← handle registered as "unknown" type
    src/widget.py
  04-doc-hierarchy-violation/
    .reqtrace.json                ← doc_hierarchy set
    docs/handle-registry.jsonl
    src/widget.py                 ← annotated with BRD handle (off-leaf)
  05-multi-handle-evidence/
    .reqtrace.json
    docs/handle-registry.jsonl
    src/widget.py                 ← two consecutive annotations, different handles
  06-scan-diff/
    .reqtrace.json
    docs/handle-registry.jsonl
    docs/trace-ledger.jsonl       ← pre-seeded with one committed record
    src/widget.py                 ← contains the committed annotation + one new one
  07-legacy-migration/
    .reqtrace.json
    docs/handle-registry.jsonl
    src/widget.py                 ← V1 form: @reqtrace HANDLE/001/@file
```

---

## Per-scenario specification

### 01-full-coverage

**Claim:** A handle with implementation and verification evidence lands in the
`full` bucket and passes `check`.

`.reqtrace.json`:
```json
{
  "legacy_form": "reject",
  "strict_level": "ledger",
  "role_map": {
    "src/**": "implementation",
    "tests/**": "verification"
  }
}
```

`docs/handle-registry.jsonl`:
```
{"handle": "TRD-1", "type": "technical-requirement"}
```

`src/widget.py`:
```python
# @reqtrace TRD-1
def compute(): ...
```

`tests/test_widget.py`:
```python
# @reqtrace TRD-1
def test_compute(): ...
```

**Runner assertions:**
1. `generate` exits 0
2. `check --strict` exits 0
3. `report --format json` exits 0 and `full` array contains `TRD-1`

---

### 02-partial-impl-only

**Claim:** A handle with only implementation evidence lands in `partial`, not
`full`, and `check` still passes (ledger is fresh).

`.reqtrace.json`: same as 01.

`docs/handle-registry.jsonl`:
```
{"handle": "TRD-2", "type": "technical-requirement"}
```

`src/widget.py`:
```python
# @reqtrace TRD-2
def compute(): ...
```

**Runner assertions:**
1. `generate` exits 0
2. `check --strict` exits 0
3. `report --format json` exits 0, `partial` array contains `TRD-2`, `full` array is empty

---

### 03-strict-full-vs-ledger

**Claim:** `check --strict=ledger` passes when the ledger is fresh regardless
of registry completeness; `check --strict=full` fails when a handle has type
`unknown`.

`docs/handle-registry.jsonl`:
```
{"handle": "TRD-3", "type": "unknown"}
```

`src/widget.py`:
```python
# @reqtrace TRD-3
def compute(): ...
```

**Runner assertions:**
1. `generate` exits 0
2. `check --strict=ledger` exits 0
3. `check --strict=full` exits 1 and stderr contains `E_HANDLE_NOT_REGISTERED`

---

### 04-doc-hierarchy-violation

**Claim:** When `doc_hierarchy` is set, `check` fails with `E_OFFLEAF_HANDLE`
for an implementation-kind annotation whose handle prefix is not the leaf.

`.reqtrace.json` adds:
```json
{
  "doc_hierarchy": ["BRD", "ARD", "DRD", "TRD"],
  "role_map": {"src/**": "implementation"}
}
```

`docs/handle-registry.jsonl`:
```
{"handle": "BRD-1", "type": "business-requirement"}
```

`src/widget.py`:
```python
# @reqtrace BRD-1
def compute(): ...
```

**Runner assertions:**
1. `generate` exits 0
2. `check` exits 1 and stderr contains `E_OFFLEAF_HANDLE`
3. stderr contains `expected leaf: TRD`

---

### 05-multi-handle-evidence

**Claim:** When `doc_hierarchy` is set, `check` fails with
`E_MULTI_HANDLE_EVIDENCE` when two consecutive implementation annotations
name different handles.

`.reqtrace.json` adds `doc_hierarchy` as above.

`docs/handle-registry.jsonl`:
```
{"handle": "TRD-4", "type": "technical-requirement"}
{"handle": "TRD-5", "type": "technical-requirement"}
```

`src/widget.py`:
```python
# @reqtrace TRD-4
# @reqtrace TRD-5
def compute(): ...
```

**Runner assertions:**
1. `generate` exits 0
2. `check` exits 1 and stderr contains `E_MULTI_HANDLE_EVIDENCE`

---

### 06-scan-diff

**Claim:** `scan --diff` shows only annotations absent from the committed
ledger — not annotations already in it.

`docs/trace-ledger.jsonl` (pre-seeded, one committed record):
```json
{"handle": "TRD-6", "id": "abcd", "path": "src/widget.py", "line": 1, "kind": "implementation"}
```

`src/widget.py`:
```python
# @reqtrace TRD-6   ← already in ledger (line 1)
def existing(): ...

# @reqtrace TRD-7   ← new annotation, not in ledger
def new_feature(): ...
```

`docs/handle-registry.jsonl`:
```
{"handle": "TRD-6", "type": "technical-requirement"}
{"handle": "TRD-7", "type": "technical-requirement"}
```

**Runner assertions:**
1. `scan --diff --format json` exits 0
2. Output JSON contains exactly one entry with `handle: TRD-7`
3. Output JSON does not contain `TRD-6`

---

### 07-legacy-migration

**Claim:** `migrate` rewrites V1 annotations to V2 form; the resulting file
passes `check --strict`.

`.reqtrace.json`:
```json
{
  "legacy_form": "warn",
  "strict_level": "ledger",
  "role_map": {"src/**": "implementation"}
}
```

`docs/handle-registry.jsonl`:
```
{"handle": "AUTH-SESSION-ROTATION", "type": "requirement"}
```

`src/widget.py` (initial content, V1 form):
```python
# @reqtrace AUTH-SESSION-ROTATION/001/@file
def rotate(): ...
```

**Runner assertions:**
1. `migrate` exits 0
2. `src/widget.py` after migration contains `@reqtrace AUTH-SESSION-ROTATION` without `/001/@file`
3. `check --strict` exits 0

---

## Runner script specification (`examples/calibration/run.py`)

The runner is a standalone Python 3 script with no dependencies beyond the
standard library. It must not import `reqtrace` directly — it invokes
`python scripts/reqtrace.py <command>` as a subprocess so each scenario runs
against the real installed CLI in an isolated temporary working directory.

### Structure

```python
#!/usr/bin/env python3
"""
Reqtrace v2.1 calibration runner.

Usage:
    python examples/calibration/run.py

Runs every calibration scenario and reports PASS/FAIL. Exit code is the
number of failures (0 = all pass).
"""
```

### Per-scenario execution pattern

For each scenario:

1. Copy the scenario directory to a `tempfile.TemporaryDirectory`.
2. Call `python <repo_root>/scripts/reqtrace.py <command>` with
   `cwd=<temp_dir>`, `capture_output=True`, `text=True`.
3. Assert the expected exit code and any required stdout/stderr substrings.
4. On failure, print the scenario name, failed assertion, and captured output.
5. Always clean up the temp directory.

### Reporting

After all scenarios, print a summary:

```
Reqtrace v2.1 calibration
=========================
01-full-coverage          PASS
02-partial-impl-only      PASS
03-strict-full-vs-ledger  PASS
04-doc-hierarchy-violation PASS
05-multi-handle-evidence  PASS
06-scan-diff              PASS
07-legacy-migration       PASS

7 scenarios: 7 passed, 0 failed
```

Exit with the count of failures.

---

## Post-creation verification

After Codex creates all files, run:

```
python examples/calibration/run.py
```

All 7 scenarios must report PASS. If any fail, fix the fixture or the runner
assertion before declaring v2.1 complete — failures here indicate a gap
between the documented claim and the actual CLI behaviour.

---

## Summary

| File | Purpose |
|---|---|
| `examples/calibration/run.py` | Standalone runner; invoke manually to verify all claims |
| `examples/calibration/01-full-coverage/` | Proves full-bucket classification |
| `examples/calibration/02-partial-impl-only/` | Proves partial-bucket classification |
| `examples/calibration/03-strict-full-vs-ledger/` | Proves two strict levels behave differently |
| `examples/calibration/04-doc-hierarchy-violation/` | Proves E_OFFLEAF_HANDLE fires |
| `examples/calibration/05-multi-handle-evidence/` | Proves E_MULTI_HANDLE_EVIDENCE fires |
| `examples/calibration/06-scan-diff/` | Proves scan --diff filters committed annotations |
| `examples/calibration/07-legacy-migration/` | Proves migrate rewrites V1 form and check passes |
