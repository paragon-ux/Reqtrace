# Reqtrace V2 — Annotation Cleanup + Leaf-Enforcement Feature

## Context

`scripts/reqtrace.py` self-annotates with `@reqtrace` handles. The project
documents follow a top-down hierarchy:

    BRD (why) → ARD (system structure) → DRD (data / schema) → TRD (exact technical spec)

Each level is upstream of the next. Implementation code satisfies the **leaf**
— the most downstream document. Tracing code directly back to BRD/ARD/DRD is
wrong: those are already satisfied transitively when the TRD requirement is
met. Annotating at multiple levels adds maintenance burden with no information
gain.

A second error also present: consecutive `@reqtrace` blocks stack many handles
for a single function. Each evidence block (a consecutive annotation run above
one function or file section) must contain exactly **one** handle — the leaf.

A third error: handles with the prefix `V2M` (i.e. any handle whose first
segment before `-` is `V2M` — V2M-ARD-1, V2M-BRD-4, V2M-DRD-10, V2M-TRD-1,
etc.) are artefacts of a misguided versioning scheme. Documents should be
updated in-place or replaced with a new identity. All V2M-prefixed annotations
must be removed unconditionally from every file.

---

## Part 1 — New feature: `doc_hierarchy` enforcement in `check`

### 1.1 New config field

Add `doc_hierarchy` to `DEFAULT_CONFIG` and the config validator. Because
`CONFIG_FIELDS = frozenset(DEFAULT_CONFIG)`, adding the key to `DEFAULT_CONFIG`
automatically registers it — no separate edit to `CONFIG_FIELDS` needed. Only
the validator block (lines 156–183) requires a new stanza.

    DEFAULT_CONFIG: dict[str, Any] = {
        ...
        "doc_hierarchy": [],   # e.g. ["BRD", "ARD", "DRD", "TRD"]
    }

Accepted value: a list of strings. Each string is a document-type prefix
matching the leading segment of handle names before the first `-`. An empty
list disables enforcement. The validator must reject non-list values and
non-string elements.

### 1.2 Prefix extraction helper

    def handle_prefix(handle: str) -> str:
        """Return the document-type prefix, e.g. 'TRD' from 'TRD-7'."""
        return handle.split("-")[0]

Note: V2M handles produce prefix `V2M`, which does not appear in a
`doc_hierarchy` of `["BRD","ARD","DRD","TRD"]`. Part 1 enforcement will
therefore flag any surviving V2M annotation as `E_OFFLEAF_HANDLE`, providing
a safety net after the Part 2 cleanup.

### 1.3 Two new `check` errors

Both fire when `doc_hierarchy` is non-empty, regardless of the `--strict`
flag. Both count as failures (exit 1).

**`E_OFFLEAF_HANDLE`** — an `implementation`-kind record's handle prefix is
not `doc_hierarchy[-1]`.

    E_OFFLEAF_HANDLE {handle} at {path}:{line} (expected leaf: {leaf})

**`E_MULTI_HANDLE_EVIDENCE`** — more than one distinct handle annotates a
single contiguous evidence block in the same file (consecutive records where
no gap between line numbers exceeds 1).

    E_MULTI_HANDLE_EVIDENCE {path}:{first_line}-{last_line} has {n} handles: {handle_list}

### 1.4 Implementation location

Inside `command_check`, after the stale-ledger block (ends ~line 731), before
the strict-level block (starts ~line 733). Both checks operate on `generated`
(live scan records).

    if config["doc_hierarchy"]:
        leaf = config["doc_hierarchy"][-1]
        impl_records = [r for r in generated if r.kind == "implementation"]

        for record in impl_records:
            if handle_prefix(record.handle) != leaf:
                print(
                    f"E_OFFLEAF_HANDLE {record.handle} at {record.path}:{record.line} "
                    f"(expected leaf: {leaf})",
                    file=sys.stderr,
                )
                failures = True

        by_file: dict[str, list[LedgerRecord]] = defaultdict(list)
        for record in impl_records:
            by_file[record.path].append(record)
        for file_path, file_records in by_file.items():
            sorted_records = sorted(file_records, key=lambda r: r.line)
            blocks: list[list[LedgerRecord]] = []
            current: list[LedgerRecord] = [sorted_records[0]]
            for record in sorted_records[1:]:
                if record.line - current[-1].line <= 1:
                    current.append(record)
                else:
                    blocks.append(current)
                    current = [record]
            blocks.append(current)
            for block in blocks:
                handles_in_block = sorted({r.handle for r in block})
                if len(handles_in_block) > 1:
                    print(
                        f"E_MULTI_HANDLE_EVIDENCE {file_path}:{block[0].line}-{block[-1].line} "
                        f"has {len(handles_in_block)} handles: {', '.join(handles_in_block)}",
                        file=sys.stderr,
                    )
                    failures = True

