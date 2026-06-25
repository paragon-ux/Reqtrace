[![CI](https://github.com/paragon-ux/Reqtrace/actions/workflows/reqtrace.yml/badge.svg)](https://github.com/paragon-ux/Reqtrace/actions/workflows/reqtrace.yml)

# Reqtrace

Reqtrace is a grep-native convention for tracing implementation evidence to an existing upstream handle. A handle may belong to a requirement, ADR, security control, policy, compliance rule, or test specification.

Reqtrace starts after that handle already exists. It does not create, rename, split, supersede, or interpret upstream artifacts.

Current release: [`v2.1.5`](https://github.com/paragon-ux/Reqtrace/releases/tag/v2.1.5).

## One Marker, One Record

Place one marker near source, test, or documentation evidence:

```txt
@reqtrace <handle>
```

The validator derives the repo-relative path, line, role, and short occurrence ID. There are no manual ordinals or `@file` placeholders.

The canonical ledger is `docs/trace-ledger.jsonl`: a generated, sorted JSON Lines file. `docs/handle-registry.jsonl` lists known upstream handles and their types. Both remain grep-friendly files.

## Marker Semantics

Reqtrace markers are evidence annotations, not explanatory comments. Use `@reqtrace <HANDLE>` to connect code, tests, docs, and artifacts to upstream handles.

Do not use markers as a substitute for comments that explain intent, invariants, tradeoffs, surprising logic, security assumptions, or maintenance hazards. When adding markers to existing code, preserve existing explanatory comments. If a code path needed a comment before annotation, it still needs one after.

The project uses markers in calibration fixtures and examples to test and demonstrate the evidence convention. Production code should only carry `@reqtrace` markers when tied to meaningful upstream requirements. Calibration fixtures are scanner/report/check fixtures, not production annotation style guides.

## Quickstart

```bash
python scripts/reqtrace.py init
python scripts/reqtrace.py register AUTH-LOGIN --type requirement --source docs/requirements.md
# Add: @reqtrace AUTH-LOGIN
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict
```

## Workflow

1. Add a marker using an existing registered handle.
2. Run `python scripts/reqtrace.py generate`.
3. Run `python scripts/reqtrace.py render` to refresh Markdown ledger blocks.
4. Run `python scripts/reqtrace.py check --strict` before committing.

`check --strict` is enforced in the supplied pre-commit hook and GitHub Actions workflow. It detects stale ledgers, malformed ledger records, legacy annotations, and ambiguous markers. Use `check --strict=full` to also require complete registry metadata.

## Commands

| Command | Purpose |
| --- | --- |
| `python scripts/reqtrace.py init` | Create a starter config, empty registry, and empty ledger from detected project directories. |
| `python scripts/reqtrace.py register <HANDLE> [--type TYPE] [--source PATH]` | Add a handle to the registry and print the marker to place. |
| `python scripts/reqtrace.py scan` | Print annotations for diagnosis. |
| `python scripts/reqtrace.py scan --format json` | Emit annotation objects for automation. |
| `python scripts/reqtrace.py scan --diff` | Show source annotations absent from the committed ledger. |
| `python scripts/reqtrace.py generate` | Write the canonical JSONL ledger. |
| `python scripts/reqtrace.py render` | Refresh Markdown ledger blocks. |
| `python scripts/reqtrace.py check --strict` | Use the configured strict policy (`ledger` by default). |
| `python scripts/reqtrace.py check --strict=ledger` | Enforce ledger freshness only. |
| `python scripts/reqtrace.py check --strict=full` | Enforce ledger freshness and registry completeness. |
| `python scripts/reqtrace.py report --format github` | Emit a Markdown coverage table. |
| `python scripts/reqtrace.py migrate --dry-run` | Inspect deprecated V1 transition migration. |

Use `report --format json` for machine-readable coverage. A handle is full when it has implementation evidence, partial when it has only non-implementation evidence, and zero when it has no ledger records; each entry also lists observed role kinds and status.

## What Reqtrace Delegates

Reqtrace v2.1.5 stabilizes the evidence convention. It does not replace every
surrounding workflow.

- **Search / command compression:** use `grep`, `rg`, or RTK.
- **Hierarchy presets:** use Doorstop, Sphinx-Needs/Open-Needs, OpenFastTrace, Jira, or Azure Boards. Reqtrace coexists with any of these; use their IDs as handles.
- **HTML dashboards:** generate from `report --format json`.
- **Blame / provenance:** join `scan --format json` and `trace-ledger.jsonl` in downstream tooling.
- **Graph visualization:** build from the registry and ledger JSONL files.

Reqtrace owns the portable evidence layer. See
[`docs/adr/0001-v2.1.5-core-boundaries.md`](docs/adr/0001-v2.1.5-core-boundaries.md)
for the full delegation rationale.

## Grep First

Reqtrace requires no service, database, daemon, or runtime dependency beyond Python 3's standard library. If the CLI is unavailable, traces remain discoverable with normal repository search:

```bash
grep -R "@reqtrace " .
grep -R "ADR-0012" .
```

The optional V1 legacy form is recognized during the transition and configured by `.reqtrace.json`'s `legacy_form` setting. Run `migrate` to rewrite it.

## Examples

- **[examples/refresh-token/](examples/refresh-token/)** — Full walkthrough:
  source files, tests, explanatory comments, trace markers, and a rendered
  ledger block for a token-rotation requirement.
- **[examples/calibration/](examples/calibration/)** — Seven scenario fixtures
  proving every documented claim. Run `python examples/calibration/run.py` to
  verify.

## Documentation Site

The full reference is published at
[https://paragon-ux.github.io/Reqtrace/](https://paragon-ux.github.io/Reqtrace/).

## Integrations

- **`.pre-commit-hooks.yaml`** — Pre-commit hook that runs `check --strict`
  to block trace drift before commit.
- **`AGENTS.md`** — Guidance for AI coding agents working in this repo.
- **`skills/`** — Reqtrace annotation and audit skills for AI-assisted
  development workflows.
