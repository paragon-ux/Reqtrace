# Edge Cases

This page uses paired **Incorrect** and **Correct** examples so implementers and review agents can classify traces without needing a custom resolver.

A Reqtrace handle in code is always unresolved:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

A trace ledger entry in documentation is always resolved:

```txt
<REQUIREMENT>/<ORDINAL>/<repo-relative-file-path>
```

## Multiple Ordinals in the Same File

Multiple implementation ordinals may appear in the same file when they identify different implementation evidence.

**Correct**

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

The file path is the same, but the ordinals are different, so the occurrences remain distinct.

## Same Ordinal Repeated in the Same File

Repeating the same requirement and ordinal in the same file creates a duplicate resolved trace.

**Incorrect**

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenOwnership(token, userId) {}
```

Both comments resolve to the same ledger key:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

**Correct**

Use one trace near the strongest evidence:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshToken(token, userId) {
  validateRefreshTokenShape(token);
  validateRefreshTokenOwnership(token, userId);
}
```

Or use separate ordinals when they are separate implementation occurrences:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
function validateRefreshTokenShape(token) {}

// @reqtrace AUTH-SESSION-ROTATION/002/@file
function validateRefreshTokenOwnership(token, userId) {}
```

## Same Ordinal Repeated Across Different Files

The same requirement and ordinal should not normally appear in different files. That creates ambiguous implementation evidence for one ordinal.

**Incorrect**

```txt
examples/refresh-token/src/validation.js: // @reqtrace AUTH-SESSION-ROTATION/001/@file
examples/refresh-token/src/rotation.js:   // @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Resolved ledger entries would compete for the same ordinal:

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

The code comment must keep `@file` literal. The current file path supplies the expanded location.

**Incorrect**

```js
// @reqtrace AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

This creates path drift when the file is renamed or moved.

**Correct**

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Then the ledger stores the resolved form:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Leaving `@file` in the Documentation Ledger

Documentation ledgers must contain validated expanded traces, not unresolved code handles.

**Incorrect**

```md
## Trace ledger

- AUTH-SESSION-ROTATION/001/@file
```

**Correct**

```md
## Trace ledger

- AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Requirement Rename

A requirement rename is allowed only when the meaning is preserved.

**Correct**

A wording cleanup that preserves identity:

```txt
AUTH-SESSION-ROTATION -> AUTH-REFRESH-TOKEN-ROTATION
```

Update code comments and ledger entries together:

```bash
grep -R "AUTH-SESSION-ROTATION" .
```

Then replace the old handle with the new handle in both unresolved code comments and resolved ledger entries.

**Incorrect**

Do not use a rename to hide a semantic change:

```txt
AUTH-SESSION-ROTATION -> AUTH-DEVICE-BOUND-ROTATION
```

If device binding adds a new obligation, this is a replacement or split, not a safe rename.

## Requirement Semantic Replacement

When the meaning changes, create or reference a new requirement instead of silently rewriting old traces.

**Incorrect**

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

Silently changed to:

```txt
AUTH-DEVICE-BOUND-ROTATION/001/examples/refresh-token/src/validation.js
```

without creating or referencing the new requirement.

**Correct**

Keep the old requirement history understandable and trace the new requirement separately:

```md
# AUTH-SESSION-ROTATION

Status: superseded by AUTH-DEVICE-BOUND-ROTATION.
```

```md
# AUTH-DEVICE-BOUND-ROTATION

Successful refresh-token exchange must rotate the token and bind the replacement token to the device identity.

## Trace ledger

- AUTH-DEVICE-BOUND-ROTATION/001/examples/refresh-token/src/device-binding.js
```

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

Reqtrace uses one hook. Do not add separate hook names for implementation, verification, or support. Role is inferred from the file path and surrounding code.

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
examples/refresh-token/src/rotation.js        implementation evidence
examples/refresh-token/tests/rotation.test.js verification evidence
```

## Ledger Maintenance

Every valid trace must be appended to the requirement's trace ledger or the trace must be removed.

**Incorrect**

Code contains:

```js
// @reqtrace AUTH-SESSION-ROTATION/003/@file
```

but `docs/requirements.md` has no resolved trace for it.

**Correct**

After validation, append the resolved trace:

```md
## Trace ledger

- AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
```

Append-only ledgers are useful for review history. Regenerated ledgers are useful after file moves.

## Missing Trace Review

A behavior-changing pull request does not always need a new trace, but it must make the decision explicit during review.

**Incorrect**

A PR changes refresh-token reuse behavior but does not add, update, remove, or discuss any `AUTH-SESSION-ROTATION` traces.

**Correct**

The PR does one of these:

```txt
- adds a new @reqtrace handle and ledger entry
- updates an existing trace and ledger entry
- removes an invalid trace and ledger entry
- states that the change is not related to AUTH-SESSION-ROTATION
```

## Ordinal Gaps

Ordinals do not have to prove a perfect historical sequence forever. They only need to identify validated implementation occurrences clearly.

**Acceptable**

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
```

This can happen after removing an invalid or obsolete trace.

**Avoid**

Renumbering unrelated traces just to close a gap. Renumbering creates unnecessary diff noise and can make review history harder to follow.
