"""
Edge-case tests targeting the 15 bugs identified in the Reqtrace V2 code review.

Each test is labelled with the BUG-N it exercises. Some tests probe pre-fix
behaviour (they document what currently goes wrong) while others probe the
fix contract (what must hold after the fix). Codex should make ALL tests pass.

One happy-path smoke test is included at the bottom.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "reqtrace.py"
MODULE_SPEC = importlib.util.spec_from_file_location("reqtrace_edge", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reqtrace = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = reqtrace
MODULE_SPEC.loader.exec_module(reqtrace)
MARKER = "@req" + "trace"


class EdgeCaseTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=fixture_root)
        root = Path(tmp.name)
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "tests").mkdir()
        return tmp

    def make_empty_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=fixture_root)

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def config(self, root: Path) -> dict:
        return reqtrace.load_config(root)

    def ledger_record(self, handle: str, id: str, path: str, line: int, kind: str) -> str:
        return json.dumps({"handle": handle, "id": id, "path": path, "line": line, "kind": kind}) + "\n"

    # ------------------------------------------------------------------
    # BUG-1: bare --strict is a no-op without const="ledger"
    # ------------------------------------------------------------------

    def test_bug1_bare_strict_flag_produces_ledger_not_none(self) -> None:
        """After the fix, bare --strict must parse to "ledger", not None."""
        parser = reqtrace.build_parser()
        args = parser.parse_args(["check", "--strict"])
        self.assertEqual(
            args.strict,
            "ledger",
            "bare --strict must produce 'ledger' (const); got None means BUG-1 is unfixed",
        )

    def test_bug1_strict_equals_full_still_works(self) -> None:
        """--strict=full must still produce 'full'."""
        parser = reqtrace.build_parser()
        args = parser.parse_args(["check", "--strict=full"])
        self.assertEqual(args.strict, "full")

    def test_bug1_absent_strict_flag_is_none(self) -> None:
        """Absent flag must produce None so the config default is used."""
        parser = reqtrace.build_parser()
        args = parser.parse_args(["check"])
        self.assertIsNone(args.strict)

    def test_bug1_bare_strict_on_fresh_ledger_exits_0(self) -> None:
        """
        Bare --strict on a project with a fresh ledger and no registry must
        exit 0 (ledger-level check passes) — not silently use config default.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False))
            # BUG-1: if const is missing, args.strict=None falls through to
            # config["strict_level"]="ledger" by accident — same result, but
            # --strict=full would also silently do nothing. We test the parse
            # value directly (above) and verify the function call honours it.
            rc = reqtrace.command_check(root, config, SimpleNamespace(strict="ledger"))
            self.assertEqual(rc, 0)

    def test_bug1_bare_strict_does_not_enforce_full_when_config_is_ledger(self) -> None:
        """
        Config strict_level=ledger + bare --strict must exit 0 even with an
        unregistered handle. If the fix naively escalates to config level when
        requested_level is None (pre-fix behaviour), this would still pass; the
        real trap is when config="full" and the user passes bare --strict to
        downgrade to ledger. Test that too.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} UNREGISTERED-HANDLE\n")
            # config has no handle-registry entries for UNREGISTERED-HANDLE
            config = self.config(root)
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False))
            rc = reqtrace.command_check(root, config, SimpleNamespace(strict="ledger"))
            self.assertEqual(rc, 0)

    def test_bug1_full_config_with_bare_strict_flag_uses_ledger_not_full(self) -> None:
        """
        When config has strict_level=full, bare --strict=ledger (from the
        const after the fix) must win and NOT enforce registry check.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(root / ".reqtrace.json", json.dumps({"strict_level": "full"}) + "\n")
            config = self.config(root)
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False))
            # strict="ledger" explicitly should NOT trigger E_HANDLE_NOT_REGISTERED
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = reqtrace.command_check(root, config, SimpleNamespace(strict="ledger"))
            self.assertEqual(rc, 0, f"strict=ledger should pass; stderr: {stderr.getvalue()!r}")
            self.assertNotIn("E_HANDLE_NOT_REGISTERED", stderr.getvalue())

    # ------------------------------------------------------------------
    # BUG-2: command_init rollback leaves orphaned directories
    # ------------------------------------------------------------------

    def test_bug2_init_rollback_removes_created_docs_dir(self) -> None:
        """
        When registry write succeeds but ledger write fails, the docs/
        directory created during init must be removed in rollback — not left as
        an orphan.
        """
        with self.make_empty_root() as directory:
            root = Path(directory)
            original_write_ledger = reqtrace.write_ledger

            def fail_ledger(path, records):
                raise reqtrace.ReqtraceError("injected ledger failure")

            with patch.object(reqtrace, "write_ledger", side_effect=fail_ledger):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = reqtrace.command_init(root, SimpleNamespace())
            self.assertEqual(rc, 2)
            self.assertFalse((root / "docs").exists(), "orphaned docs/ dir must be removed on rollback")
            self.assertFalse((root / ".reqtrace.json").exists())

    def test_bug2_init_rollback_does_not_remove_pre_existing_docs_dir(self) -> None:
        """
        If docs/ already existed before init was called, the rollback must NOT
        remove it — only directories created during this init run are in scope.
        """
        with self.make_empty_root() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            marker_file = root / "docs" / "existing-file.txt"
            marker_file.write_text("keep me", encoding="utf-8")

            def fail_ledger(path, records):
                raise reqtrace.ReqtraceError("injected ledger failure")

            with patch.object(reqtrace, "write_ledger", side_effect=fail_ledger):
                with contextlib.redirect_stderr(io.StringIO()):
                    reqtrace.command_init(root, SimpleNamespace())

            self.assertTrue((root / "docs").exists(), "pre-existing docs/ must survive rollback")
            self.assertTrue(marker_file.exists())

    # ------------------------------------------------------------------
    # BUG-3: find_project_root silently returns cwd with no config
    # ------------------------------------------------------------------

    def test_bug3_commands_exit_2_outside_project(self) -> None:
        """
        Running check (or any non-init command) in a directory with no
        .reqtrace.json anywhere in the tree must exit 2 with a clear error.
        Previously it silently used DEFAULT_CONFIG and exited 0.
        """
        with tempfile.TemporaryDirectory() as directory:
            root_outside = Path(directory)
            original_dir = Path.cwd()
            try:
                os.chdir(root_outside)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = reqtrace.main(["check"])
            finally:
                os.chdir(original_dir)
        self.assertEqual(rc, 2, "check outside a project must exit 2")
        self.assertTrue(
            stderr.getvalue().strip(),
            "must print an error message explaining no project was found",
        )

    def test_bug3_find_project_root_raises_when_no_config(self) -> None:
        """find_project_root must raise ReqtraceError when no .reqtrace.json exists."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(reqtrace.ReqtraceError):
                reqtrace.find_project_root(Path(directory))

    def test_bug3_find_project_root_locates_config_in_parent(self) -> None:
        """find_project_root must find .reqtrace.json in a parent directory."""
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({}) + "\n")
            nested = root / "src" / "deep" / "nested"
            nested.mkdir(parents=True, exist_ok=True)
            found = reqtrace.find_project_root(nested)
            self.assertEqual(found, root)

    # ------------------------------------------------------------------
    # BUG-4: init creates shadow config if run inside an existing project
    # ------------------------------------------------------------------

    def test_bug4_init_inside_existing_project_exits_2(self) -> None:
        """
        Running init from inside a directory whose ancestor already has
        .reqtrace.json must exit 2 and must NOT create a second config.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({}) + "\n")
            subdir = root / "src"
            original_dir = Path.cwd()
            try:
                os.chdir(subdir)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = reqtrace.main(["init"])
            finally:
                os.chdir(original_dir)
        self.assertEqual(rc, 2)
        self.assertFalse((subdir / ".reqtrace.json").exists(), "shadow config must not be created")
        self.assertIn("E_INIT_EXISTS", stderr.getvalue())

    def test_bug4_init_in_project_root_itself_exits_2_not_overwrite(self) -> None:
        """Running init in a directory that already IS the project root must also refuse."""
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"strict_level": "ledger"}) + "\n")
            original_dir = Path.cwd()
            try:
                os.chdir(root)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = reqtrace.main(["init"])
            finally:
                os.chdir(original_dir)
            self.assertEqual(rc, 2)
            # config must not have been overwritten
            config = json.loads((root / ".reqtrace.json").read_text(encoding="utf-8"))
            self.assertEqual(config["strict_level"], "ledger")

    # ------------------------------------------------------------------
    # BUG-5: scan --diff builds committed_identities from a partial ledger
    # ------------------------------------------------------------------

    def test_bug5_scan_diff_with_corrupt_ledger_does_not_produce_false_new_annotations(self) -> None:
        """
        When the ledger has a corrupt line, scan --diff must NOT silently show
        all annotations as "new" (because the corrupt entry wasn't in
        committed_identities). It should either skip the diff filter or report
        the parse error and show zero diff output.
        """
        with self.make_root() as directory:
            root = Path(directory)
            # One real ledger record + one corrupt line
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                self.ledger_record("ADR-0012", "abcd", "src/feature.py", 1, "implementation")
                + "{BAD JSON\n",
            )
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            json_out = io.StringIO()
            stderr_out = io.StringIO()
            with contextlib.redirect_stdout(json_out), contextlib.redirect_stderr(stderr_out):
                rc = reqtrace.command_scan(
                    root, self.config(root), SimpleNamespace(format="json", diff=True)
                )
            self.assertEqual(rc, 0)
            result = json.loads(json_out.getvalue())
            # ADR-0012 at src/feature.py:1 is in the ledger (good line) —
            # it must NOT appear as a new annotation despite the corrupt line
            found_as_new = any(
                entry["handle"] == "ADR-0012" and entry["path"] == "src/feature.py"
                for entry in result
            )
            self.assertFalse(
                found_as_new,
                "annotation already in ledger must not appear as new when ledger has a corrupt line",
            )
            self.assertIn("E_LEDGER_PARSE", stderr_out.getvalue())

    def test_bug5_scan_diff_with_fully_corrupt_ledger_shows_error_not_all_new(self) -> None:
        """
        A fully corrupt ledger (every line unparseable) must produce a parse
        error, not silently list every annotation as new.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "trace-ledger.jsonl", "{BAD}\n{ALSO BAD}\n")
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            json_out = io.StringIO()
            stderr_out = io.StringIO()
            with contextlib.redirect_stdout(json_out), contextlib.redirect_stderr(stderr_out):
                reqtrace.command_scan(
                    root, self.config(root), SimpleNamespace(format="json", diff=True)
                )
            self.assertIn("E_LEDGER_PARSE", stderr_out.getvalue())

    # ------------------------------------------------------------------
    # BUG-6: generate --register-unknown writes registry before ledger
    # ------------------------------------------------------------------

    def test_bug6_ledger_written_before_registry(self) -> None:
        """
        If write_ledger raises after registry was already written, the registry
        ends up ahead of the ledger. After the fix, the ledger must be written
        BEFORE the registry so failure leaves the ledger as the source of truth.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} NEW-HANDLE\n")
            write_order: list[str] = []
            original_write_ledger = reqtrace.write_ledger
            original_register = reqtrace.register_unknown_handles

            def tracking_ledger(path, records):
                write_order.append("ledger")
                return original_write_ledger(path, records)

            def tracking_register(path, records):
                write_order.append("registry")
                return original_register(path, records)

            with (
                patch.object(reqtrace, "write_ledger", side_effect=tracking_ledger),
                patch.object(reqtrace, "register_unknown_handles", side_effect=tracking_register),
            ):
                rc = reqtrace.command_generate(
                    root, self.config(root), SimpleNamespace(register_unknown=True)
                )
            self.assertEqual(rc, 0)
            self.assertEqual(
                write_order,
                ["ledger", "registry"],
                "ledger must be written before registry; order was: " + str(write_order),
            )

    def test_bug6_registry_failure_does_not_corrupt_ledger(self) -> None:
        """
        When register_unknown_handles raises, the ledger must already be written
        and must contain the correct records.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} NEW-HANDLE\n")
            config = self.config(root)

            def fail_register(path, records):
                raise reqtrace.ReqtraceError("registry write failed")

            with patch.object(reqtrace, "register_unknown_handles", side_effect=fail_register):
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=True))
            self.assertEqual(rc, 2)
            ledger, errors = reqtrace.read_ledger(
                reqtrace.project_path(root, config["ledger_path"])
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(ledger), 1)
            self.assertEqual(ledger[0].handle, "NEW-HANDLE")

    # ------------------------------------------------------------------
    # BUG-7: scan --diff "no new annotations" message fires on wrong branch
    # ------------------------------------------------------------------

    def test_bug7_diff_on_empty_repo_prints_no_reqtrace_comments(self) -> None:
        """
        On a repo with zero annotations, scan --diff must print
        "No Reqtrace comments found." — not the "no new annotations" message.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "trace-ledger.jsonl", "")
            text_out = io.StringIO()
            with contextlib.redirect_stdout(text_out):
                reqtrace.command_scan(
                    root, self.config(root), SimpleNamespace(format="text", diff=True)
                )
            output = text_out.getvalue()
            self.assertIn("No Reqtrace comments found", output)
            self.assertNotIn("No new annotations", output)

    def test_bug7_diff_when_all_annotations_committed_prints_no_new(self) -> None:
        """
        When annotations exist but all are already in the ledger, scan --diff
        must print "No new annotations (all are already in the committed ledger)."
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False))
            text_out = io.StringIO()
            with contextlib.redirect_stdout(text_out):
                reqtrace.command_scan(
                    root, config, SimpleNamespace(format="text", diff=True)
                )
            self.assertIn("No new annotations", text_out.getvalue())

    # ------------------------------------------------------------------
    # BUG-8: source_identity includes kind — move between role dirs = false new
    # ------------------------------------------------------------------

    def test_bug8_annotation_moved_between_role_dirs_not_shown_as_new(self) -> None:
        """
        After BUG-8 fix (kind dropped from source_identity), changing a path's
        inferred role changes kind but not the annotation's physical location.
        scan --diff must NOT show that annotation as new.
        """
        with self.make_root() as directory:
            root = Path(directory)
            # Ledger records src/feature.py as implementation.
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                self.ledger_record("ADR-0012", "abcd", "src/feature.py", 1, "implementation"),
            )
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            config["role_map"] = {"src/**": "verification"}
            json_out = io.StringIO()
            with contextlib.redirect_stdout(json_out):
                reqtrace.command_scan(
                    root, config, SimpleNamespace(format="json", diff=True)
                )
            result = json.loads(json_out.getvalue())
            found_as_new = any(
                entry["handle"] == "ADR-0012" and entry["path"] == "src/feature.py"
                for entry in result
            )
            self.assertFalse(
                found_as_new,
                "changing only an annotation role must not show it as new in --diff",
            )

    # ------------------------------------------------------------------
    # BUG-9: command_report bucket "full" requires impl+verif, not impl alone
    # ------------------------------------------------------------------

    def test_bug9_implementation_only_is_partial_not_full(self) -> None:
        """
        A handle with only implementation evidence must land in the 'partial'
        bucket, not 'full'. Before the fix it lands in 'full'.
        """
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "ADR-0012", "type": "adr"}) + "\n",
            )
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                self.ledger_record("ADR-0012", "abcd", "src/feature.py", 1, "implementation"),
            )
            json_out = io.StringIO()
            with contextlib.redirect_stdout(json_out):
                reqtrace.command_report(
                    root, self.config(root), SimpleNamespace(format="json")
                )
            report = json.loads(json_out.getvalue())
            full_handles = [entry["handle"] for entry in report["full"]]
            partial_handles = [entry["handle"] for entry in report["partial"]]
            self.assertNotIn("ADR-0012", full_handles, "impl-only must not be in 'full' bucket")
            self.assertIn("ADR-0012", partial_handles, "impl-only must be in 'partial' bucket")

    def test_bug9_verification_only_is_partial_not_full(self) -> None:
        """A handle with only verification evidence must also be partial, not full."""
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                self.ledger_record("ADR-0012", "abcd", "tests/feature.py", 1, "verification"),
            )
            json_out = io.StringIO()
            with contextlib.redirect_stdout(json_out):
                reqtrace.command_report(
                    root, self.config(root), SimpleNamespace(format="json")
                )
            report = json.loads(json_out.getvalue())
            self.assertNotIn(
                "ADR-0012",
                [e["handle"] for e in report["full"]],
                "verification-only must not be in 'full' bucket",
            )

    def test_bug9_both_impl_and_verif_is_full(self) -> None:
        """A handle with both implementation and verification must be in 'full'."""
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                self.ledger_record("ADR-0012", "a001", "src/feature.py", 1, "implementation")
                + self.ledger_record("ADR-0012", "a002", "tests/feature.py", 1, "verification"),
            )
            json_out = io.StringIO()
            with contextlib.redirect_stdout(json_out):
                reqtrace.command_report(
                    root, self.config(root), SimpleNamespace(format="json")
                )
            report = json.loads(json_out.getvalue())
            self.assertIn("ADR-0012", [e["handle"] for e in report["full"]])

    # ------------------------------------------------------------------
    # BUG-10: records_from_occurrences gives up after 3 lengths
    # ------------------------------------------------------------------

    def test_bug10_collision_escalates_beyond_four_and_six(self) -> None:
        """
        When id_length=4 and lengths 4, 6 both collide, the function must
        keep escalating (not give up at length+4=8) until it resolves or hits
        MAX_ID_LENGTH.
        """
        original_short_id = reqtrace.short_id
        tried_lengths: list[int] = []
        try:
            def collide_until_8(path: str, line: int, length: int = 4) -> str:
                tried_lengths.append(length)
                if length < 8:
                    return "x" * length  # always collide for lengths < 8
                return original_short_id(path, line, length)

            reqtrace.short_id = collide_until_8
            records, errors = reqtrace.records_from_occurrences(
                [
                    reqtrace.Occurrence("HANDLE", "src/a.py", 1, "implementation"),
                    reqtrace.Occurrence("HANDLE", "src/b.py", 1, "implementation"),
                ],
                4,
            )
        finally:
            reqtrace.short_id = original_short_id
        self.assertEqual(errors, [])
        self.assertGreater(len(records), 0)
        # Must have tried lengths 4, 5, 6, 7, 8 — not just 4, 6, 8
        self.assertIn(5, tried_lengths, "must try every consecutive length, not skip by 2")
        self.assertIn(7, tried_lengths)

    def test_bug10_exhausted_escalation_returns_collision_error(self) -> None:
        """
        When all lengths up to MAX_ID_LENGTH collide, records_from_occurrences
        must return a single E_ID_COLLISION error (not raise).
        """
        original_short_id = reqtrace.short_id
        try:
            reqtrace.short_id = lambda path, line, length=4: "0" * length
            records, errors = reqtrace.records_from_occurrences(
                [
                    reqtrace.Occurrence("HANDLE", "src/a.py", 1, "implementation"),
                    reqtrace.Occurrence("HANDLE", "src/b.py", 1, "implementation"),
                ],
                4,
            )
        finally:
            reqtrace.short_id = original_short_id
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("E_ID_COLLISION", errors[0])

    # ------------------------------------------------------------------
    # BUG-12: ledger_record_from_json positional unpacking
    # ------------------------------------------------------------------

    def test_bug12_ledger_record_from_json_fields_are_correct(self) -> None:
        """
        After the fix (explicit keyword construction), reordering the 'required'
        tuple or the unpacking order must not silently swap field values. We
        verify the parsed record matches what was written.
        """
        with self.make_root() as directory:
            root = Path(directory)
            ledger_path = root / "docs" / "trace-ledger.jsonl"
            self.write(
                ledger_path,
                json.dumps({
                    "handle": "AUTH-SESSION",
                    "id": "ffff",
                    "path": "src/auth.py",
                    "line": 42,
                    "kind": "implementation",
                }) + "\n",
            )
            records, errors = reqtrace.read_ledger(ledger_path)
        self.assertEqual(errors, [])
        r = records[0]
        self.assertEqual(r.handle, "AUTH-SESSION")
        self.assertEqual(r.id, "ffff")
        self.assertEqual(r.path, "src/auth.py")
        self.assertEqual(r.line, 42)
        self.assertEqual(r.kind, "implementation")

    def test_bug12_kind_and_path_do_not_swap(self) -> None:
        """
        A record where 'path' and 'kind' happen to both look like strings
        must not have them swapped. This would only happen if the positional
        unpacking order diverged from the required-tuple order.
        """
        with self.make_root() as directory:
            root = Path(directory)
            ledger_path = root / "docs" / "trace-ledger.jsonl"
            # Craft a record where kind="tests/a.py" looks like a path — swap would be obvious
            self.write(
                ledger_path,
                json.dumps({
                    "handle": "H",
                    "id": "1234",
                    "path": "src/unusual_kind_string.py",
                    "line": 7,
                    "kind": "verification",
                }) + "\n",
            )
            records, errors = reqtrace.read_ledger(ledger_path)
        self.assertEqual(errors, [])
        self.assertEqual(records[0].kind, "verification")
        self.assertNotEqual(records[0].path, "verification")

    # ------------------------------------------------------------------
    # BUG-14: command_init hardcodes "python scripts/reqtrace.py" in output
    # ------------------------------------------------------------------

    def test_bug14_init_instructions_do_not_hardcode_script_path(self) -> None:
        """
        The instructions printed after init must not contain the literal string
        'python scripts/reqtrace.py'. They should use sys.argv[0] or a similar
        relative/contextual name.
        """
        with self.make_empty_root() as directory:
            root = Path(directory)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                reqtrace.command_init(root, SimpleNamespace())
            instructions = stdout.getvalue()
            self.assertNotIn(
                "python scripts/reqtrace.py",
                instructions,
                "init instructions must not hardcode the script invocation path",
            )

    # ------------------------------------------------------------------
    # BUG-15 (informational): register_unknown_handles race is acknowledged
    # ------------------------------------------------------------------

    def test_bug15_register_unknown_preserves_pre_existing_registry_entries(self) -> None:
        """
        register_unknown_handles must preserve entries already in the registry
        file. If a concurrent write added an entry between read and write, the
        original entries must at minimum survive (the race may lose new-only
        entries but must not delete existing ones). We test the single-threaded
        version of this: entries written before the call must still be present.
        """
        with self.make_root() as directory:
            root = Path(directory)
            registry_path = root / "docs" / "handle-registry.jsonl"
            # Pre-existing entry
            self.write(
                registry_path,
                json.dumps({"handle": "EXISTING", "type": "requirement"}) + "\n",
            )
            records = [reqtrace.LedgerRecord("NEW-HANDLE", "0000", "src/a.py", 1, "implementation")]
            reqtrace.register_unknown_handles(registry_path, records)
            registry, errors = reqtrace.read_registry(registry_path)
        self.assertEqual(errors, [])
        handles = {entry["handle"] for entry in registry}
        self.assertIn("EXISTING", handles, "pre-existing registry entries must survive")
        self.assertIn("NEW-HANDLE", handles, "new unknown handle must be appended")

    # ------------------------------------------------------------------
    # Happy-path smoke test
    # ------------------------------------------------------------------

    def test_happy_path_full_generate_render_check_pipeline(self) -> None:
        """
        A complete project: init → annotate → generate --register-unknown →
        render → check --strict=full → report --format github must all
        exit 0 with no errors.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "docs").mkdir()
            original_dir = Path.cwd()
            try:
                os.chdir(root)

                # Step 1: init
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = reqtrace.main(["init"])
                self.assertEqual(rc, 0, f"init failed: {stdout.getvalue()!r}")

                # Step 2: annotate source and test files
                (root / "src" / "auth.py").write_text(
                    f"# {MARKER} AUTH-LOGIN\ndef login(): ...\n", encoding="utf-8"
                )
                (root / "tests" / "test_auth.py").write_text(
                    f"# {MARKER} AUTH-LOGIN\ndef test_login(): ...\n", encoding="utf-8"
                )
                # Step 3: add a docs file with a ledger block for render
                (root / "docs" / "requirements.md").write_text(
                    "# AUTH-LOGIN\n\n"
                    "<!-- reqtrace:ledger:start handle=AUTH-LOGIN -->\n"
                    "<!-- reqtrace:ledger:end -->\n",
                    encoding="utf-8",
                )

                # Step 4: register handle in the registry
                config_file = root / ".reqtrace.json"
                config = json.loads(config_file.read_text(encoding="utf-8"))
                registry_path = root / config.get("registry_path", "docs/handle-registry.jsonl")
                registry_path.write_text(
                    json.dumps({"handle": "AUTH-LOGIN", "type": "requirement"}) + "\n",
                    encoding="utf-8",
                )

                # Step 5: generate
                rc = reqtrace.main(["generate"])
                self.assertEqual(rc, 0, "generate must exit 0")

                # Step 6: render
                rc = reqtrace.main(["render"])
                self.assertEqual(rc, 0, "render must exit 0")

                # Step 7: check --strict=full
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = reqtrace.main(["check", "--strict=full"])
                self.assertEqual(rc, 0, f"check --strict=full must exit 0; stderr: {stderr.getvalue()!r}")

                # Step 8: report --format github
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = reqtrace.main(["report", "--format", "github"])
                self.assertEqual(rc, 0, "report --format github must exit 0")
                report_lines = stdout.getvalue().splitlines()
                self.assertEqual(report_lines[0], "| Handle | Implementation | Verification | Documentation | Status |")
                auth_row = next((line for line in report_lines if "AUTH-LOGIN" in line), None)
                self.assertIsNotNone(auth_row, "AUTH-LOGIN must appear in report")
                self.assertIn("yes", auth_row, "AUTH-LOGIN must show implementation or verification as yes")

            finally:
                os.chdir(original_dir)


if __name__ == "__main__":
    unittest.main()
