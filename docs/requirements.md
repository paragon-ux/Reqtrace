# AUTH-SESSION-ROTATION

A successful refresh-token exchange must rotate the refresh token and prevent reuse of the old token.

This requirement is the source of truth for the demo. The entries below are generated implementation traces, not requirement definitions.

## Trace Ledger

<!-- reqtrace:ledger:start handle=AUTH-SESSION-ROTATION -->
- AUTH-SESSION-ROTATION/25ab/examples/refresh-token/src/revocation.js:2
- AUTH-SESSION-ROTATION/51de/examples/refresh-token/src/rotation.js:2
- AUTH-SESSION-ROTATION/fb2d/examples/refresh-token/src/validation.js:2
- AUTH-SESSION-ROTATION/79ac/examples/refresh-token/tests/rotation.test.js:8
<!-- reqtrace:ledger:end -->
