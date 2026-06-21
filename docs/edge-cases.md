# Edge Cases

## Multiple Markers on One Line

One line may contain only one valid marker. Multiple markers create `E_MULTIPLE_MARKERS_ON_LINE`; split them onto the evidence lines they describe.

## Legacy Annotations

V1 annotations are recognized as legacy rather than ignored. With `legacy_form: "warn"`, `check` reports a warning. With `legacy_form: "reject"`, it fails. Run `migrate --dry-run` before `migrate` to preview source rewrites and any legacy ledger entries without matching code.

## Stale Ledger Paths

A source move changes the derived path and line. Run `generate` and `render`; do not patch JSONL or Markdown bullet text by hand. `check` reports `E_STALE_LEDGER` until the generated result is committed.

## Registry Gaps

Non-strict checks permit an unregistered handle so teams can adopt Reqtrace incrementally. Strict checks reject missing registrations and `unknown` types. Add an explicit registry record after confirming the upstream artifact.

## Hash Collisions

Occurrence IDs begin at four hexadecimal characters. If two entries for the same handle collide, generation retries six and then eight characters before failing loudly with `E_ID_COLLISION`.

## Generated and Binary Files

Configured generated directories are not scanned. Put markers in human-maintained source or tests. Non-UTF-8 files are skipped because their text cannot provide a reliable grep-native annotation.
