# AUTH-SESSION-ROTATION

A successful refresh-token exchange must rotate the refresh token and prevent reuse of the old token.

This requirement is the source of truth. The entries below are validated implementation traces, not requirement definitions.

## Trace Ledger

- AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
- AUTH-SESSION-ROTATION/002/examples/refresh-token/src/rotation.js
- AUTH-SESSION-ROTATION/003/examples/refresh-token/src/revocation.js
- AUTH-SESSION-ROTATION/004/examples/refresh-token/tests/rotation.test.js
