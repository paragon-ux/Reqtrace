#!/usr/bin/env python3
"""Generate, validate, and report grep-native Reqtrace evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Iterable

# @reqtrace TRD-1
DEFAULT_CONFIG: dict[str, Any] = {
    "marker": "@reqtrace",
    "id_length": 4,
    "legacy_form": "reject",
    "strict_level": "ledger",
    "doc_hierarchy": [],
    "excluded_dirs": [".git", "node_modules", "dist", "build", "coverage", ".venv", "site"],
    "ledger_path": "docs/trace-ledger.jsonl",
    "registry_path": "docs/handle-registry.jsonl",
    "role_map": {
        "src/**": "implementation",
        "lib/**": "implementation",
        "app/**": "implementation",
        "tests/**": "verification",
        "spec/**": "verification",
        "docs/**": "documentation",
        "migrations/**": "migration",
        "infra/**": "operational",
        "deploy/**": "operational",
    },
}
CONFIG_FIELDS = frozenset(DEFAULT_CONFIG)
STARTER_ROLE_MAP = {
    "src/**": "implementation",
    "tests/**": "verification",
    "docs/**": "documentation",
    "lib/**": "implementation",
    "app/**": "implementation",
}
MAX_ID_LENGTH = 16

HANDLE_PATTERN = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*"
HANDLE_RE = re.compile(rf"^{HANDLE_PATTERN}$")
TRACE_RE = re.compile(rf"@reqtrace\s+({HANDLE_PATTERN})\b")
LEGACY_TRACE_RE = re.compile(rf"@reqtrace\s+({HANDLE_PATTERN})/([0-9]{{3}})/@file\b")
LEGACY_LEDGER_RE = re.compile(rf"^\s*-\s+({HANDLE_PATTERN})/([0-9]{{3}})/(\S+)\s*$")
START_BLOCK_RE = re.compile(rf"^\s*<!--\s*reqtrace:ledger:start\s+handle=({HANDLE_PATTERN})\s*-->\s*$")
END_BLOCK_RE = re.compile(r"^\s*<!--\s*reqtrace:ledger:end\s*-->\s*$")

@dataclass(frozen=True)
class Occurrence:
    handle: str
    path: str
    line: int
    kind: str

@dataclass(frozen=True)
class LegacyOccurrence:
    handle: str
    ordinal: str
    path: str
    line: int

@dataclass(frozen=True)
class LedgerRecord:
    handle: str
    id: str
    path: str
    line: int
    kind: str

    def as_json(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "id": self.id,
            "path": self.path,
            "line": self.line,
            "kind": self.kind,
        }

    def identity(self) -> tuple[str, str, str, int, str]:
        return (self.handle, self.id, self.path, self.line, self.kind)

    def source_identity(self) -> tuple[str, str, int]:
        return (self.handle, self.path, self.line)

@dataclass
class ScanResult:
    occurrences: list[Occurrence]
    legacy_occurrences: list[LegacyOccurrence]
    errors: list[str]

class ReqtraceError(Exception):
    """A configuration or file-system failure that maps to exit code 2."""

# @reqtrace TRD-2
def load_config(root: Path) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_path = root / ".reqtrace.json"
    if config_path.exists():
        try:
            supplied = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReqtraceError(f"cannot read .reqtrace.json: {error}") from error
        if not isinstance(supplied, dict):
            raise ReqtraceError(".reqtrace.json must contain a JSON object")
        unknown_fields = sorted(set(supplied) - CONFIG_FIELDS)
        if unknown_fields:
            raise ReqtraceError(
                ".reqtrace.json contains unknown field(s): " + ", ".join(unknown_fields)
            )
        config.update(supplied)

    if not isinstance(config["marker"], str) or not config["marker"].strip():
        raise ReqtraceError(".reqtrace.json marker must be a non-empty string")
    if (
        isinstance(config["id_length"], bool)
        or not isinstance(config["id_length"], int)
        or config["id_length"] < 1
    ):
        raise ReqtraceError(".reqtrace.json id_length must be a positive integer")
    if config["legacy_form"] not in {"warn", "reject"}:
        raise ReqtraceError(".reqtrace.json legacy_form must be 'warn' or 'reject'")
    if config["strict_level"] not in {"ledger", "full"}:
        raise ReqtraceError(".reqtrace.json strict_level must be 'ledger' or 'full'")
    if not isinstance(config["doc_hierarchy"], list) or not all(
        isinstance(prefix, str) for prefix in config["doc_hierarchy"]
    ):
        raise ReqtraceError(".reqtrace.json doc_hierarchy must be a list of strings")
    if not isinstance(config["excluded_dirs"], list) or not all(
        isinstance(item, str) and item for item in config["excluded_dirs"]
    ):
        raise ReqtraceError(".reqtrace.json excluded_dirs must be a list of directory names")
    if not isinstance(config["role_map"], dict) or not all(
        isinstance(pattern, str)
        and pattern
        and isinstance(kind, str)
        and kind
        for pattern, kind in config["role_map"].items()
    ):
        raise ReqtraceError(".reqtrace.json role_map must map non-empty patterns to roles")
    for key in ("ledger_path", "registry_path"):
        if not isinstance(config[key], str) or not config[key]:
            raise ReqtraceError(f".reqtrace.json {key} must be a non-empty string")
        project_path(root, config[key])
    return config

def starter_config(root: Path) -> dict[str, Any]:
    role_map = {
        pattern: kind
        for pattern, kind in STARTER_ROLE_MAP.items()
        if (root / (pattern[:-3] if pattern.endswith("/**") else pattern)).is_dir()
    }
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["role_map"] = role_map
    return config

def project_path(root: Path, configured_path: str) -> Path:
    candidate = (root / configured_path.replace("\\", "/")).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ReqtraceError(f"configured path escapes the repository: {configured_path}") from error
    return candidate

def find_project_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".reqtrace.json").exists():
            return candidate
    raise ReqtraceError(
        "no .reqtrace.json found in this directory or any parent; run 'reqtrace init' to set up a new project"
    )

def compile_patterns(marker: str) -> tuple[re.Pattern[str], re.Pattern[str]]:
    escaped_marker = re.escape(marker)
    return (
        re.compile(rf"{escaped_marker}\s+({HANDLE_PATTERN})\b"),
        re.compile(rf"{escaped_marker}\s+({HANDLE_PATTERN})/([0-9]{{3}})/@file\b"),
    )


def handle_prefix(handle: str) -> str:
    """Return the document-type prefix from a requirement handle."""
    return handle.split("-", 1)[0]

def is_excluded(root: Path, path: Path, excluded_dirs: set[str]) -> bool:
    return any(part in excluded_dirs for part in path.relative_to(root).parts)

# @reqtrace TRD-3
def scan_repository(root: Path, config: dict[str, Any]) -> ScanResult:
    trace_re, legacy_re = compile_patterns(config["marker"])
    excluded_dirs = set(config["excluded_dirs"])
    ledger_path = project_path(root, config["ledger_path"])
    registry_path = project_path(root, config["registry_path"])
    occurrences: list[Occurrence] = []
    legacy_occurrences: list[LegacyOccurrence] = []
    errors: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or is_excluded(root, path, excluded_dirs):
            continue
        if path.resolve() in {ledger_path, registry_path}:
            continue
        relative_path = path.relative_to(root).as_posix()
        kind = role_for_path(relative_path, config["role_map"])
        if path.suffix.lower() == ".md" and kind == "unknown":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        except OSError as error:
            raise ReqtraceError(f"cannot read {path.relative_to(root).as_posix()}: {error}") from error

        for line_number, line in enumerate(lines, start=1):
            current_matches = list(trace_re.finditer(line))
            legacy_matches = list(legacy_re.finditer(line))
            nonlegacy_current = [
                match
                for match in current_matches
                if not any(legacy.start() <= match.start() < legacy.end() for legacy in legacy_matches)
            ]
            marker_count = len(nonlegacy_current) + len(legacy_matches)
            location = f"{relative_path}:{line_number}"
            if marker_count > 1:
                errors.append(f"E_MULTIPLE_MARKERS_ON_LINE {location}")
                continue
            if legacy_matches and nonlegacy_current:
                errors.append(f"E_AMBIGUOUS_MARKER {location}")
                continue
            if legacy_matches:
                legacy = legacy_matches[0]
                legacy_occurrences.append(
                    LegacyOccurrence(legacy.group(1), legacy.group(2), relative_path, line_number)
                )
                continue
            if nonlegacy_current:
                current = nonlegacy_current[0]
                occurrences.append(Occurrence(current.group(1), relative_path, line_number, kind))

    return ScanResult(occurrences, legacy_occurrences, errors)

def role_for_path(relative_path: str, role_map: dict[str, str]) -> str:
    for pattern, kind in role_map.items():
        if fnmatchcase(relative_path, pattern):
            return kind
    return "unknown"

# @reqtrace TRD-4
def short_id(path: str, line: int, length: int = 4) -> str:
    digest = hashlib.sha256(f"{path}:{line}".encode("utf-8")).hexdigest()
    return digest[:length]

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

# @reqtrace TRD-5
def write_ledger(path: Path, records: Iterable[LedgerRecord]) -> None:
    ordered = sorted(records, key=lambda item: (item.handle, item.path, item.line))
    content = "".join(
        json.dumps(record.as_json(), separators=(", ", ": ")) + "\n" for record in ordered
    )
    atomic_write_text(path, content)

def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as temporary:
            temporary.write(content)
            temporary_name = temporary.name
        Path(temporary_name).replace(path)
    except OSError as error:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        raise ReqtraceError(f"cannot write {path}: {error}") from error

def read_ledger(path: Path) -> tuple[list[LedgerRecord], list[str]]:
    if not path.exists():
        return [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ReqtraceError(f"cannot read {path}: {error}") from error

    records: list[LedgerRecord] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(lines, start=1):
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as error:
            errors.append(f"E_LEDGER_PARSE {path.as_posix()}:{line_number}: {error.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"E_LEDGER_PARSE {path.as_posix()}:{line_number}: record must be an object")
            continue
        record = ledger_record_from_json(value)
        if record is None:
            errors.append(f"E_LEDGER_PARSE {path.as_posix()}:{line_number}: invalid record schema")
            continue
        records.append(record)
    return records, errors

def ledger_record_from_json(value: dict[str, Any]) -> LedgerRecord | None:
    required = ("handle", "id", "path", "line", "kind")
    if not set(required) <= set(value):
        return None
    handle, record_id, path, line, kind = (
        value["handle"], value["id"], value["path"], value["line"], value["kind"]
    )
    if not isinstance(handle, str) or not HANDLE_RE.fullmatch(handle):
        return None
    if not isinstance(record_id, str) or not re.fullmatch(r"[0-9a-f]+", record_id):
        return None
    if not isinstance(path, str) or not path or Path(path).is_absolute() or "\\" in path:
        return None
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        return None
    if not isinstance(kind, str) or not kind:
        return None
    return LedgerRecord(handle=handle, id=record_id, path=path, line=line, kind=kind)

# @reqtrace TRD-6
def parse_registry_text(path: Path, content: str) -> tuple[list[dict[str, Any]], list[str]]:
    lines = content.splitlines()
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    handles: set[str] = set()
    for line_number, raw_line in enumerate(lines, start=1):
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as error:
            errors.append(
                f"E_REGISTRY_PARSE_ERROR {path.as_posix()}:{line_number}: {error.msg}"
            )
            continue
        if not isinstance(value, dict):
            errors.append(
                f"E_REGISTRY_PARSE_ERROR {path.as_posix()}:{line_number}: record must be an object"
            )
            continue
        handle = value.get("handle")
        entry_type = value.get("type")
        source = value.get("source")
        if (
            not isinstance(handle, str)
            or not HANDLE_RE.fullmatch(handle)
            or (entry_type is not None and (not isinstance(entry_type, str) or not entry_type))
            or (source is not None and not isinstance(source, str))
            or handle in handles
        ):
            errors.append(
                f"E_REGISTRY_PARSE_ERROR {path.as_posix()}:{line_number}: invalid record schema"
            )
            continue
        handles.add(handle)
        entries.append(value)
    return entries, errors

def read_registry_with_text(path: Path) -> tuple[list[dict[str, Any]], list[str], str]:
    if not path.exists():
        return [], [], ""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReqtraceError(f"cannot read {path}: {error}") from error
    entries, errors = parse_registry_text(path, content)
    return entries, errors, content

def read_registry(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    entries, errors, _ = read_registry_with_text(path)
    return entries, errors

def register_unknown_handles(
    path: Path, records: Iterable[LedgerRecord]
) -> list[str]:
    entries, errors = read_registry(path)
    if errors:
        return errors
    known = {entry["handle"] for entry in entries}
    additions = sorted({record.handle for record in records} - known)
    if not additions:
        return []
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if original and not original.endswith("\n"):
        original += "\n"
    content = original + "".join(
        json.dumps({"handle": handle, "type": "unknown"}, separators=(", ", ": ")) + "\n"
        for handle in additions
    )
    atomic_write_text(path, content)
    return []

def print_messages(messages: Iterable[str], stream: Any | None = None) -> None:
    if stream is None:
        stream = sys.stderr
    for message in messages:
        print(message, file=stream)

def scan_records(root: Path, config: dict[str, Any]) -> tuple[ScanResult, list[LedgerRecord], list[str]]:
    scan = scan_repository(root, config)
    records, record_errors = records_from_occurrences(scan.occurrences, config["id_length"])
    return scan, records, [*scan.errors, *record_errors]

def command_init(root: Path, _: argparse.Namespace) -> int:
    config_path = root / ".reqtrace.json"
    config = starter_config(root)
    ledger_path = project_path(root, config["ledger_path"])
    registry_path = project_path(root, config["registry_path"])
    existing = [path.relative_to(root).as_posix() for path in (config_path, ledger_path, registry_path) if path.exists()]
    if existing:
        print(f"E_INIT_EXISTS refusing to overwrite: {', '.join(existing)}", file=sys.stderr)
        return 2
    written: list[Path] = []
    created_dirs: list[Path] = []
    try:
        for path, content in ((config_path, json.dumps(config, indent=2) + "\n"), (registry_path, "")):
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                created_dirs.append(path.parent)
            atomic_write_text(path, content)
            written.append(path)
        if not ledger_path.parent.exists():
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.append(ledger_path.parent)
        write_ledger(ledger_path, [])
    except ReqtraceError as error:
        for path in written:
            path.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        print(error, file=sys.stderr)
        return 2
    invocation = Path(sys.argv[0]).name
    print("1. Add @reqtrace <HANDLE> near source or test evidence.")
    print(f"2. Run {invocation} generate.")
    print(f"3. Run {invocation} check --strict.")
    return 0


# @reqtrace TRD-7
def command_register(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    handle = args.handle
    if not isinstance(handle, str) or not HANDLE_RE.fullmatch(handle):
        print(f"E_INVALID_HANDLE: {handle!r} must match {HANDLE_PATTERN}", file=sys.stderr)
        return 1

    registry_path = project_path(root, config["registry_path"])
    registry, errors, original = read_registry_with_text(registry_path)
    if errors:
        print_messages(errors)
        return 2
    if handle in {entry["handle"] for entry in registry}:
        print(f"E_DUPLICATE_HANDLE: {handle} is already registered", file=sys.stderr)
        return 1

    source = args.source
    if source is not None and not project_path(root, source).is_file():
        print(f"E_REGISTRY_SOURCE_MISSING: {source} not found", file=sys.stderr)
        return 1

    entry: dict[str, str] = {"handle": handle, "type": args.type or "unknown"}
    if source is not None:
        entry["source"] = source
    if original and not original.endswith("\n"):
        original += "\n"
    atomic_write_text(registry_path, original + json.dumps(entry, separators=(", ", ": ")) + "\n")
    print(f"REQTRACE REGISTERED {handle}")
    print(f"marker:   {config['marker']} {handle}")
    print(f"registry: {config['registry_path']}")
    return 0

# @reqtrace TRD-7
def command_scan(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    scan, records, errors = scan_records(root, config)
    diff = getattr(args, "diff", False)
    output_format = getattr(args, "format", "text")
    committed: list[LedgerRecord] = []
    ledger_errors: list[str] = []
    if diff or output_format == "json":
        committed, ledger_errors = read_ledger(project_path(root, config["ledger_path"]))
        errors.extend(ledger_errors)
    if diff:
        if ledger_errors:
            records = []
        else:
            committed_identities = {record.source_identity() for record in committed}
            records = [record for record in records if record.source_identity() not in committed_identities]
    if output_format == "json":
        committed_by_source = {record.source_identity(): record for record in committed}
        print(
            json.dumps(
                [
                    {
                        "handle": record.handle,
                        "path": record.path,
                        "line": record.line,
                        "kind": committed_by_source.get(record.source_identity()).kind
                        if record.source_identity() in committed_by_source
                        else None,
                        "id": committed_by_source.get(record.source_identity()).id
                        if record.source_identity() in committed_by_source
                        else None,
                    }
                    for record in records
                ],
                indent=2,
            )
        )
        print_messages(errors)
        return 0
    grouped: dict[str, list[LedgerRecord]] = defaultdict(list)
    for record in records:
        grouped[record.handle].append(record)
    if not grouped:
        total = len(scan.occurrences) + len(scan.legacy_occurrences)
        if diff and total > 0:
            print("No new annotations (all are already in the committed ledger).")
        else:
            print("No Reqtrace comments found.")
    for handle in sorted(grouped):
        print(handle)
        for record in grouped[handle]:
            print(f"  {record.path}:{record.line} id={record.id} kind={record.kind}")
    if not diff:
        for legacy in scan.legacy_occurrences:
            print(f"legacy {legacy.path}:{legacy.line} {legacy.handle}/{legacy.ordinal}")
    print_messages(errors)
    return 0

# @reqtrace TRD-7
def command_generate(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    scan, records, errors = scan_records(root, config)
    if errors:
        print_messages(errors)
        return 2
    write_ledger(project_path(root, config["ledger_path"]), records)
    if args.register_unknown:
        try:
            registry_errors = register_unknown_handles(
                project_path(root, config["registry_path"]), records
            )
        except ReqtraceError as error:
            print(error, file=sys.stderr)
            return 2
        if registry_errors:
            print_messages(registry_errors)
            return 2
    if scan.legacy_occurrences:
        for legacy in scan.legacy_occurrences:
            print(
                f"warning: E_LEGACY_FORM {legacy.path}:{legacy.line} "
                f"{legacy.handle}/{legacy.ordinal}",
                file=sys.stderr,
            )
    return 0

# @reqtrace TRD-7
def command_render(root: Path, config: dict[str, Any], _: argparse.Namespace) -> int:
    ledger_path = project_path(root, config["ledger_path"])
    records, errors = read_ledger(ledger_path)
    if errors:
        print_messages(errors)
        return 2
    try:
        render_documents(root, config, records)
    except ReqtraceError as error:
        print(error, file=sys.stderr)
        return 2
    return 0

def render_documents(root: Path, config: dict[str, Any], records: Iterable[LedgerRecord]) -> None:
    records_by_handle: dict[str, list[LedgerRecord]] = defaultdict(list)
    for record in records:
        records_by_handle[record.handle].append(record)
    excluded_dirs = set(config["excluded_dirs"])
    docs_root = root / "docs"
    if not docs_root.exists():
        return
    for path in sorted(docs_root.rglob("*.md")):
        if is_excluded(root, path, excluded_dirs):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as error:
            raise ReqtraceError(f"cannot read {path.relative_to(root).as_posix()}: {error}") from error
        rendered: list[str] = []
        found_block = False
        index = 0
        while index < len(lines):
            start = START_BLOCK_RE.match(lines[index].rstrip("\r\n"))
            if not start:
                rendered.append(lines[index])
                index += 1
                continue
            handle = start.group(1)
            rendered.append(lines[index])
            index += 1
            end_index = index
            while end_index < len(lines) and not END_BLOCK_RE.match(lines[end_index].rstrip("\r\n")):
                end_index += 1
            if end_index == len(lines):
                raise ReqtraceError(
                    f"unterminated ledger block for {handle} in {path.relative_to(root).as_posix()}"
                )
            found_block = True
            for record in sorted(records_by_handle[handle], key=lambda item: (item.path, item.line)):
                rendered.append(f"- {record.handle}/{record.id}/{record.path}:{record.line}\n")
            rendered.append(lines[end_index])
            index = end_index + 1
        rendered_content = "".join(rendered)
        if found_block and rendered_content != "".join(lines):
            atomic_write_text(path, rendered_content)

# @reqtrace TRD-8
def command_check(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    scan, generated, errors = scan_records(root, config)
    failures = False
    error_codes: list[str] = []

    def emit_error(message: str) -> None:
        nonlocal failures
        print(message, file=sys.stderr)
        code = message.split(" ", 1)[0]
        if code not in error_codes:
            error_codes.append(code)
        failures = True

    if errors:
        for message in errors:
            emit_error(message)
    for legacy in scan.legacy_occurrences:
        message = f"E_LEGACY_FORM {legacy.path}:{legacy.line} {legacy.handle}/{legacy.ordinal}"
        if config["legacy_form"] == "reject":
            emit_error(message)
        else:
            print(f"warning: {message}", file=sys.stderr)

    committed, ledger_errors = read_ledger(project_path(root, config["ledger_path"]))
    if ledger_errors:
        for message in ledger_errors:
            emit_error(message)
    else:
        if sorted(record.identity() for record in generated) != sorted(
            record.identity() for record in committed
        ):
            emit_error("E_STALE_LEDGER committed ledger differs from a fresh scan")
            if sorted(record.source_identity() for record in generated) == sorted(
                record.source_identity() for record in committed
            ):
                print("hint: ledger may need regeneration after id_length change", file=sys.stderr)

    if config["doc_hierarchy"]:
        leaf = config["doc_hierarchy"][-1]
        implementation_records = [record for record in generated if record.kind == "implementation"]
        for record in implementation_records:
            prefix = handle_prefix(record.handle)
            if prefix != leaf and (prefix in config["doc_hierarchy"] or prefix == "V2M"):
                emit_error(
                    f"E_OFFLEAF_HANDLE {record.handle} at {record.path}:{record.line} "
                    f"(expected leaf: {leaf})"
                )
        records_by_file: dict[str, list[LedgerRecord]] = defaultdict(list)
        for record in implementation_records:
            records_by_file[record.path].append(record)
        for file_path, file_records in records_by_file.items():
            ordered_records = sorted(file_records, key=lambda record: record.line)
            blocks: list[list[LedgerRecord]] = []
            current_block = [ordered_records[0]]
            for record in ordered_records[1:]:
                if record.line - current_block[-1].line <= 1:
                    current_block.append(record)
                else:
                    blocks.append(current_block)
                    current_block = [record]
            blocks.append(current_block)
            for block in blocks:
                handles = sorted({record.handle for record in block})
                if len(handles) > 1:
                    emit_error(
                        f"E_MULTI_HANDLE_EVIDENCE {file_path}:{block[0].line}-{block[-1].line} "
                        f"has {len(handles)} handles: {', '.join(handles)}"
                    )

    requested_level = getattr(args, "strict", None)
    strict_level = requested_level if requested_level is not None else config["strict_level"]
    registry_for_summary: list[dict[str, Any]] | None = None
    if strict_level == "full":
        registry_for_summary, registry_errors = read_registry(project_path(root, config["registry_path"]))
        if registry_errors:
            for message in registry_errors:
                emit_error(message)
        else:
            registry_by_handle = {entry["handle"]: entry for entry in registry_for_summary}
            for handle in sorted({record.handle for record in generated}):
                entry = registry_by_handle.get(handle)
                if entry is None or entry.get("type") in {None, "unknown"}:
                    emit_error(f"E_HANDLE_NOT_REGISTERED {handle}")
            for entry in registry_for_summary:
                source = entry.get("source")
                if source is None:
                    continue
                if not source:
                    emit_error(
                        f"E_REGISTRY_SOURCE_MISSING {entry['handle']} "
                        f"(source: blank)"
                    )
                    continue
                try:
                    source_path = project_path(root, source)
                except ReqtraceError as error:
                    emit_error(
                        f"E_REGISTRY_SOURCE_MISSING {entry['handle']} "
                        f"(source: {source} invalid: {error})"
                    )
                    continue
                if not source_path.exists():
                    emit_error(
                        f"E_REGISTRY_SOURCE_MISSING {entry['handle']} "
                        f"(source: {source} not found)"
                    )
    output_format = getattr(args, "format", "text")
    if failures:
        if output_format == "json":
            print(json.dumps({"status": "fail", "errors": error_codes}))
        else:
            print(f"REQTRACE FAIL checks={len(error_codes)}", file=sys.stderr)
            print(
                "fix: python scripts/reqtrace.py generate && python scripts/reqtrace.py check --strict",
                file=sys.stderr,
            )
        return 1

    if registry_for_summary is None:
        registry_for_summary, _ = read_registry(project_path(root, config["registry_path"]))
    buckets, _ = coverage_data(registry_for_summary, committed)
    summary = coverage_summary(buckets)
    if output_format == "json":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "registered": len(registry_for_summary),
                    "full": summary["full"],
                    "partial": summary["partial"],
                    "zero": summary["zero"],
                }
            )
        )
    else:
        print(
            f"REQTRACE OK registered={len(registry_for_summary)} full={summary['full']} "
            f"partial={summary['partial']} zero={summary['zero']}"
        )
    return 0

# @reqtrace TRD-12
def coverage_data(
    registry: Iterable[dict[str, Any]], ledger: Iterable[LedgerRecord]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Build deterministic role-aware coverage entries from registry and ledger records."""
    records_by_handle: dict[str, list[LedgerRecord]] = defaultdict(list)
    for record in ledger:
        records_by_handle[record.handle].append(record)
    buckets: dict[str, list[dict[str, Any]]] = {"zero": [], "partial": [], "full": []}
    registry_by_handle = {entry["handle"]: entry for entry in registry}
    items: list[dict[str, Any]] = []
    for handle in sorted(set(registry_by_handle) | set(records_by_handle)):
        records = records_by_handle[handle]
        entry = registry_by_handle.get(handle, {})
        kinds = sorted({record.kind for record in records})
        implementation = "implementation" in kinds
        verification = "verification" in kinds
        documentation = "documentation" in kinds
        if implementation and verification:
            status = "both"
        elif implementation:
            status = "implementation"
        elif verification:
            status = "verification"
        elif records:
            status = "documentation-only" if documentation else "non-implementation-only"
        else:
            status = "none"
        item: dict[str, Any] = {
            "handle": handle,
            "type": entry.get("type", "unknown"),
            "source": entry.get("source"),
            "occurrences": len(records),
            "kinds": kinds,
            "kind_counts": {kind: sum(record.kind == kind for record in records) for kind in kinds},
            "implementation": implementation,
            "verification": verification,
            "documentation": documentation,
            "status": status,
        }
        if implementation and verification:
            bucket = "full"
        elif implementation or verification:
            bucket = "partial"
        else:
            bucket = "zero"
        buckets[bucket].append(item)
        items.append(item)
    return buckets, items