### 1.5 Update `.reqtrace.json`

    {
      "doc_hierarchy": ["BRD", "ARD", "DRD", "TRD"]
    }

---

## Part 2 — Cleanup: re-annotate `scripts/reqtrace.py` and `tests/test_reqtrace.py`

**V2M-\* convention**: throughout this section, `V2M-*` means every handle
whose first segment is `V2M` — V2M-ARD-x, V2M-BRD-x, V2M-DRD-x, V2M-TRD-x,
etc. Delete all of them unconditionally wherever they appear.

### Rules

1. **One handle per evidence block.** Each function gets exactly one
   `@reqtrace` line.
2. **Leaf only.** The surviving handle must have prefix `TRD`. If no TRD
   handle is present in the block, keep the most downstream one
   (DRD > ARD > BRD).
3. **Delete all V2M-\* annotations unconditionally.**
4. **Do not change any function signatures or logic.**

### Cleanup table

Locate each block by its anchor function name (line numbers may have shifted
±5). The Handles column lists what is actually present in the current file.

| Block anchor | Handles present | Keep | Action |
|---|---|---|---|
| File top (module-level block, ~line 19) | BRD-7, BRD-8, BRD-9, BRD-10, BRD-G5, BRD-G8, BRD-R1, BRD-R2, DRD-1..DRD-4, DRD-8, DRD-24, ARD-1, ARD-2, ARD-R1, ARD-5, ARD-6, ARD-17, ARD-18, TRD-1, TRD-2, TRD-11, TRD-13, V2M-* | TRD-1 | delete all others |
| `load_config` | DRD-8, DRD-23, ARD-10, ARD-14, TRD-2, V2M-* | TRD-2 | delete all others |
| `starter_config` | V2M-* only (6 lines) | none | delete entire block |
| `find_project_root` | V2M-ARD-1 (1 line) | none | delete |
| `scan_repository` | BRD-2, BRD-3, BRD-5, BRD-G1, BRD-G2, DRD-5..DRD-8, DRD-14, DRD-22, ARD-7, ARD-11, ARD-12, TRD-3, V2M-* | TRD-3 | delete all others |
| `short_id` (covers `records_from_occurrences` too) | BRD-G2, BRD-M3, DRD-6, ARD-3, TRD-4, V2M-* | TRD-4 | delete all others |
| `write_ledger` | BRD-4, BRD-G3, BRD-M1, BRD-M3, DRD-11, DRD-12, ARD-3, ARD-4, ARD-8, ARD-9, TRD-5 | TRD-5 | delete all others |
| `ledger_record_from_json` | V2M-* only (2 lines) | none | delete entire block |
| `read_registry` | BRD-6, BRD-G6, BRD-G7, BRD-M4, BRD-M6, BRD-R4, DRD-9, DRD-10, ARD-13, ARD-R2, TRD-6 | TRD-6 | delete all others |
| `command_init` | V2M-* only (6 lines) | none | delete entire block |
| `command_scan` | BRD-8, DRD-4, DRD-16, DRD-20, ARD-7, ARD-15, TRD-7, V2M-* | TRD-7 | delete all others |
| `command_generate` | BRD-4, BRD-G3, BRD-M1, BRD-M3, DRD-12, DRD-13, DRD-16, ARD-3, ARD-4, TRD-7 | TRD-7 | delete all others |
| `command_render` | BRD-4, BRD-G3, DRD-11, DRD-12, ARD-4, TRD-5, TRD-7 | TRD-7 | delete all others |
| `command_check` | BRD-1, BRD-G4, BRD-M2, DRD-15, DRD-16, DRD-21, DRD-23, ARD-10, ARD-12, ARD-16, TRD-7, TRD-8, TRD-10, V2M-* | TRD-8 | delete all others |
| `command_report` | BRD-G7, BRD-M4, DRD-9, DRD-10, ARD-13, TRD-7, TRD-12, V2M-* | TRD-12 | delete all others |
| `command_migrate` | BRD-R3, BRD-M5, DRD-22, DRD-23, ARD-10, ARD-19, TRD-9, V2M-* | TRD-9 | delete all others |
| `build_parser` | BRD-1, BRD-G4, DRD-16..DRD-19, ARD-6, ARD-15, ARD-R3, TRD-7 | TRD-7 | delete all others |
| `main` | V2M-* only (2 lines) | none | delete entire block |
| `tests/test_reqtrace.py` — `test_default_legacy_form_is_reject` (~line 280) | V2M-* only (6 lines) | none | delete entire block |

