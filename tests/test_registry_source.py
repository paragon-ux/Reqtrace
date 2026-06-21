"""Strict-full registry source validation tests."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "reqtrace.py"
MODULE_SPEC = importlib.util.spec_from_file_location("reqtrace_registry_source", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reqtrace = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = reqtrace
MODULE_SPEC.loader.exec_module(reqtrace)
MARKER = "@req" + "trace"


class RegistrySourceTests(unittest.TestCase):
    def make_root(self) -> tempfile.TemporaryDirectory[str]:
        fixture_root = REPOSITORY_ROOT / ".tmp-test"
        fixture_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=fixture_root)
        root = Path(temporary.name)
        for directory in ("docs", "src"):
            (root / directory).mkdir()
        return temporary

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def check_full(self, root: Path, handle: str) -> tuple[int, str]:
        self.write(root / "src" / "feature.py", f"# {MARKER} {handle}\n")
        config = reqtrace.load_config(root)
        self.assertEqual(
            reqtrace.command_generate(root, config, SimpleNamespace(register_unknown=False)), 0
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = reqtrace.command_check(root, config, SimpleNamespace(strict="full"))
        return result, stderr.getvalue()

    def write_registry(self, root: Path, *entries: dict[str, str]) -> None:
        self.write(
            root / "docs" / "handle-registry.jsonl",
            "".join(json.dumps(entry) + "\n" for entry in entries),
        )

    def test_existing_registry_source_passes_strict_full(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "reference.md", "# Reference\n")
            self.write_registry(
                root,
                {
                    "handle": "TRD-1",
                    "type": "technical-requirement",
                    "source": "docs/reference.md",
                },
            )
            result, stderr = self.check_full(root, "TRD-1")
            self.assertEqual(result, 0, stderr)
            self.assertNotIn("E_REGISTRY_SOURCE_MISSING", stderr)

    def test_missing_registry_source_fails_strict_full(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write_registry(
                root,
                {
                    "handle": "TRD-2",
                    "type": "technical-requirement",
                    "source": "docs/missing.md",
                },
            )
            result, stderr = self.check_full(root, "TRD-2")
            self.assertEqual(result, 1)
            self.assertIn("E_REGISTRY_SOURCE_MISSING TRD-2", stderr)

    def test_registry_entry_without_source_is_exempt(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write_registry(root, {"handle": "TRD-3", "type": "technical-requirement"})
            result, stderr = self.check_full(root, "TRD-3")
            self.assertEqual(result, 0, stderr)
            self.assertNotIn("E_REGISTRY_SOURCE_MISSING", stderr)

    def test_only_missing_source_is_reported_from_multiple_entries(self) -> None:
        with self.make_root() as directory:
            root = Path(directory)
            self.write(root / "docs" / "reference.md", "# Reference\n")
            self.write_registry(
                root,
                {
                    "handle": "TRD-4",
                    "type": "technical-requirement",
                    "source": "docs/reference.md",
                },
                {
                    "handle": "TRD-5",
                    "type": "technical-requirement",
                    "source": "docs/missing.md",
                },
            )
            result, stderr = self.check_full(root, "TRD-4")
            self.assertEqual(result, 1)
            self.assertIn("E_REGISTRY_SOURCE_MISSING TRD-5", stderr)
            self.assertNotIn("E_REGISTRY_SOURCE_MISSING TRD-4", stderr)


if __name__ == "__main__":
    unittest.main()
