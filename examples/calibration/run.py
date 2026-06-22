#!/usr/bin/env python3
"""
Reqtrace v2.1 calibration runner.

Usage:
    python examples/calibration/run.py

Runs every calibration scenario and reports PASS/FAIL. Exit code is the
number of failures (0 = all pass).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_ROOT = Path(__file__).resolve().parent
CLI_PATH = REPOSITORY_ROOT / "scripts" / "reqtrace.py"
ScenarioCheck = Callable[[Path], None]


def command(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def require_exit(result: subprocess.CompletedProcess[str], expected: int) -> None:
    if result.returncode != expected:
        raise AssertionError(
            f"{' '.join(str(part) for part in result.args)} exited {result.returncode}; "
            f"expected {expected}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def require_contains(text: str, expected: str, description: str) -> None:
    if expected not in text:
        raise AssertionError(f"{description}: expected {expected!r}\noutput:\n{text}")


def report(root: Path) -> dict[str, object]:
    result = command(root, "report", "--format", "json")
    require_exit(result, 0)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"report did not return JSON:\n{result.stdout}") from error


def full_coverage(root: Path) -> None:
    require_exit(command(root, "generate"), 0)
    require_exit(command(root, "check", "--strict"), 0)
    payload = report(root)
    full_handles = {entry["handle"] for entry in payload["handles"]["full"]}
    if "TRD-1" not in full_handles:
        raise AssertionError(f"TRD-1 missing from full coverage: {payload}")


def partial_implementation_only(root: Path) -> None:
    require_exit(command(root, "generate"), 0)
    require_exit(command(root, "check", "--strict"), 0)
    payload = report(root)
    partial_handles = {entry["handle"] for entry in payload["handles"]["partial"]}
    if "TRD-2" not in partial_handles or payload["handles"]["full"]:
        raise AssertionError(f"expected TRD-2 partial and no full coverage: {payload}")


def strict_full_vs_ledger(root: Path) -> None:
    require_exit(command(root, "generate"), 0)
    require_exit(command(root, "check", "--strict=ledger"), 0)
    result = command(root, "check", "--strict=full")
    require_exit(result, 1)
    require_contains(result.stderr, "E_HANDLE_NOT_REGISTERED", "strict=full")


def doc_hierarchy_violation(root: Path) -> None:
    require_exit(command(root, "generate"), 0)
    result = command(root, "check")
    require_exit(result, 1)
    require_contains(result.stderr, "E_OFFLEAF_HANDLE", "hierarchy validation")
    require_contains(result.stderr, "expected leaf: TRD", "hierarchy validation")


def multi_handle_evidence(root: Path) -> None:
    require_exit(command(root, "generate"), 0)
    result = command(root, "check")
    require_exit(result, 1)
    require_contains(result.stderr, "E_MULTI_HANDLE_EVIDENCE", "evidence validation")


def scan_diff(root: Path) -> None:
    result = command(root, "scan", "--diff", "--format", "json")
    require_exit(result, 0)
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"scan --diff did not return JSON:\n{result.stdout}") from error
    if records != [
        {"handle": "TRD-7", "path": "src/widget.py", "line": 4, "kind": None, "id": None}
    ]:
        raise AssertionError(f"scan --diff returned unexpected records: {records}")


def legacy_migration(root: Path) -> None:
    require_exit(command(root, "migrate"), 0)
    content = (root / "src" / "widget.py").read_text(encoding="utf-8")
    require_contains(content, "@reqtrace AUTH-SESSION-ROTATION", "migration output")
    if "/001/@file" in content:
        raise AssertionError(f"migration retained the V1 suffix:\n{content}")
    require_exit(command(root, "check", "--strict"), 0)


SCENARIOS: tuple[tuple[str, ScenarioCheck], ...] = (
    ("01-full-coverage", full_coverage),
    ("02-partial-impl-only", partial_implementation_only),
    ("03-strict-full-vs-ledger", strict_full_vs_ledger),
    ("04-doc-hierarchy-violation", doc_hierarchy_violation),
    ("05-multi-handle-evidence", multi_handle_evidence),
    ("06-scan-diff", scan_diff),
    ("07-legacy-migration", legacy_migration),
)


def run_scenario(name: str, verify: ScenarioCheck) -> str | None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / name
        shutil.copytree(SCENARIOS_ROOT / name, root)
        try:
            verify(root)
        except AssertionError as error:
            return str(error)
    return None


def main() -> int:
    print("Reqtrace v2.1 calibration")
    print("=========================")
    failures: list[tuple[str, str]] = []
    for name, verify in SCENARIOS:
        failure = run_scenario(name, verify)
        if failure is None:
            print(f"{name:<30} PASS")
        else:
            print(f"{name:<30} FAIL")
            print(f"  {failure}")
            failures.append((name, failure))
    print()
    print(f"{len(SCENARIOS)} scenarios: {len(SCENARIOS) - len(failures)} passed, {len(failures)} failed")
    return len(failures)


if __name__ == "__main__":
    sys.exit(main())
