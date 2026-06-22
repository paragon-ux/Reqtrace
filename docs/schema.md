# JSON Contracts

Reqtrace exposes four stable JSON contracts. Field names and types do not change
within a `schemaVersion`; command output uses `--format json` and the ledger and
registry remain JSON Lines files.

## Annotation (`scan --format json`)

Each array item describes one annotation occurrence.

| Field | Type | Description |
| --- | --- | --- |
| `handle` | string | Upstream handle identifier. |
| `path` | string | Repo-relative file path. |
| `line` | integer | 1-based line number. |
| `kind` | string\|null | Role: `implementation`, `verification`, `documentation`, `migration`, or `operational`; `null` without a matching ledger record. |
| `id` | string\|null | Occurrence ID from the ledger; `null` without a matching ledger record. |

## Ledger Record (`docs/trace-ledger.jsonl`)

Each JSONL line is one generated occurrence record.

| Field | Type | Description |
| --- | --- | --- |
| `handle` | string | Upstream handle identifier. |
| `id` | string | Four-character occurrence ID, stable for its handle, path, and line. |
| `path` | string | Repo-relative file path. |
| `line` | integer | 1-based line number. |
| `kind` | string | Inferred role. |

## Coverage Report (`report --format json`)

The report is a versioned envelope. Its handle arrays use the per-handle object
defined after the envelope table.

| Field | Type | Description |
| --- | --- | --- |
| `schemaVersion` | string | `"2.1"`. |
| `handles` | object | `full`, `partial`, and `zero` arrays of handle objects. |
| `summary` | object | Integer `total`, `full`, `partial`, and `zero` counts. |

| Field | Type | Description |
| --- | --- | --- |
| `handle` | string | Upstream handle identifier. |
| `type` | string | Registry type, or `unknown` when unregistered. |
| `source` | string\|null | Registry source path. |
| `occurrences` | integer | Total annotation sites. |
| `kinds` | array | Unique observed role strings. |
| `kind_counts` | object | Count by role string. |
| `implementation` | boolean | Has implementation evidence. |
| `verification` | boolean | Has verification evidence. |
| `documentation` | boolean | Has documentation evidence. |
| `status` | string | `both`, `implementation`, `verification`, `documentation-only`, `non-implementation-only`, or `none`. |

## Registry Record (`docs/handle-registry.jsonl`)

Each JSONL line describes one upstream handle.

| Field | Type | Description |
| --- | --- | --- |
| `handle` | string | Unique upstream handle identifier. |
| `type` | string\|absent | Handle type, such as `requirement` or `security-control`. |
| `source` | string\|absent | Repo-relative source-document path. |
| `parent` | string\|absent | Reserved immediate-parent handle in a vertical hierarchy. |
| `links` | array\|absent | Reserved peer-handle relationships. |

Fields are absent rather than `null` when unavailable. In v2.1.5, `register`
writes `handle`, then `type` and `source` only when supplied. The register does not write `parent` or `links`.
Reqtrace preserves reserved relationship fields already in
the registry, but `check` does not infer, require, or validate their semantics.
Tools, agents, and users may add those fields directly. Future releases may add
CLI support after real-world relationship usage establishes the right model.

> **Reserved relationship fields:** `parent` and `links` are deliberately
> reserved but unenforced in v2.1.5. Downstream tools can traverse them without
> forcing Reqtrace core to choose a hierarchy model prematurely.

## Exit Codes

| Exit code | Meaning |
| --- | --- |
| 0 | Command succeeded; `check` passed or a generated file was written. |
| 1 | A validation failed, such as `check` drift, a duplicate handle, or a missing source. |