def coverage_summary(buckets: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Derive summary counts directly from coverage bucket lists."""
    return {
        "total": sum(len(buckets[bucket]) for bucket in ("full", "partial", "zero")),
        "full": len(buckets["full"]),
        "partial": len(buckets["partial"]),
        "zero": len(buckets["zero"]),
    }


# @reqtrace TRD-12
def command_report(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    registry, registry_errors = read_registry(project_path(root, config["registry_path"]))
    ledger, ledger_errors = read_ledger(project_path(root, config["ledger_path"]))
    if registry_errors or ledger_errors:
        print_messages([*registry_errors, *ledger_errors])
        return 2
    buckets, items = coverage_data(registry, ledger)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "schemaVersion": "2.1",
                    "handles": buckets,
                    "summary": coverage_summary(buckets),
                },
                indent=2,
            )
        )
        return 0
    if args.format == "github":
        print("| Handle | Implementation | Verification | Documentation | Status |")
        print("| --- | --- | --- | --- | --- |")
        for item in items:
            print(
                f"| {item['handle']} | {'yes' if item['implementation'] else 'no'} | "
                f"{'yes' if item['verification'] else 'no'} | "
                f"{'yes' if item['documentation'] else 'no'} | {item['status']} |"
            )
        return 0
    total = len(items)
    print(
        f"Coverage: {len(buckets['full'])} full, {len(buckets['partial'])} partial, "
        f"{len(buckets['zero'])} zero ({total} reported handles)"
    )
    for bucket in ("zero", "partial", "full"):
        print(f"{bucket} ({len(buckets[bucket])})")
        for entry in buckets[bucket]:
            roles = ", ".join(entry["kinds"]) or "none"
            print(
                f"  {entry['handle']} [{entry['type']}] {entry['occurrences']} occurrence(s) "
                f"roles={roles} status={entry['status']}"
            )
    return 0

def read_legacy_ledger(root: Path) -> list[tuple[str, str, str]]:
    legacy_ledger = root / "docs" / "requirements.md"
    if not legacy_ledger.exists():
        return []
    try:
        lines = legacy_ledger.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ReqtraceError(f"cannot read docs/requirements.md: {error}") from error
    entries: list[tuple[str, str, str]] = []
    for line in lines:
        match = LEGACY_LEDGER_RE.match(line)
        if match:
            entries.append(match.groups())
    return entries

# @reqtrace TRD-9
def command_migrate(root: Path, config: dict[str, Any], args: argparse.Namespace) -> int:
    print(
        "warning: migrate is deprecated V1 transition support; use only for legacy annotations.",
        file=sys.stderr,
    )
    scan = scan_repository(root, config)
    if scan.errors:
        print_messages(scan.errors)
        return 2
    legacy_ledger = read_legacy_ledger(root)
    post_migration_locations = {
        (occurrence.handle, occurrence.path) for occurrence in scan.occurrences
    } | {(occurrence.handle, occurrence.path) for occurrence in scan.legacy_occurrences}
    warnings = [
        f"warning: legacy ledger entry has no matching post-migration code occurrence: "
        f"{handle}/{ordinal}/{path}"
        for handle, ordinal, path in legacy_ledger
        if (handle, path) not in post_migration_locations
    ]
    if args.dry_run:
        for occurrence in scan.legacy_occurrences:
            print(
                f"would migrate {occurrence.path}:{occurrence.line} "
                f"{occurrence.handle}/{occurrence.ordinal}"
            )
        print_messages(warnings)
        return 1 if warnings else 0

    legacy_re = compile_patterns(config["marker"])[1]
    changed_paths = sorted({root / occurrence.path for occurrence in scan.legacy_occurrences})
    for path in changed_paths:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"cannot read {path.relative_to(root).as_posix()}: {error}", file=sys.stderr)
            return 2
        migrated = legacy_re.sub(lambda match: f"{config['marker']} {match.group(1)}", content)
        atomic_write_text(path, migrated)

    migrated_scan, records, errors = scan_records(root, config)
    if errors or migrated_scan.legacy_occurrences:
        print_messages(errors)
        for occurrence in migrated_scan.legacy_occurrences:
            print(f"E_LEGACY_FORM {occurrence.path}:{occurrence.line}", file=sys.stderr)
        return 2
    write_ledger(project_path(root, config["ledger_path"]), records)
    print_messages(warnings)
    return 1 if warnings else 0

# @reqtrace TRD-7
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the grep-native Reqtrace ledger.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    scan = subcommands.add_parser("scan", help="print source annotations")
    scan.add_argument("--format", choices=("text", "json"), default="text")
    scan.add_argument("--diff", action="store_true", help="show annotations absent from the ledger")
    subcommands.add_parser("init", help="write starter local Reqtrace files")
    register = subcommands.add_parser("register", help="append a validated handle to the registry")
    register.add_argument("handle")
    register.add_argument("--type")
    register.add_argument("--source")
    generate = subcommands.add_parser("generate", help="write the canonical JSONL ledger")
    generate.add_argument(
        "--register-unknown", action="store_true", help="add unregistered handles as type unknown"
    )
    subcommands.add_parser("render", help="render Markdown ledger blocks")
    check = subcommands.add_parser("check", help="fail when the committed ledger is stale")
    check.add_argument(
        "--strict",
        nargs="?",
        const="full",
        choices=("ledger", "full"),
        help="run full validation, or specify ledger or full explicitly",
    )
    check.add_argument("--format", choices=("text", "json"), default="text")
    report = subcommands.add_parser("report", help="report coverage from registry and ledger")
    report.add_argument("--format", choices=("text", "json", "github"), default="text")
    migrate = subcommands.add_parser(
        "migrate", help="deprecated: rewrite legacy annotations and generate the ledger"
    )
    migrate.add_argument("--dry-run", action="store_true", help="show migration changes without writing")
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = Path.cwd().resolve()
        if args.command == "init":
            try:
                existing_root = find_project_root(root)
            except ReqtraceError:
                return command_init(root, args)
            print(
                f"E_INIT_EXISTS already inside a Reqtrace project rooted at {existing_root.as_posix()}",
                file=sys.stderr,
            )
            return 2
        root = find_project_root(root)
        config = load_config(root)
        commands = {
            "scan": command_scan,
            "register": command_register,
            "generate": command_generate,
            "render": command_render,
            "check": command_check,
            "report": command_report,
            "migrate": command_migrate,
        }
        return commands[args.command](root, config, args)
    except ReqtraceError as error:
        print(error, file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
