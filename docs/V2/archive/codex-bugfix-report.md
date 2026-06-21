```markdown
# Reqtrace V2 Maturity Upgrade — Bug-Fix Report for Codex

## Context

You are working on `scripts/reqtrace.py`, a zero-dependency Python 3 CLI for
grep-native requirements tracing. A second maturity-upgrade pass was just
applied to the working tree (changes are uncommitted). A multi-angle code
review found **15 bugs**. Fix them in severity order. Do not change any feature
behavior beyond what each fix describes. Run `python -m pytest tests/test_reqtrace.py -v`
after each group.

---

## CRITICAL (fix first)

### BUG-1 — `--strict` bare flag is a no-op; indistinguishable from omitting the flag
**File:** `scripts/reqtrace.py` **Lines:** 951–956, 744–745

`build_parser` declares `--strict` with `nargs="?"` and `choices=("ledger","full")`
but no `const`. With `nargs="?"`, the implicit const is `None`. Bare `--strict` →
`args.strict = None`. Absent `--strict` → `args.strict = None`. Both are identical.

At line 744–745:
```python
requested_level = getattr(args, "strict", None)
strict_level = config["strict_level"] if requested_level in {None, False, True} else requested_level
```
Both paths produce `strict_level = config["strict_level"]`. The flag has no effect.

**Fix:**
1. Add `const="ledger"` to the argparse declaration so bare `--strict` maps to `"ledger"`:
```python
check.add_argument(
    "--strict",
    nargs="?",
    const="ledger",
    choices=("ledger", "full"),
    help="use the configured policy, or specify ledger or full explicitly",
)
```
2. Simplify the resolution (drop the dead `False` branch — argparse with string
   choices never produces `False`):
```python
requested_level = getattr(args, "strict", None)
strict_level = requested_level if requested_level is not None else config["strict_level"]
```

---

### BUG-2 — `command_init` rollback leaves orphaned directories
**File:** `scripts/reqtrace.py` **Lines:** 369–370, 537–543

`atomic_write_text` calls `path.parent.mkdir(parents=True, exist_ok=True)` at
line 370 *before* writing. The rollback in `command_init` (lines 541–542) only
calls `path.unlink(missing_ok=True)` on files — it never removes directories
that were created as a side effect.

**Failure scenario:** Project has no `docs/` dir. Step (1) writes
`.reqtrace.json` OK. Step (2) `atomic_write_text(registry_path)` creates
`docs/` then succeeds. Step (3) `write_ledger` raises (e.g. disk full).
Rollback removes both files but leaves `docs/` as an empty orphan.
Re-running `init` finds nothing to reject (files gone) but leaves `docs/`
behind indefinitely.

**Fix:** Track created directories alongside files; remove them in reverse
order on rollback:
```python
written_files: list[Path] = []
created_dirs: list[Path] = []
try:
    for path, content_fn in [
        (config_path, lambda: json.dumps(config, indent=2) + "\n"),
        (registry_path, lambda: ""),
    ]:
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.append(path.parent)
        atomic_write_text(path, content_fn())
        written_files.append(path)
    write_ledger(ledger_path, [])
except ReqtraceError as error:
    for path in written_files:
        path.unlink(missing_ok=True)
    for directory in reversed(created_dirs):
        try:
            directory.rmdir()
        except OSError:
            pass
    print(error, file=sys.stderr)
    return 2
```

---

### BUG-3 — `find_project_root` silently returns cwd when no config exists
**File:** `scripts/reqtrace.py` **Lines:** 220–224, 975–976

When no `.reqtrace.json` is found in any parent, `find_project_root` returns
`start` (cwd). `load_config` then succeeds silently with `DEFAULT_CONFIG`
(line 148 skips the update when `config_path.exists()` is False). Running
`reqtrace check` in any random directory exits 0 with no warning.

**Fix:** Raise in `find_project_root` when no config is found:
```python
def find_project_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".reqtrace.json").exists():
            return candidate
    raise ReqtraceError(
        "no .reqtrace.json found in this directory or any parent; "
        "run 'reqtrace init' to set up a new project"
    )
```
The `ReqtraceError` propagates to `main`'s except block and exits 2.

---

### BUG-4 — `command_init` uses raw `Path.cwd()` before `find_project_root`, creating shadow configs in subdirectories
**File:** `scripts/reqtrace.py` **Lines:** 972–974

`main` calls `command_init(root, args)` with `root = Path.cwd().resolve()` —
before any root-finding logic. Running `reqtrace init` from `/repo/src/` where
`/repo/.reqtrace.json` already exists creates `/repo/src/.reqtrace.json`.
Subsequent commands run from `/repo/src/` find the shadow config first.

**Fix:** Before calling `command_init`, check if any parent already has a
`.reqtrace.json` and refuse:
```python
if args.command == "init":
    # Check that we're not inside an existing project before initialising
    try:
        existing_root = find_project_root(root)
        print(
            f"E_INIT_EXISTS already inside a Reqtrace project rooted at "
            f"{existing_root.as_posix()}",
            file=sys.stderr,
        )
        return 2
    except ReqtraceError:
        pass  # no config found — safe to init here
    return command_init(root, args)
