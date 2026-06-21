# Reqtrace

Reqtrace is a grep-native convention for tracing implementation evidence to an existing upstream handle. A handle may belong to a requirement, ADR, security control, policy, compliance rule, or test specification.

Reqtrace starts after that handle already exists. It does not create, rename, split, supersede, or interpret upstream artifacts.

## One Marker, One Record

Place one marker near source, test, or documentation evidence:

```txt
@reqtrace <handle>
```

The validator derives the repo-relative path, line, role, and short occurrence ID. There are no manual ordinals or `@file` placeholders.

The canonical ledger is `docs/trace-ledger.jsonl`: a generated, sorted JSON Lines file. `docs/handle-registry.jsonl` lists known upstream handles and their types. Both remain grep-friendly files.

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

## Grep First

Reqtrace requires no service, database, daemon, or runtime dependency beyond Python 3's standard library. If the CLI is unavailable, traces remain discoverable with normal repository search:

```bash
grep -R "@reqtrace " .
grep -R "ADR-0012" .
```

The optional V1 legacy form is recognized during the transition and configured by `.reqtrace.json`'s `legacy_form` setting. Run `migrate` to rewrite it.
