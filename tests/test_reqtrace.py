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
MODULE_SPEC = importlib.util.spec_from_file_location("reqtrace_under_test", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reqtrace = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = reqtrace
MODULE_SPEC.loader.exec_module(reqtrace)
MARKER = "@req" + "trace"


class ReqtraceCliTests(unittest.TestCase):
    def make_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=fixture_root)
        root = Path(temporary.name)
        (root / "docs").mkdir()
        (root / "src").mkdir()
        return temporary

    def make_empty_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=fixture_root)

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def config(self, root: Path) -> dict[str, object]:
        return reqtrace.load_config(root)

    def test_grammar_accepts_alphanumeric_handle_segments(self) -> None:
        for handle in (
            "AUTH",
            "ADR-0012",
            "ADR-0012-V2",
            "SEC-CONTROL-7",
            "TRD-12",
            "ONE-TWO-THREE-FOUR-FIVE-SIX-SEVEN-EIGHT-NINE-TEN",
        ):
            self.assertIsNotNone(reqtrace.TRACE_RE.search(f"{MARKER} {handle}"))
        self.assertIsNotNone(
            reqtrace.LEGACY_TRACE_RE.search(f"{MARKER} AUTH-SESSION-ROTATION/001/@file")
        )

    def test_generate_is_idempotent(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            first = (root / "docs" / "trace-ledger.jsonl").read_bytes()
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            self.assertEqual((root / "docs" / "trace-ledger.jsonl").read_bytes(), first)

    def test_multiple_markers_on_one_line_are_rejected(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012 {MARKER} SEC-CONTROL-7\n")
            scan = reqtrace.scan_repository(root, self.config(root))
            self.assertEqual(scan.occurrences, [])
            self.assertTrue(any(error.startswith("E_MULTIPLE_MARKERS_ON_LINE") for error in scan.errors))

    def test_collision_escalates_from_four_to_five_characters(self) -> None:
        original_short_id = reqtrace.short_id
        try:
            reqtrace.short_id = lambda path, line, length=4: (
                "0000" if length == 4 else original_short_id(path, line, length)
            )
            records, errors = reqtrace.records_from_occurrences(
                [
                    reqtrace.Occurrence("ADR-0012", "src/one.py", 1, "implementation"),
                    reqtrace.Occurrence("ADR-0012", "src/two.py", 1, "implementation"),
                ],
                4,
            )
        finally:
            reqtrace.short_id = original_short_id
        self.assertEqual(errors, [])
        self.assertTrue(all(len(record.id) == 5 for record in records))

    def test_collision_escalates_upward_from_configured_length(self) -> None:
        original_short_id = reqtrace.short_id
        tried_lengths: list[int] = []
        try:
            def colliding_id(_: str, __: int, length: int = 4) -> str:
                tried_lengths.append(length)
                return "0" * length

            reqtrace.short_id = colliding_id
            records, errors = reqtrace.records_from_occurrences(
                [
                    reqtrace.Occurrence("ADR-0012", "src/one.py", 1, "implementation"),
                    reqtrace.Occurrence("ADR-0012", "src/two.py", 1, "implementation"),
                ],
                10,
            )
        finally:
            reqtrace.short_id = original_short_id
        self.assertEqual(records, [])
        self.assertEqual(sorted(set(tried_lengths)), list(range(10, 17)))
        self.assertEqual(errors, ["E_ID_COLLISION unable to disambiguate occurrence IDs at 16 hex characters"])

    def test_check_omits_stale_error_when_scan_has_collision(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "feature.py",
                f"# {MARKER} ADR-0012\n# {MARKER} ADR-0012\n",
            )
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "ADR-0012",
                        "id": "abcd",
                        "path": "src/feature.py",
                        "line": 1,
                        "kind": "implementation",
                    }
                )
                + "\n",
            )
            original_short_id = reqtrace.short_id
            try:
                reqtrace.short_id = lambda _path, _line, length=4: "0" * length
                output = io.StringIO()
                with contextlib.redirect_stderr(output):
                    self.assertEqual(
                        reqtrace.command_check(
                            root, self.config(root), SimpleNamespace(strict=None)
                        ),
                        1,
                    )
            finally:
                reqtrace.short_id = original_short_id
            self.assertIn("E_ID_COLLISION", output.getvalue())
            self.assertNotIn("E_STALE_LEDGER", output.getvalue())

    def test_report_buckets_zero_and_partial_coverage(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                "\n".join(
                    [
                        json.dumps({"handle": "ADR-0012", "type": "adr"}),
                        json.dumps({"handle": "SEC-CONTROL-7", "type": "security-control"}),
                    ]
                )
                + "\n",
            )
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "ADR-0012",
                        "id": "abcd",
                        "path": "tests/decision_test.py",
                        "line": 1,
                        "kind": "verification",
                    }
                )
                + "\n",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_report(root, self.config(root), SimpleNamespace(format="json")), 0
                )
            report = json.loads(output.getvalue())
            self.assertEqual([entry["handle"] for entry in report["handles"]["partial"]], ["ADR-0012"])
            self.assertEqual([entry["handle"] for entry in report["handles"]["zero"]], ["SEC-CONTROL-7"])
            self.assertEqual(report["handles"]["partial"][0]["kinds"], ["verification"])
            self.assertFalse(report["handles"]["partial"][0]["implementation"])
            self.assertTrue(report["handles"]["partial"][0]["verification"])

    def test_strict_ledger_allows_incomplete_registry_but_full_rejects_it(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=True)), 0
            )
            self.assertEqual(
                reqtrace.command_check(root, config, SimpleNamespace(strict="ledger")), 0
            )
            self.assertEqual(
                reqtrace.command_check(root, config, SimpleNamespace(strict="full")), 1
            )

    def test_migration_warns_without_dropping_unmatched_legacy_ledger_entry(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "feature.py", f"# {MARKER} AUTH-SESSION-ROTATION/001/@file\n"
            )
            self.write(
                root / "docs" / "requirements.md",
                "\n".join(
                    [
                        "- AUTH-SESSION-ROTATION/001/src/feature.py",
                        "- SEC-CONTROL-7/002/src/missing.py",
                    ]
                )
                + "\n",
            )
            self.assertEqual(
                reqtrace.command_migrate(root, self.config(root), SimpleNamespace(dry_run=False)), 1
            )
            self.assertIn(
                f"{MARKER} AUTH-SESSION-ROTATION", (root / "src" / "feature.py").read_text()
            )
            self.assertNotIn("/001/@file", (root / "src" / "feature.py").read_text())

    def test_migrated_fixture_passes_strict_check(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "feature.py", f"# {MARKER} AUTH-SESSION-ROTATION/001/@file\n"
            )
            self.write(
                root / "docs" / "requirements.md",
                "# AUTH-SESSION-ROTATION\n\n"
                "- AUTH-SESSION-ROTATION/001/src/feature.py\n",
            )
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps(
                    {
                        "handle": "AUTH-SESSION-ROTATION",
                        "type": "requirement",
                        "source": "docs/requirements.md",
                    }
                )
                + "\n",
            )
            config = self.config(root)
            self.assertEqual(reqtrace.command_migrate(root, config, SimpleNamespace(dry_run=False)), 0)
            self.write(
                root / "docs" / "requirements.md",
                "# AUTH-SESSION-ROTATION\n\n"
                "<!-- reqtrace:ledger:start handle=AUTH-SESSION-ROTATION -->\n"
                "<!-- reqtrace:ledger:end -->\n",
            )
            self.assertEqual(reqtrace.command_render(root, config, SimpleNamespace()), 0)
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict="ledger")), 0)

    def test_legacy_form_warns_then_rejects_when_configured(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-TEST/001/@file\n")
            config = self.config(root)
            config["legacy_form"] = "warn"
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=None)), 0)
            config["legacy_form"] = "reject"
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=None)), 1)

    def test_default_legacy_form_is_reject(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-TEST/001/@file\n")
            config = self.config(root)
            self.assertEqual(config["legacy_form"], "reject")
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=None)), 1)

    def test_config_rejects_invalid_json(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", "{not json}\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                self.config(root)

    def test_config_rejects_unknown_fields(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"not_a_setting": True}) + "\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                self.config(root)

    def test_config_rejects_invalid_strict_level(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"strict_level": "everything"}) + "\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                self.config(root)

    def test_config_rejects_boolean_id_length(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"id_length": True}) + "\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                self.config(root)

    def test_config_uses_defaults_when_optional_fields_are_missing(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"marker": "@reqtrace"}) + "\n")
            config = self.config(root)
            self.assertEqual(config["strict_level"], "ledger")
            self.assertEqual(config["ledger_path"], "docs/trace-ledger.jsonl")

    def test_ledger_rejects_truncated_json_line(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            ledger = root / "docs" / "trace-ledger.jsonl"
            self.write(ledger, '{"handle": "ADR-0012"\n')
            _, errors = reqtrace.read_ledger(ledger)
            self.assertTrue(any(error.startswith("E_LEDGER_PARSE") for error in errors))

    def test_ledger_rejects_missing_required_field(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            ledger = root / "docs" / "trace-ledger.jsonl"
            self.write(
                ledger,
                json.dumps({"handle": "ADR-0012", "id": "abcd", "path": "src/a.py", "line": 1})
                + "\n",
            )
            _, errors = reqtrace.read_ledger(ledger)
            self.assertTrue(any("invalid record schema" in error for error in errors))

    def test_ledger_accepts_future_extra_field(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            ledger = root / "docs" / "trace-ledger.jsonl"
            self.write(
                ledger,
                json.dumps(
                    {
                        "handle": "ADR-0012",
                        "id": "abcd",
                        "path": "src/a.py",
                        "line": 1,
                        "kind": "implementation",
                        "extra": True,
                    }
                )
                + "\n",
            )
            records, errors = reqtrace.read_ledger(ledger)
            self.assertEqual(errors, [])
            self.assertEqual(records[0].handle, "ADR-0012")

    def test_check_rejects_ledger_entry_for_deleted_file(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "ADR-0012",
                        "id": "abcd",
                        "path": "src/deleted.py",
                        "line": 1,
                        "kind": "implementation",
                    }
                )
                + "\n",
            )
            self.assertEqual(
                reqtrace.command_check(root, self.config(root), SimpleNamespace(strict="ledger")), 1
            )

    def test_multiple_annotations_for_one_handle_are_recorded(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "feature.py",
                f"# {MARKER} ADR-0012\n\n# {MARKER} ADR-0012\n",
            )
            records, errors = reqtrace.records_from_occurrences(
                reqtrace.scan_repository(root, self.config(root)).occurrences, 4
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 2)
            self.assertNotEqual(records[0].id, records[1].id)

    def test_windows_config_paths_generate_posix_ledger_records(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(
                root / ".reqtrace.json",
                json.dumps(
                    {
                        "ledger_path": "docs\\trace-ledger.jsonl",
                        "registry_path": "docs\\handle-registry.jsonl",
                    }
                )
                + "\n",
            )
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            ledger, errors = reqtrace.read_ledger(root / "docs" / "trace-ledger.jsonl")
            self.assertEqual(errors, [])
            self.assertEqual(ledger[0].path, "src/feature.py")

    def test_unicode_path_is_scanned(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "café.py", f"# {MARKER} ADR-0012\n")
            scan = reqtrace.scan_repository(root, self.config(root))
            self.assertEqual(scan.errors, [])
            self.assertEqual(scan.occurrences[0].path, "src/café.py")

    def test_empty_project_scan_has_no_annotations(self) -> None:
        with self.make_empty_root() as directory:
            root = Path(directory)
            scan = reqtrace.scan_repository(root, self.config(root))
            self.assertEqual(scan.occurrences, [])
            self.assertEqual(scan.errors, [])

    def test_annotation_on_last_line_without_newline_is_scanned(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012")
            scan = reqtrace.scan_repository(root, self.config(root))
            self.assertEqual(len(scan.occurrences), 1)
            self.assertEqual(scan.occurrences[0].line, 1)

    def test_generate_render_check_pipeline_has_deterministic_bytes(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(root / "tests" / "feature_test.py", f"# {MARKER} ADR-0012\n")
            self.write(
                root / "docs" / "requirements.md",
                "# ADR-0012\n\n"
                "<!-- reqtrace:ledger:start handle=ADR-0012 -->\n"
                "<!-- reqtrace:ledger:end -->\n",
            )
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "ADR-0012", "type": "adr"}) + "\n",
            )
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            first = (root / "docs" / "trace-ledger.jsonl").read_bytes()
            self.assertEqual(reqtrace.command_render(root, config, SimpleNamespace()), 0)
            self.assertEqual(
                reqtrace.command_check(root, config, SimpleNamespace(strict="ledger")), 0
            )
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            self.assertEqual((root / "docs" / "trace-ledger.jsonl").read_bytes(), first)
            rendered = (root / "docs" / "requirements.md").read_text(encoding="utf-8")
            self.assertIn("ADR-0012/", rendered)
            self.assertIn("/src/feature.py:1", rendered)
            self.assertIn("/tests/feature_test.py:1", rendered)

    def test_init_creates_starter_files_and_prints_quickstart(self) -> None:
        with self.make_empty_root() as directory:
            root = Path(directory)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(reqtrace.command_init(root, SimpleNamespace()), 0)
            config = json.loads((root / ".reqtrace.json").read_text(encoding="utf-8"))
            self.assertEqual(config["strict_level"], "ledger")
            self.assertEqual((root / "docs" / "handle-registry.jsonl").read_bytes(), b"")
            self.assertEqual((root / "docs" / "trace-ledger.jsonl").read_bytes(), b"")
            self.assertEqual(len(output.getvalue().splitlines()), 3)

    def test_init_rolls_back_files_after_later_write_failure(self) -> None:
        with self.make_empty_root() as directory:
            root = Path(directory)
            original_write = reqtrace.atomic_write_text

            def fail_registry(path: Path, content: str) -> None:
                if path.name == "handle-registry.jsonl":
                    raise reqtrace.ReqtraceError("cannot write registry")
                original_write(path, content)

            output = io.StringIO()
            with patch.object(reqtrace, "atomic_write_text", side_effect=fail_registry):
                with contextlib.redirect_stderr(output):
                    self.assertEqual(reqtrace.command_init(root, SimpleNamespace()), 2)
            self.assertIn("cannot write registry", output.getvalue())
            self.assertFalse((root / ".reqtrace.json").exists())
            self.assertFalse((root / "docs" / "handle-registry.jsonl").exists())
            self.assertFalse((root / "docs" / "trace-ledger.jsonl").exists())

    def test_init_detects_common_project_directories(self) -> None:
        with self.make_empty_root() as directory:
            root = Path(directory)
            for name in ("src", "tests", "docs", "lib", "app"):
                (root / name).mkdir()
            self.assertEqual(reqtrace.command_init(root, SimpleNamespace()), 0)
            config = json.loads((root / ".reqtrace.json").read_text(encoding="utf-8"))
            self.assertEqual(
                config["role_map"],
                {
                    "src/**": "implementation",
                    "tests/**": "verification",
                    "docs/**": "documentation",
                    "lib/**": "implementation",
                    "app/**": "implementation",
                },
            )

    def test_init_from_cli_uses_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_directory = Path.cwd()
            try:
                os.chdir(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(reqtrace.main(["init"]), 0)
            finally:
                os.chdir(original_directory)
            self.assertTrue((root / ".reqtrace.json").exists())

    def test_non_init_cli_finds_project_root_from_nested_directory(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", "{}\n")
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            original_directory = Path.cwd()
            try:
                os.chdir(root / "src")
                self.assertEqual(reqtrace.main(["check", "--strict"]), 0)
            finally:
                os.chdir(original_directory)

    def test_report_distinguishes_role_coverage(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                "\n".join(
                    json.dumps({"handle": handle, "type": "requirement"})
                    for handle in ("ADR-0012", "AUTH", "SEC-CONTROL-7", "UNUSED")
                )
                + "\n",
            )
            records = [
                {"handle": "ADR-0012", "id": "a001", "path": "src/a.py", "line": 1, "kind": "implementation"},
                {"handle": "ADR-0012", "id": "a002", "path": "tests/a.py", "line": 1, "kind": "verification"},
                {"handle": "AUTH", "id": "b001", "path": "docs/a.md", "line": 1, "kind": "documentation"},
                {"handle": "SEC-CONTROL-7", "id": "c001", "path": "tests/a.py", "line": 2, "kind": "verification"},
            ]
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                "".join(json.dumps(record) + "\n" for record in records),
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_report(root, self.config(root), SimpleNamespace(format="json")), 0
                )
            report = json.loads(output.getvalue())
            entries = {
                entry["handle"]: entry
                for bucket in report["handles"].values()
                for entry in bucket
            }
            self.assertEqual(entries["ADR-0012"]["status"], "both")
            self.assertEqual(entries["AUTH"]["status"], "documentation-only")
            self.assertEqual(entries["SEC-CONTROL-7"]["status"], "verification")
            self.assertEqual(entries["UNUSED"]["status"], "none")
            self.assertEqual([entry["handle"] for entry in report["handles"]["full"]], ["ADR-0012"])
            self.assertEqual([entry["handle"] for entry in report["handles"]["zero"]], ["AUTH", "UNUSED"])

    def test_report_includes_unregistered_ledger_handles(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "ADR-0012",
                        "id": "abcd",
                        "path": "src/a.py",
                        "line": 1,
                        "kind": "implementation",
                    }
                )
                + "\n",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_report(root, self.config(root), SimpleNamespace(format="json")), 0
                )
            report = json.loads(output.getvalue())
            partial = report["handles"]["partial"]
            self.assertEqual(partial[0]["handle"], "ADR-0012")
            self.assertEqual(partial[0]["type"], "unknown")

    def test_report_github_format_is_markdown_table(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "ADR-0012", "type": "adr"}) + "\n",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_report(root, self.config(root), SimpleNamespace(format="github")), 0
                )
            lines = output.getvalue().splitlines()
            self.assertEqual(
                lines[:2],
                [
                    "| Handle | Implementation | Verification | Documentation | Status |",
                    "| --- | --- | --- | --- | --- |",
                ],
            )
            self.assertIn("| ADR-0012 | no | no | no | none |", lines)

    def test_scan_json_has_stable_annotation_schema(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, self.config(root), SimpleNamespace(format="json", diff=False)
                    ),
                    0,
                )
            self.assertEqual(
                json.loads(output.getvalue()),
                [
                    {
                        "handle": "ADR-0012",
                        "path": "src/feature.py",
                        "line": 1,
                        "kind": None,
                        "id": None,
                    }
                ],
            )

    def test_scan_diff_lists_annotations_absent_from_ledger(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(root / "docs" / "trace-ledger.jsonl", "")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, self.config(root), SimpleNamespace(format="json", diff=True)
                    ),
                    0,
                )
            self.assertEqual(
                json.loads(output.getvalue()),
                [
                    {
                        "handle": "ADR-0012",
                        "path": "src/feature.py",
                        "line": 1,
                        "kind": None,
                        "id": None,
                    }
                ],
            )

    def test_scan_diff_uses_source_identity_and_reports_no_new_annotations(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            config["id_length"] = 6
            json_output = io.StringIO()
            with contextlib.redirect_stdout(json_output):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, config, SimpleNamespace(format="json", diff=True)
                    ),
                    0,
                )
            self.assertEqual(json.loads(json_output.getvalue()), [])
            text_output = io.StringIO()
            with contextlib.redirect_stdout(text_output):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, config, SimpleNamespace(format="text", diff=True)
                    ),
                    0,
                )
            self.assertIn("No new annotations", text_output.getvalue())
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=None)), 1)
            self.assertIn("E_STALE_LEDGER", errors.getvalue())
            self.assertIn("id_length change", errors.getvalue())

    def test_scan_diff_suppresses_legacy_annotations(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012/001/@file\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, self.config(root), SimpleNamespace(format="text", diff=True)
                    ),
                    0,
                )
            self.assertIn("No new annotations", output.getvalue())
            self.assertNotIn("legacy src/feature.py", output.getvalue())

    def test_scan_is_diagnostic_when_source_contains_scan_errors(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "feature.py",
                f"# {MARKER} ADR-0012 {MARKER} SEC-CONTROL-7\n",
            )
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(
                    reqtrace.command_scan(
                        root, self.config(root), SimpleNamespace(format="json", diff=False)
                    ),
                    0,
                )
            self.assertIn("E_MULTIPLE_MARKERS_ON_LINE", errors.getvalue())

    def test_markdown_scan_respects_configured_role_map(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "documentation" / "guide.md", f"{MARKER} ADR-0012\n")
            config = self.config(root)
            config["role_map"] = {"documentation/**": "documentation"}
            scan = reqtrace.scan_repository(root, config)
            self.assertEqual(scan.errors, [])
            self.assertEqual(
                scan.occurrences,
                [reqtrace.Occurrence("ADR-0012", "documentation/guide.md", 1, "documentation")],
            )

    def test_check_uses_configured_full_policy_without_flag(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(root / ".reqtrace.json", json.dumps({"strict_level": "full"}) + "\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=None)), 1)

    def test_bare_strict_uses_configured_full_policy(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            self.write(root / ".reqtrace.json", json.dumps({"strict_level": "full"}) + "\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            args = reqtrace.build_parser().parse_args(["check", "--strict"])
            self.assertEqual(args.strict, "ledger")
            self.assertEqual(reqtrace.command_check(root, config, args), 0)

    def test_migrate_prints_deprecation_notice(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012/001/@file\n")
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                self.assertEqual(
                    reqtrace.command_migrate(root, self.config(root), SimpleNamespace(dry_run=True)), 0
                )
            self.assertIn("deprecated", output.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
