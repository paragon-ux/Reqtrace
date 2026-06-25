# Calibration Fixtures

These directories are CLI behavior-testing fixtures. They intentionally use the smallest files that exercise scanner, ledger, report, strictness, hierarchy, diff, and migration behavior.

They are not production annotation style guides. Real code should keep explanatory comments for intent, invariants, security assumptions, or maintenance hazards alongside any `@reqtrace` markers.

`01-full-coverage` is a full-coverage scanner/report/check fixture. Its stub functions exist only to prove that one handle can have both implementation and verification evidence.
