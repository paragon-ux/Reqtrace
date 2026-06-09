# Rules

Reqtrace rules are mechanical. They govern trace handles and ledgers, not the requirement process.

1. A requirement handle must already exist upstream.
2. A Reqtrace handle never defines, rewrites, splits, supersedes, or interprets a requirement.
3. The ordinal is an implementation ordinal, not a sub-requirement.
4. `@file` must remain literal in code comments.
5. Documentation ledgers must contain resolved traces, not `@file`.
6. Every implementation pass with Reqtrace handles must end with a grep pass.
7. Every valid trace must be appended to the requirement's trace ledger.
8. Invalid traces must be removed or fixed.
9. If an upstream requirement handle changes, update unresolved code handles and resolved ledger entries together.
10. Role is inferred from file path and surrounding code; do not add separate hooks such as `@implements` or `@verifies`.
11. File moves do not require rewriting code comments; they require regenerating or updating resolved ledger entries.
12. No server, daemon, database, or graph resolver is required.

## Ordinal Rules

An ordinal identifies one validated implementation occurrence under a requirement handle.

Good:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/002/examples/refresh-token/src/rotation.js
AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
```

Suspicious or invalid:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/rotation.js
```

If two files provide different evidence, give them different ordinals.

## Role Inference

Reqtrace uses one hook: `@reqtrace`.

It does not need separate hooks like `@implements`, `@verifies`, or `@supports`. Role is inferred from the file path and surrounding code:

```txt
src/**         implementation evidence
tests/**       verification evidence
docs/**        documentation evidence
migrations/**  migration evidence
```

## Ledger Rule

The ledger is the mandatory second stage. A code comment is only an unresolved trace. The ledger contains validated expanded traces.
