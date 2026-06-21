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
MODULE_SPEC = importlib.util.spec_from_file_location("reqtrace_hierarchy", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reqtrace = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = reqtrace
MODULE_SPEC.loader.exec_module(reqtrace)
MARKER = "@req" + "trace"
HIERARCHY = ["BRD", "ARD", "DRD", "TRD"]


class HierarchyTests(unittest.TestCase):
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

    def config(self, root: Path, hierarchy: list[str] | None = HIERARCHY) -> dict[str, object]:
        config = reqtrace.load_config(root)
        if hierarchy is not None:
            config["doc_hierarchy"] = hierarchy
        return config

    def check(self, root: Path, config: dict[str, object]) -> tuple[int, str]:
        self.assertEqual(
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = reqtrace.command_check(root, config, SimpleNamespace(strict=None))
        return result, stderr.getvalue()

    def test_doc_hierarchy_empty_list_is_accepted(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"doc_hierarchy": []}) + "\n")
            self.assertEqual(reqtrace.load_config(root)["doc_hierarchy"], [])

    def test_doc_hierarchy_rejects_non_list(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"doc_hierarchy": "TRD"}) + "\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                reqtrace.load_config(root)

    def test_doc_hierarchy_rejects_non_string_elements(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / ".reqtrace.json", json.dumps({"doc_hierarchy": [1, 2]}) + "\n")
            with self.assertRaises(reqtrace.ReqtraceError):
                reqtrace.load_config(root)

    def test_handle_prefix(self) -> None:
        self.assertEqual(reqtrace.handle_prefix("TRD-7"), "TRD")
        self.assertEqual(reqtrace.handle_prefix("BRD-G3"), "BRD")
        self.assertEqual(reqtrace.handle_prefix("SEC-CONTROL-7"), "SEC")
        self.assertEqual(reqtrace.handle_prefix("V2M-ARD-1"), "V2M")

    def test_implementation_offleaf_handle_fails(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} BRD-1\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 1)
            self.assertIn("E_OFFLEAF_HANDLE BRD-1", stderr)

    def test_implementation_leaf_handle_passes(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} TRD-7\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 0)
            self.assertNotIn("E_OFFLEAF_HANDLE", stderr)

    def test_verification_offleaf_handle_passes(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "tests" / "feature_test.py", f"# {MARKER} BRD-1\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 0)
            self.assertNotIn("E_OFFLEAF_HANDLE", stderr)

    def test_empty_hierarchy_disables_enforcement(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} BRD-1\n")
            result, stderr = self.check(root, self.config(root, []))
            self.assertEqual(result, 0)
            self.assertNotIn("E_OFFLEAF_HANDLE", stderr)

    def test_v2m_handle_fails_as_offleaf(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} V2M-ARD-1\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 1)
            self.assertIn("E_OFFLEAF_HANDLE V2M-ARD-1", stderr)

    def test_consecutive_implementation_handles_fail(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} TRD-1\n# {MARKER} TRD-2\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 1)
            self.assertIn("E_MULTI_HANDLE_EVIDENCE", stderr)

    def test_gapped_implementation_handles_pass(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} TRD-1\n\n# {MARKER} TRD-2\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 0)
            self.assertNotIn("E_MULTI_HANDLE_EVIDENCE", stderr)

    def test_consecutive_same_implementation_handle_passes(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "src" / "feature.py", f"# {MARKER} TRD-1\n# {MARKER} TRD-1\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 0)
            self.assertNotIn("E_MULTI_HANDLE_EVIDENCE", stderr)

    def test_consecutive_verification_handles_pass(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "tests" / "feature_test.py", f"# {MARKER} TRD-1\n# {MARKER} TRD-2\n")
            result, stderr = self.check(root, self.config(root))
            self.assertEqual(result, 0)
            self.assertNotIn("E_MULTI_HANDLE_EVIDENCE", stderr)


if __name__ == "__main__":
    unittest.main()