```
(This requires BUG-3's fix — `find_project_root` now raises when nothing is
found, so the `except ReqtraceError: pass` path is the "not inside a project"
case.)

---

## HIGH

### BUG-5 — `scan --diff` builds committed_identities from a partially-parsed ledger when `read_ledger` returns errors
**File:** `scripts/reqtrace.py` **Lines:** 566–569

When the ledger file has a corrupt line, `read_ledger` returns
`(partial_records, [parse_errors])`. Line 567 appends parse errors to `errors`.
Line 568 then builds `committed_identities` from `partial_records` only.
Line 569 filters current records: any record whose source_identity matched a
failed-parse line is not in `committed_identities` → shown as "new" in `--diff`
output. The user sees already-committed annotations flagged as new.

**Fix:** Skip the diff filter when ledger errors are present:
```python
if diff:
    committed, ledger_errors = read_ledger(project_path(root, config["ledger_path"]))
    errors.extend(ledger_errors)
    if not ledger_errors:
        committed_identities = {record.source_identity() for record in committed}
        records = [record for record in records if record.source_identity() not in committed_identities]
```

---

### BUG-6 — `generate --register-unknown` leaves registry/ledger permanently out of sync if `write_ledger` fails
**File:** `scripts/reqtrace.py` **Lines:** 617–621

`register_unknown_handles` writes new handles to the registry at line 617.
`write_ledger` is called at line 621. If `write_ledger` raises (e.g. disk
quota), the registry has entries for handles the ledger doesn't contain. The
two files are permanently out of sync; the user cannot recover without manual
repair.

**Fix:** Reverse the order — write the ledger first, then register handles. A
stale registry is recoverable (run `generate --register-unknown` again); a
registry with handles that aren't in the ledger is not:
```python
write_ledger(project_path(root, config["ledger_path"]), records)
if args.register_unknown:
    registry_errors = register_unknown_handles(
        project_path(root, config["registry_path"]), records
    )
    if registry_errors:
        print_messages(registry_errors)
        return 2
return 0
```

---

### BUG-7 — `scan --diff` "no annotations" message fires wrong branch on empty repo
**File:** `scripts/reqtrace.py` **Lines:** 585–589

In `--diff` mode with a repository that has zero annotations,
`scan.occurrences` and `scan.legacy_occurrences` are both `[]`. Line 586:
`if diff and (scan.occurrences or scan.legacy_occurrences)` → `False`. Falls
to `elif not scan.legacy_occurrences:` → prints "No Reqtrace comments found."
— wrong message for a diff invocation.

**Fix:** Use total annotation count to decide:
```python
if not grouped:
    total = len(scan.occurrences) + len(scan.legacy_occurrences)
    if diff and total > 0:
        print("No new annotations (all are already in the committed ledger).")
    else:
        print("No Reqtrace comments found.")
```

---

## MEDIUM

### BUG-8 — `source_identity()` includes `kind`; moving a file between role dirs makes `scan --diff` report it as new
**File:** `scripts/reqtrace.py` **Lines:** 122–123

`source_identity()` returns `(handle, path, line, kind)`. When an annotation
moves from `src/auth.py` (kind=`implementation`) to `tests/auth.py`
(kind=`verification`), the old and new `source_identity` tuples differ. `scan
--diff` shows it as a new annotation. The annotation is the same one relocated;
the user's diff output is misleading.

**Fix:** Drop `kind` from `source_identity` so it matches on physical location
only:
```python
def source_identity(self) -> tuple[str, str, int]:
    return (self.handle, self.path, self.line)
```

---

### BUG-9 — `command_report` bucket `"full"` requires only `implementation`, not `implementation + verification`
**File:** `scripts/reqtrace.py` **Lines:** 814–816

Line 815: `elif implementation: bucket = "full"`. A handle traced only in
`src/` (no test) is reported as "full coverage" alongside handles with both
implementation and verification evidence. The summary count is misleading.

**Fix:** `"full"` should require both:
```python
if implementation and verification:
    bucket = "full"
elif implementation or verification:
    bucket = "partial"
else:
    bucket = "zero"
