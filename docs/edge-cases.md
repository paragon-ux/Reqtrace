# Edge Cases

This page shows how to classify Reqtrace handles without using a custom resolver.

Reqtrace does **not** define, rewrite, split, supersede, or interpret requirements. The requirement source remains upstream: a spec, ticket, PRD, documentation page, issue, or SDD artifact. This page only describes how Reqtrace handles should appear in code and how resolved traces should appear in a trace ledger.

A Reqtrace handle in code is always unresolved:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

A trace ledger entry in documentation is always resolved:

```txt
<REQUIREMENT>/<ORDINAL>/<repo-relative-file-path>
```

## Multiple Ordinals in the Same File

A file can contain multiple Reqtrace handles for the same requirement when each handle identifies a different implementation occurrence.

**Incorrect**

Using the same ordinal twice in one file creates a duplicate resolved trace:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenOwnership(token, userId) {}
```

Both comments resolve to the same ledger entry:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

**Correct**

Use distinct ordinals for distinct implementation occurrences:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/002/@file
function validateRefreshTokenOwnership(token, userId) {}
```

Resolved ledger entries:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/validation.js
```

The file path is the same, but the ordinals are different.

## Same Ordinal Repeated Across Different Files

The same requirement and ordinal should not normally appear in different files. That makes one ordinal point to competing implementation evidence.

**Incorrect**

```txt
examples/refresh-token/src/validation.js: // @reqtrace AUTH-SESSION-ROTATION/001/@file
examples/refresh-token/src/rotation.js:   // @reqtrace AUTH-SESSION-ROTATION/001/@file
```

These produce competing resolved traces for the same ordinal:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/rotation.js
```

**Correct**

Assign each validated occurrence its own ordinal:

```txt
examples/refresh-token/src/validation.js: // @reqtrace AUTH-SESSION-ROTATION/001/@file
examples/refresh-token/src/rotation.js:   // @reqtrace AUTH-SESSION-ROTATION/002/@file
```

Resolved ledger entries:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/rotation.js
```

## Hardcoding the File Path in Code

The code comment must keep `@file` literal. The current file path supplies the expanded location during grep, review, or validation.

**Incorrect**

```js
// @reqtrace AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

This creates path drift when the file is renamed or moved.

**Correct**

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Then the trace ledger stores the resolved form:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Leaving `@file` in the Documentation Ledger

Documentation ledgers must contain validated expanded traces, not unresolved code handles.

**Incorrect**

```md
## Trace Ledger

- AUTH-SESSION-ROTATION/001/@file
```

**Correct**

```md
## Trace Ledger

- AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Upstream Requirement Handle Changes

If the upstream requirement source changes a requirement handle, update unresolved code handles and resolved ledger entries together. Reqtrace does not decide whether the handle change is valid; it only keeps traces mechanically consistent with the upstream handle.

**Incorrect**

Only updating code comments and leaving the ledger stale:

```txt
Code:   @reqtrace AUTH-REFRESH-TOKEN-ROTATION/001/@file
Ledger: AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

**Correct**

Update unresolved code handles and resolved ledger entries together:

```txt
Code:   @reqtrace AUTH-REFRESH-TOKEN-ROTATION/001/@file
Ledger: AUTH-REFRESH-TOKEN-ROTATION/001/examples/refresh-token/src/validation.js
```

Useful review commands:

```bash
grep -R "AUTH-SESSION-ROTATION" .
grep -R "AUTH-REFRESH-TOKEN-ROTATION" .
```

## Requirement Meaning Questions

Reqtrace should not hide uncertainty about requirement meaning. If a code change appears to depend on a new, changed, or different requirement, the upstream requirement process must provide the handle to use.

**Incorrect**

A trace handle is rewritten to a different requirement name without an upstream requirement handle or review decision:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

silently becomes:

```txt
AUTH-DEVICE-BOUND-ROTATION/001/examples/refresh-token/src/validation.js
```

**Correct**

Keep Reqtrace mechanical. Use the requirement handle supplied by the upstream requirement source or PR review:

```txt
Upstream handle: AUTH-DEVICE-BOUND-ROTATION
Code:            @reqtrace AUTH-DEVICE-BOUND-ROTATION/001/@file
Ledger:          AUTH-DEVICE-BOUND-ROTATION/001/examples/refresh-token/src/device-binding.js
```

Reqtrace records implementation evidence against the chosen handle. It does not choose the handle.

## File Rename or Move

File moves do not require rewriting code comments because `@file` remains literal. They do require updating the resolved ledger.

**Incorrect**

The file moved to `examples/refresh-token/src/tokens/rotation.js`, but the ledger still says:

```txt
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/rotation.js
```

**Correct**

Code comment remains unchanged:

```js
// @reqtrace AUTH-SESSION-ROTATION/002/@file
```

Ledger entry is regenerated or updated:

```txt
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/tokens/rotation.js
```

## Generated Files

Generated files should not carry Reqtrace handles. Put traces in human-maintained source files or tests.

**Incorrect**

```txt
dist/rotation.bundle.js: // @reqtrace AUTH-SESSION-ROTATION/002/@file
coverage/report.js:     // @reqtrace AUTH-SESSION-ROTATION/004/@file
```

**Correct**

```txt
examples/refresh-token/src/rotation.js:        // @reqtrace AUTH-SESSION-ROTATION/002/@file
examples/refresh-token/tests/rotation.test.js: // @reqtrace AUTH-SESSION-ROTATION/004/@file
```

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

Reqtrace uses one hook. Do not add separate hook names for implementation, verification, or support. Role is inferred from the path and surrounding code.

**Incorrect**

```js
// @implements AUTH-SESSION-ROTATION/002/@file
```

```js
// @verifies AUTH-SESSION-ROTATION/004/@file
```

**Correct**

```js
// @reqtrace AUTH-SESSION-ROTATION/002/@file
```

```js
// @reqtrace AUTH-SESSION-ROTATION/004/@file
```

Role is inferred from paths such as:

```txt
examples/refresh-token/src/rotation.js         implementation evidence
examples/refresh-token/tests/rotation.test.js  verification evidence
```

## Ledger Maintenance

Every valid trace must be appended to the requirement's trace ledger, or the unresolved trace must be removed.

**Incorrect**

Code contains:

```js
// @reqtrace AUTH-SESSION-ROTATION/003/@file
```

but the requirement documentation has no resolved trace for it.

**Correct**

After validation, append the resolved trace:

```md
## Trace Ledger

- AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
```

Append-only ledgers are useful for review history. Regenerated ledgers are useful after file moves.

## Missing Trace Review

A behavior-changing pull request does not always need a new trace, but it should make the trace decision visible during review.

**Incorrect**

A pull request changes refresh-token behavior but does not add, update, remove, or discuss any `AUTH-SESSION-ROTATION` traces.

**Correct**

The pull request does one of these:

```txt
- adds a new @reqtrace handle and ledger entry
- updates an existing trace and ledger entry
- removes an invalid trace and ledger entry
- states that the change does not affect AUTH-SESSION-ROTATION trace evidence
```

## Ordinal Gaps

Ordinals do not need to prove a perfect historical sequence forever. They only need to identify validated implementation occurrences clearly.

**Acceptable**

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
```

This can happen after removing an invalid or obsolete trace.

**Avoid**

Renumbering unrelated traces just to close a gap. Renumbering creates unnecessary diff noise and can make review history harder to follow.
