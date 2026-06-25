"""v2.1.5 machine-contract and registration tests."""

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
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "reqtrace.py"
MODULE_SPEC = importlib.util.spec_from_file_location("reqtrace_stabilize", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reqtrace = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = reqtrace
MODULE_SPEC.loader.exec_module(reqtrace)
MARKER = "@req" + "trace"


class StabilizeTests(unittest.TestCase):
    def make_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=fixture_root)
        root = Path(temporary.name)
        for directory in ("docs", "src", "tests"):
            (root / directory).mkdir()
        return temporary

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def config(self, root: Path) -> dict[str, object]:
        return reqtrace.load_config(root)

    def scan_json(self, root: Path, config: dict[str, object]) -> list[dict[str, object]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                reqtrace.command_scan(root, config, SimpleNamespace(format="json", diff=False)), 0
            )
        return json.loads(output.getvalue())

    def report_json(self, root: Path, config: dict[str, object]) -> dict[str, object]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                reqtrace.command_report(root, config, SimpleNamespace(format="json")), 0
            )
        return json.loads(output.getvalue())

    def test_scan_json_uses_matching_ledger_kind_and_id(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            ledger, errors = reqtrace.read_ledger(root / "docs" / "trace-ledger.jsonl")
            self.assertEqual(errors, [])
            records = self.scan_json(root, config)
            self.assertEqual(list(records[0]), ["handle", "path", "line", "kind", "id"])
            self.assertEqual(records[0]["kind"], ledger[0].kind)
            self.assertEqual(records[0]["id"], ledger[0].id)

    def test_scan_json_without_ledger_uses_null_kind_and_id(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            records = self.scan_json(root, self.config(root))
            self.assertEqual(records[0]["kind"], None)
            self.assertEqual(records[0]["id"], None)

    def test_default_scan_text_output_is_unchanged(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_scan(root, self.config(root), SimpleNamespace(format="text", diff=False)),
                    0,
                )
            self.assertEqual(
                output.getvalue(),
                f"AUTH-LOGIN\n  src/auth.py:1 id={reqtrace.short_id('src/auth.py', 1)} kind=implementation\n",
            )

    def test_report_json_has_versioned_envelope_and_derived_summary(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                "\n".join(
                    json.dumps({"handle": handle, "type": "requirement", "source": "docs/reference.md"})
                    for handle in ("AUTH-LOGIN", "AUTH-LOGOUT")
                )
                + "\n",
            )
            self.write(root / "docs" / "reference.md", "# Reference\n")
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                "\n".join(
                    json.dumps(record)
                    for record in (
                        {
                            "handle": "AUTH-LOGIN",
                            "id": "a001",
                            "path": "src/auth.py",
                            "line": 1,
                            "kind": "implementation",
                        },
                        {
                            "handle": "AUTH-LOGIN",
                            "id": "a002",
                            "path": "tests/test_auth.py",
                            "line": 1,
                            "kind": "verification",
                        },
                    )
                )
                + "\n",
            )
            report = self.report_json(root, self.config(root))
            self.assertEqual(list(report), ["schemaVersion", "handles", "summary"])
            self.assertEqual(report["schemaVersion"], "2.1")
            handles = report["handles"]
            summary = report["summary"]
            self.assertEqual(summary["total"], sum(len(handles[name]) for name in ("full", "partial", "zero")))
            self.assertEqual(summary["full"], len(handles["full"]))
            self.assertEqual(
                set(handles["full"][0]),
                {
                    "handle", "type", "source", "occurrences", "kinds", "kind_counts",
                    "implementation", "verification", "documentation", "status",
                },
            )

    def test_report_github_output_remains_a_markdown_table(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "AUTH-LOGIN", "type": "requirement"}) + "\n",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_report(root, self.config(root), SimpleNamespace(format="github")), 0
                )
            self.assertEqual(
                output.getvalue().splitlines()[:2],
                [
                    "| Handle | Implementation | Verification | Documentation | Status |",
                    "| --- | --- | --- | --- | --- |",
                ],
            )

    def test_check_success_reports_text_and_json_status_with_report_counts(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "AUTH-LOGIN", "type": "requirement"}) + "\n",
            )
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            text = io.StringIO()
            with contextlib.redirect_stdout(text):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="ledger", format="text")), 0
                )
            self.assertTrue(text.getvalue().startswith("REQTRACE OK registered=1"))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="ledger", format="json")), 0
                )
            status = json.loads(output.getvalue())
            report = self.report_json(root, config)
            self.assertEqual(status["status"], "ok")
            self.assertEqual(status["full"], report["summary"]["full"])
            self.assertEqual(status["partial"], report["summary"]["partial"])
            self.assertEqual(status["zero"], report["summary"]["zero"])

    def test_check_failure_reports_text_and_json_status(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            config = self.config(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(sys, "argv", ["reqtrace"]),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="ledger", format="text")), 1
                )
            self.assertIn("E_STALE_LEDGER", stderr.getvalue())
            self.assertIn("REQTRACE FAIL checks=1", stderr.getvalue())
            self.assertIn("fix: python reqtrace generate && python reqtrace check --strict", stderr.getvalue())
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="ledger", format="json")), 1
                )
            self.assertEqual(json.loads(stdout.getvalue()), {"status": "fail", "errors": ["E_STALE_LEDGER"]})
            self.assertIn("E_STALE_LEDGER", stderr.getvalue())

    def test_register_appends_default_type_and_prints_marker(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            config = self.config(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    reqtrace.command_register(
                        root, config, SimpleNamespace(handle="AUTH-LOGIN", type=None, source=None)
                    ),
                    0,
                )
            entry = json.loads((root / "docs" / "handle-registry.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(entry, {"handle": "AUTH-LOGIN", "type": "unknown"})
            self.assertIn("REQTRACE REGISTERED AUTH-LOGIN", output.getvalue())
            self.assertIn(f"marker:   {MARKER} AUTH-LOGIN", output.getvalue())
            self.assertEqual(
                reqtrace.command_check(root, config, SimpleNamespace(strict="ledger", format="text")), 0
            )

    def test_register_default_unknown_type_remains_incomplete_for_strict_full(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_register(
                    root, config, SimpleNamespace(handle="AUTH-LOGIN", type=None, source=None)
                ),
                0,
            )
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="full", format="text")), 1
                )
            self.assertIn("E_HANDLE_NOT_REGISTERED AUTH-LOGIN", stderr.getvalue())

    def test_register_rejects_duplicates_invalid_handles_and_missing_sources(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            config = self.config(root)
            args = SimpleNamespace(handle="AUTH-LOGIN", type="requirement", source=None)
            self.assertEqual(reqtrace.command_register(root, config, args), 0)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(reqtrace.command_register(root, config, args), 1)
            self.assertIn("E_DUPLICATE_HANDLE: AUTH-LOGIN is already registered", stderr.getvalue())
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_register(
                        root, config, SimpleNamespace(handle="AUTH LOGIN", type=None, source=None)
                    ),
                    1,
                )
            self.assertIn("E_INVALID_HANDLE", stderr.getvalue())
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_register(
                        root,
                        config,
                        SimpleNamespace(handle="AUTH-LOGOUT", type=None, source="docs/missing.md"),
                    ),
                    1,
                )
            self.assertIn("E_REGISTRY_SOURCE_MISSING: docs/missing.md not found", stderr.getvalue())

    def test_register_rejects_handles_outside_trace_grammar(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            config = self.config(root)
            for handle in ("auth-login", "AUTH_LOGIN"):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(
                        reqtrace.command_register(
                            root, config, SimpleNamespace(handle=handle, type=None, source=None)
                        ),
                        1,
                    )
                self.assertIn("E_INVALID_HANDLE", stderr.getvalue())

    def test_register_writes_type_and_existing_source_when_requested(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "reference.md", "# Reference\n")
            self.assertEqual(
                reqtrace.command_register(
                    root,
                    self.config(root),
                    SimpleNamespace(
                        handle="AUTH-LOGIN", type="requirement", source="docs/reference.md"
                    ),
                ),
                0,
            )
            entry = json.loads((root / "docs" / "handle-registry.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(
                entry,
                {"handle": "AUTH-LOGIN", "type": "requirement", "source": "docs/reference.md"},
            )

    def test_registry_preserves_reserved_relationship_fields(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps(
                    {
                        "handle": "SDS-1",
                        "type": "design-spec",
                        "parent": "SRS-1",
                        "links": ["ADR-001"],
                    }
                )
                + "\n",
            )
            entries, errors = reqtrace.read_registry(root / "docs" / "handle-registry.jsonl")
            self.assertEqual(errors, [])
            self.assertEqual(entries[0]["parent"], "SRS-1")
            self.assertEqual(entries[0]["links"], ["ADR-001"])

    def test_strict_full_success_summary_reuses_validated_registry(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            validated = [{"handle": "AUTH-LOGIN", "type": "requirement"}]
            mutated = [*validated, {"handle": "EXTRA-HANDLE", "type": "requirement"}]
            calls: list[Path] = []

            def changing_registry(path: Path) -> tuple[list[dict[str, object]], list[str]]:
                calls.append(path)
                return (validated if len(calls) == 1 else mutated), []

            output = io.StringIO()
            with patch.object(reqtrace, "read_registry", side_effect=changing_registry):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(
                        reqtrace.command_check(
                            root, config, SimpleNamespace(strict="full", format="json")
                        ),
                        0,
                    )
            status = json.loads(output.getvalue())
            self.assertEqual(status["registered"], 1)
            self.assertEqual(len(calls), 1)

    def test_check_reports_stale_ledger_even_when_scan_has_errors(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "src" / "auth.py",
                f"# {MARKER} AUTH-LOGIN {MARKER} AUTH-LOGOUT\n",
            )
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "AUTH-LOGIN",
                        "id": "a001",
                        "path": "src/auth.py",
                        "line": 1,
                        "kind": "implementation",
                    }
                )
                + "\n",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(
                        root, self.config(root), SimpleNamespace(strict="ledger", format="text")
                    ),
                    1,
                )
            self.assertIn("E_MULTIPLE_MARKERS_ON_LINE", stderr.getvalue())
            self.assertIn("E_STALE_LEDGER", stderr.getvalue())

    def test_bare_strict_parser_selects_full_validation(self) -> None:
        args = reqtrace.build_parser().parse_args(["check", "--strict"])
        self.assertEqual(args.strict, "full")

    def test_check_json_reports_registry_parse_error_code(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "handle-registry.jsonl", "{BAD JSON\n")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(
                        root, self.config(root), SimpleNamespace(strict="full", format="json")
                    ),
                    1,
                )
            self.assertEqual(
                json.loads(stdout.getvalue()),
                {"status": "fail", "errors": ["E_REGISTRY_PARSE_ERROR"]},
            )
            self.assertIn("E_REGISTRY_PARSE_ERROR", stderr.getvalue())

    def test_blank_registry_source_fails_strict_full(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps({"handle": "AUTH-LOGIN", "type": "requirement", "source": ""}) + "\n",
            )
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="full", format="text")),
                    1,
                )
            self.assertIn("E_REGISTRY_SOURCE_MISSING AUTH-LOGIN", stderr.getvalue())

    def test_escaped_registry_source_fails_strict_full(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "auth.py", f"# {MARKER} AUTH-LOGIN\n")
            self.write(
                root / "docs" / "handle-registry.jsonl",
                json.dumps(
                    {"handle": "AUTH-LOGIN", "type": "requirement", "source": "../outside.md"}
                )
                + "\n",
            )
            config = self.config(root)
            self.assertEqual(
                reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    reqtrace.command_check(root, config, SimpleNamespace(strict="full", format="text")),
                    1,
                )
            self.assertIn("E_REGISTRY_SOURCE_MISSING AUTH-LOGIN", stderr.getvalue())
            self.assertIn("escapes the repository", stderr.getvalue())

    def test_register_reads_registry_once_before_append(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            registry_path = root / "docs" / "handle-registry.jsonl"
            self.write(
                registry_path,
                json.dumps({"handle": "EXISTING", "type": "requirement"}) + "\n",
            )
            config = self.config(root)
            original_read_text = Path.read_text
            registry_reads = 0

            def counting_read_text(path: Path, *args: object, **kwargs: object) -> str:
                nonlocal registry_reads
                if path == registry_path:
                    registry_reads += 1
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", counting_read_text):
                self.assertEqual(
                    reqtrace.command_register(
                        root, config, SimpleNamespace(handle="AUTH-LOGIN", type=None, source=None)
                    ),
                    0,
                )
            self.assertEqual(registry_reads, 1)

    def test_render_skips_write_when_ledger_block_is_current(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(
                root / "docs" / "trace-ledger.jsonl",
                json.dumps(
                    {
                        "handle": "AUTH-LOGIN",
                        "id": "a001",
                        "path": "src/auth.py",
                        "line": 1,
                        "kind": "implementation",
                    }
                )
                + "\n",
            )
            self.write(
                root / "docs" / "requirements.md",
                "# AUTH-LOGIN\n\n"
                "<!-- reqtrace:ledger:start handle=AUTH-LOGIN -->\n"
                "- AUTH-LOGIN/a001/src/auth.py:1\n"
                "<!-- reqtrace:ledger:end -->\n",
            )
            with patch.object(reqtrace, "atomic_write_text") as write_text:
                self.assertEqual(reqtrace.command_render(root, self.config(root), SimpleNamespace()), 0)
            write_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
