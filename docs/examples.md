# Examples

## Refresh Token (full walkthrough)

`examples/refresh-token/` is a complete worked example: two source files, one
test file, and a `docs/requirements.md` with a rendered ledger block. It shows
the full generate → render → check workflow for a single handle.

## Calibration Fixtures

`examples/calibration/` contains seven self-contained mini-projects. Each
proves one specific claim about Reqtrace's behaviour. Run them all at once:

```bash
python examples/calibration/run.py
```

Expected output on a correctly installed v2.1:

```
Reqtrace v2.1 calibration
=========================
01-full-coverage           PASS
02-partial-impl-only       PASS
03-strict-full-vs-ledger   PASS
04-doc-hierarchy-violation PASS
05-multi-handle-evidence   PASS
06-scan-diff               PASS
07-legacy-migration        PASS

7 scenarios: 7 passed, 0 failed
```

| Scenario | Claim proved |
|---|---|
| `01-full-coverage` | A handle with implementation + verification evidence lands in the `full` bucket |
| `02-partial-impl-only` | A handle with only implementation evidence lands in `partial`, not `full` |
| `03-strict-full-vs-ledger` | `--strict=ledger` and `--strict=full` produce different results on an `unknown`-type handle |
| `04-doc-hierarchy-violation` | `E_OFFLEAF_HANDLE` fires when an implementation annotation's prefix is not the hierarchy leaf |
| `05-multi-handle-evidence` | `E_MULTI_HANDLE_EVIDENCE` fires when consecutive implementation annotations name different handles |
| `06-scan-diff` | `scan --diff` shows only annotations absent from the committed ledger |
| `07-legacy-migration` | `migrate` rewrites V1 annotations to V2 form and the result passes `check` |