### Notes on specific rows

**`starter_config` vs `find_project_root`**: these are two distinct blocks.
`starter_config` (~line 186) carries a 6-line all-V2M block. `find_project_root`
(~line 210) carries a single V2M-ARD-1 annotation. Both are delete-only; they
are listed as separate rows above.

**`short_id`**: the annotation block sits above `short_id` but covers the
`records_from_occurrences` function immediately below it. One block, two
functions. Keep TRD-4.

**`command_render`**: two TRD handles are present (TRD-5 and TRD-7). TRD-5
tracks the ledger-write operation; TRD-7 tracks the CLI commands. As a
`command_*` entrypoint, TRD-7 is the correct leaf. Keep TRD-7.

**`tests/test_reqtrace.py`**: the test file carries a V2M-* block above
`test_default_legacy_form_is_reject`. Because tests are `verification`-kind,
`E_OFFLEAF_HANDLE` does not fire there — but the handles are still dead
references that must be cleaned up.

### Post-cleanup verification

    python -m pytest tests/test_reqtrace.py tests/test_edge_cases.py -v
    python scripts/reqtrace.py generate
    python scripts/reqtrace.py check --strict

`check` must exit 0 with zero `E_OFFLEAF_HANDLE` and zero
`E_MULTI_HANDLE_EVIDENCE` errors.

---

## Part 3 — Tests

Add to `tests/test_edge_cases.py` or a new `tests/test_hierarchy.py`:

### Config validation

- `doc_hierarchy: []` accepted, no enforcement
- `doc_hierarchy: "TRD"` (string, not list) raises ReqtraceError
- `doc_hierarchy: [1, 2]` (non-string elements) raises ReqtraceError

### handle_prefix helper

- handle_prefix("TRD-7") == "TRD"
- handle_prefix("BRD-G3") == "BRD"
- handle_prefix("SEC-CONTROL-7") == "SEC"
- handle_prefix("V2M-ARD-1") == "V2M"

### E_OFFLEAF_HANDLE

- implementation record with handle BRD-1; doc_hierarchy ["BRD","ARD","DRD","TRD"] → exit 1, E_OFFLEAF_HANDLE BRD-1 in stderr
- implementation record with handle TRD-7; same config → exit 0, no error
- verification record with handle BRD-1; same config → exit 0 (rule is implementation-only)
- doc_hierarchy []; implementation record BRD-1 → exit 0 (no enforcement)
- implementation record with handle V2M-ARD-1; doc_hierarchy ["BRD","ARD","DRD","TRD"] → exit 1, E_OFFLEAF_HANDLE V2M-ARD-1 in stderr (V2M prefix is not the leaf)

### E_MULTI_HANDLE_EVIDENCE

- Two implementation records, same file, lines 10 and 11, different handles → exit 1, E_MULTI_HANDLE_EVIDENCE in stderr
- Two implementation records, same file, lines 10 and 20 (gap > 1) → exit 0 (separate blocks)
- Two implementation records, same file, lines 10 and 11, same handle → exit 0 (not a multi-handle violation)
- Two verification records, same file, lines 10 and 11, different handles → exit 0 (implementation-only rule)

---

## Summary

| File | Change |
|---|---|
| `scripts/reqtrace.py` | Add `doc_hierarchy` to `DEFAULT_CONFIG` and validator; add `handle_prefix()`; add two new check errors; strip all off-leaf and V2M-* annotations from own annotation blocks |
| `tests/test_reqtrace.py` | Strip V2M-* block above `test_default_legacy_form_is_reject` |
| `.reqtrace.json` | Add `"doc_hierarchy": ["BRD", "ARD", "DRD", "TRD"]` |
| `docs/trace-ledger.jsonl` | Re-generate after annotation cleanup (`reqtrace generate`) |
| `tests/test_edge_cases.py` or `tests/test_hierarchy.py` | Add hierarchy-enforcement tests (Part 3) |
