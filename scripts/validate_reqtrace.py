#!/usr/bin/env python3
"""Expand Reqtrace comments and compare them with the documentation ledger."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path


EXCLUDED_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".venv"}
TRACE_RE = re.compile(r"@reqtrace\s+([A-Z]+(?:-[A-Z]+)*)/([0-9]{3})/@file\b")
LEDGER_RE = re.compile(r"^\s*-\s+([A-Z]+(?:-[A-Z]+)*)/([0-9]{3})/(\S+)\s*$")


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def scan_code_traces(root: Path) -> dict[str, set[str]]:
    traces: dict[str, set[str]] = defaultdict(set)

    for path in sorted(root.rglob("*")):
        if not path.is_file() or is_excluded(path):
            continue

        relative_path = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".md":
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line in lines:
            for match in TRACE_RE.finditer(line):
                requirement, ordinal = match.groups()
                traces[requirement].add(f"{requirement}/{ordinal}/{relative_path}")

    return traces


def read_ledger(root: Path) -> dict[str, set[str]]:
    ledger_path = root / "docs" / "requirements.md"
    if not ledger_path.exists():
        print("warning: docs/requirements.md is missing")
        return {}

    ledger: dict[str, set[str]] = defaultdict(set)
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        match = LEDGER_RE.match(line)
        if match:
            requirement, ordinal, relative_path = match.groups()
            ledger[requirement].add(f"{requirement}/{ordinal}/{relative_path}")

    return ledger


def print_grouped_traces(traces: dict[str, set[str]]) -> None:
    if not traces:
        print("No Reqtrace comments found.")
        return

    for requirement in sorted(traces):
        print(requirement)
        for trace in sorted(traces[requirement]):
            print(f"  {trace}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    code_traces = scan_code_traces(root)
    ledger_traces = read_ledger(root)

    print_grouped_traces(code_traces)

    warnings: list[str] = []
    all_requirements = sorted(set(code_traces) | set(ledger_traces))
    for requirement in all_requirements:
        missing_from_ledger = sorted(code_traces[requirement] - ledger_traces[requirement])
        missing_from_code = sorted(ledger_traces[requirement] - code_traces[requirement])

        for trace in missing_from_ledger:
            warnings.append(f"expanded trace missing from ledger: {trace}")
        for trace in missing_from_code:
            warnings.append(f"ledger entry has no matching code comment: {trace}")

    if warnings:
        print()
        for warning in warnings:
            print(f"warning: {warning}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