```

---

### BUG-10 — `records_from_occurrences` always tries exactly 3 lengths; gives up instead of escalating further
**File:** `scripts/reqtrace.py` **Lines:** 331–347

`lengths = [id_length, id_length+2, id_length+4]` is a fixed 3-element list.
If all three lengths produce collisions, the function returns `E_ID_COLLISION`
with no recovery path. A while loop escalating to a maximum cap handles
pathological repos without manual config changes.

**Fix:**
```python
MAX_ID_LENGTH = 16

def records_from_occurrences(
    occurrences: Iterable[Occurrence], id_length: int
) -> tuple[list[LedgerRecord], list[str]]:
    ordered = sorted(occurrences, key=lambda item: (item.handle, item.path, item.line))
    length = id_length
    while length <= MAX_ID_LENGTH:
        records = [
            LedgerRecord(item.handle, short_id(item.path, item.line, length), item.path, item.line, item.kind)
            for item in ordered
        ]
        ids_by_handle: dict[str, set[str]] = defaultdict(set)
        collision = False
        for record in records:
            if record.id in ids_by_handle[record.handle]:
                collision = True
                break
            ids_by_handle[record.handle].add(record.id)
        if not collision:
            return records, []
        length += 1
    return [], [f"E_ID_COLLISION unable to disambiguate occurrence IDs at {MAX_ID_LENGTH} hex characters"]
```

---

## LOW / CLEANUP

### BUG-11 — `command_check` runs 4 full `sorted()` calls; hint sorts run unconditionally
**File:** `scripts/reqtrace.py` **Lines:** 734–741

The `source_identity` sorts at lines 738–740 (used only to decide whether to
print the id_length hint) run on every `check` invocation, even when there is
no stale-ledger mismatch to hint about. Move them inside the mismatch branch:
```python
if sorted(record.identity() for record in generated) != sorted(
    record.identity() for record in committed
):
    print("E_STALE_LEDGER committed ledger differs from a fresh scan", file=sys.stderr)
    if sorted(record.source_identity() for record in generated) == sorted(
        record.source_identity() for record in committed
    ):
        print("hint: ledger may need regeneration after id_length change", file=sys.stderr)
    failures = True
```
(They are already inside the mismatch branch in the current code — verify and
leave as-is if correct; the redundancy to fix is that they always execute even
when the outer `elif not errors:` is False.)

---

### BUG-12 — `ledger_record_from_json` field-order coupling: unpacks by iterating `required` tuple
**File:** `scripts/reqtrace.py` **Line:** 418

```python
handle, record_id, path, line, kind = (value[field] for field in required)
```
If `required` is ever reordered without matching `LedgerRecord`'s field order,
values silently swap (all are strings or ints — no TypeError). Unpack
explicitly:
```python
return LedgerRecord(
    handle=value["handle"],
    id=value["id"],
    path=value["path"],
    line=value["line"],
    kind=value["kind"],
)
```

---

### BUG-13 — `False` in strict-level sentinel set is dead code
**File:** `scripts/reqtrace.py` **Line:** 745

Addressed by BUG-1's fix (`requested_level is not None` check). No separate
action needed; verify `False` is removed from any remaining sentinel set after
BUG-1 is applied.

---

### BUG-14 — `command_init` instruction output hardcodes `python scripts/reqtrace.py`
**File:** `scripts/reqtrace.py` **Lines:** 545–547

When installed as a package entry-point, the instructions tell users to run a
path that may not exist. Use `sys.argv[0]` or a constant:
```python
invocation = Path(sys.argv[0]).name  # e.g. "reqtrace" or "reqtrace.py"
print(f"1. Add @reqtrace <HANDLE> near source or test evidence.")
print(f"2. Run {invocation} generate.")
print(f"3. Run {invocation} check --strict.")
```

---

### BUG-15 — `register_unknown_handles` silently discards concurrent external edits to the registry
**File:** `scripts/reqtrace.py` **Lines:** 494–501

`read_registry` reads the file at line 487; `atomic_write_text` overwrites it
at line 501. A concurrent external edit between those two calls is lost. This
is a low-severity race (single-user CLI), but the pattern is worth noting. No
fix required for CLI use; document the limitation with a comment if the
function is ever exposed to concurrent callers.

---

## Verification Checklist

After all fixes:
```
python -m pytest tests/test_reqtrace.py -v              # all tests pass
python scripts/reqtrace.py init                          # exit 0 in empty dir; exit 2 from project subdir
python scripts/reqtrace.py check                         # exit 0, honors config strict_level
python scripts/reqtrace.py check --strict                # exit 0, uses ledger level (not silent no-op)
python scripts/reqtrace.py check --strict=full           # exit 0, uses full level
python scripts/reqtrace.py scan --diff                   # exit 0, correct message on zero-annotation repo
python scripts/reqtrace.py report --format github        # exit 0, 'full' bucket requires impl+verif
python scripts/reqtrace.py generate --register-unknown   # exit 0, ledger written before registry
```
```