# Edge Cases

## Multiple Ordinals in the Same File

A file can contain multiple implementation occurrences for the same requirement when each occurrence has a distinct ordinal.

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/002/@file
function validateRefreshTokenOwnership(token, userId) {}
```

Both resolve through the same file path, but the ordinals keep the occurrences distinct.

## Same Ordinal Repeated in the Same File

Repeating the same ordinal in the same file is usually accidental.

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenOwnership(token, userId) {}
```

Keep one trace near the strongest implementation evidence or assign distinct ordinals when there are truly separate occurrences.

## Same Ordinal Repeated Across Different Files

Repeating the same ordinal across different files creates ambiguous implementation evidence.

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/rotation.js
```

Use a unique ordinal for each validated occurrence.

## Requirement Rename

Requirement renames are allowed only when the meaning is preserved.

Safe rename:

```txt
AUTH-SESSION-ROTATION -> AUTH-REFRESH-TOKEN-ROTATION
```

Use normal repository tools:

```bash
grep -R "AUTH-SESSION-ROTATION" .
```

Then update code comments and ledger entries together.

## Requirement Semantic Replacement

Semantic changes should create or reference a new requirement instead of silently renaming old traces.

If `AUTH-SESSION-ROTATION` becomes device-bound rotation, create or reference a new requirement such as:

```txt
AUTH-DEVICE-BOUND-ROTATION
```

Do not bulk-rename old traces unless the meaning is preserved.

## File Rename or Move

File moves do not require rewriting code comments because `@file` remains literal.

Before move:

```txt
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/rotation.js
```

After move:

```txt
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/tokens/rotation.js
```

The code comment remains:

```js
// @reqtrace AUTH-SESSION-ROTATION/002/@file
```

Only the resolved ledger entry needs to be regenerated or updated.

## Generated Files

Generated files should be ignored. Put traces in source files or tests that humans maintain.

Common ignored paths:

```txt
.git/
node_modules/
dist/
build/
coverage/
.venv/
```

## Tests and Source Files

Tests and source files use the same hook. Their role is inferred from the path.

```txt
examples/refresh-token/src/rotation.js        implementation evidence
examples/refresh-token/tests/rotation.test.js verification evidence
```

## Ledger Maintenance

The docs ledger can be append-only or regenerated, as long as it contains validated expanded traces.

Append-only ledgers are useful for review history. Regenerated ledgers are useful after file moves.

## Missing Trace Review

If a pull request changes behavior but not traces, a reviewer should ask whether a trace is missing.

A missing trace does not always mean the PR is wrong. It means the PR should explicitly decide whether the changed behavior is relevant to an existing requirement handle.
