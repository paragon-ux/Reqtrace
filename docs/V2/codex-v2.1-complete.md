# Reqtrace v2.1 "Verified" — Complete Codex Prompt

Execute the following tasks in order. After each phase, run
`python -m pytest tests/test_reqtrace.py tests/test_edge_cases.py -v`
and stop if any test fails before proceeding.

---

## Task 1 — Bug fixes (`docs/V2/archive/codex-bugfix-report.md`)

Apply every fix in the archive report to `scripts/reqtrace.py` (and
`tests/test_reqtrace.py` where noted). Fix in severity order: CRITICAL,
HIGH, MEDIUM, LOW. All 30 tests in `tests/test_edge_cases.py` must pass
alongside the existing tests in `tests/test_reqtrace.py`.

---

## Task 2 — Annotation cleanup + `doc_hierarchy` feature (`docs/V2/codex-annotation-cleanup.md`)

Execute the three parts in their stated sequence:

1. **Part 1** — Add `doc_hierarchy` to `DEFAULT_CONFIG` and `load_config`,
   add `handle_prefix()`, add `E_OFFLEAF_HANDLE` and `E_MULTI_HANDLE_EVIDENCE`
   checks to `command_check`, and update `.reqtrace.json` with
   `"doc_hierarchy": ["BRD", "ARD", "DRD", "TRD"]`. Run tests.

2. **Part 2** — Apply the cleanup table to `scripts/reqtrace.py` and
   `tests/test_reqtrace.py`. Then run:
   ```
   python scripts/reqtrace.py generate
   python scripts/reqtrace.py check --strict
   ```
   Both must exit 0 with no `E_OFFLEAF_HANDLE` or `E_MULTI_HANDLE_EVIDENCE`
   errors.

3. **Part 3** — Add hierarchy-enforcement tests (to `tests/test_edge_cases.py`
   or a new `tests/test_hierarchy.py`). Run the full test suite.

---

## Task 3 — Registry source validation (`docs/V2/codex-registry-validation.md`)

### 3a — Implement the feature

Add `E_REGISTRY_SOURCE_MISSING` to `command_check` exactly as specified in
the document: inside the `strict_level == "full"` block, after the
`E_HANDLE_NOT_REGISTERED` loop.

Add tests covering:

- Registry entry with `source` pointing to an existing file →
  `check --strict=full` exits 0
- Registry entry with `source` pointing to a non-existent file →
  `check --strict=full` exits 1, `E_REGISTRY_SOURCE_MISSING` in stderr
- Registry entry with no `source` field →
  `check --strict=full` exits 0 (exempt)
- Multiple entries, only one with a missing source → only that handle reported

Run the full test suite.

### 3b — Repair `docs/handle-registry.jsonl`

Run `python scripts/reqtrace.py check --strict=full`. It will fire
`E_REGISTRY_SOURCE_MISSING` for 121 of the 123 registry entries because
their source paths do not exist on disk. Repair the registry as follows:

**34 V2M-\* entries** (`V2M-ARD-*`, `V2M-BRD-*`, `V2M-DRD-*`, `V2M-TRD-*`):
Remove these entries entirely from `docs/handle-registry.jsonl`. The V2M
annotation scheme is being retired (see Task 2), so these handles have no
source documents and no future role.

**87 canonical entries** (all `ARD-*`, `BRD-*`, `DRD-*`, `TRD-*` handles)
whose `source` field points to `docs/V2/reqtrace-v2-ARD.md`,
`docs/V2/reqtrace-v2-BRD.md`, `docs/V2/reqtrace-v2-DRD.md`, or
`docs/V2/reqtrace-v2-TRD.md`: those files were never committed to the repo.
The actual source for all canonical handles is the single reference document
`docs/reference.md`, which exists. Update every affected entry's `source`
field to `"docs/reference.md"`.

After both repairs, run:
```
python scripts/reqtrace.py check --strict=full
```
It must exit 0 with zero `E_REGISTRY_SOURCE_MISSING` errors.

---

## Task 4 — Calibration fixtures (`docs/V2/codex-calibration-fixtures.md`)

Create all 7 scenario directories under `examples/calibration/` and the
runner script `examples/calibration/run.py` exactly as specified.

Run:
```
python examples/calibration/run.py
```

All 7 scenarios must report PASS. If any scenario fails, fix the fixture or
runner assertion — do not modify `scripts/reqtrace.py` unless a genuine CLI
bug is found that is not already covered by the test suite.

---

## Final verification

```
python -m pytest tests/test_reqtrace.py tests/test_edge_cases.py -v
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict=full
python examples/calibration/run.py
```

All four commands must exit 0. This completes **Reqtrace v2.1 "Verified"**.
