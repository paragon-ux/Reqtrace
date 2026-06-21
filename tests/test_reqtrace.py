from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


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

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def config(self, root: Path) -> dict[str, object]:
        return reqtrace.load_config(root)

    def test_grammar_accepts_alphanumeric_handle_segments(self) -> None:
        for handle in ("ADR-0012", "SEC-CONTROL-7", "TRD-12"):
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

    def test_collision_escalates_from_four_to_six_characters(self) -> None:
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
        self.assertTrue(all(len(record.id) == 6 for record in records))

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
            self.assertEqual([entry["handle"] for entry in report["partial"]], ["ADR-0012"])
            self.assertEqual([entry["handle"] for entry in report["zero"]], ["SEC-CONTROL-7"])

    def test_generate_register_unknown_does_not_satisfy_strict_check(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-0012\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=True)), 0
            )
            self.assertEqual(
                reqtrace.command_check(root, config, SimpleNamespace(strict=True)), 1
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
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=True)), 0)

    def test_legacy_form_warns_then_rejects_when_configured(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} ADR-TEST/001/@file\n")
            config = self.config(root)
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=False)), 0)
            config["legacy_form"] = "reject"
            self.assertEqual(reqtrace.command_check(root, config, SimpleNamespace(strict=False)), 1)


if __name__ == "__main__":
    unittest.main()
