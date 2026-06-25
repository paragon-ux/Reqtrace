---
name: codex-pr-review-branch
description: Use for code reviews, bug triage handoffs, review-to-implementation prompts, or repository changes. Produces compact candidate-bug ledgers for Codex, never defers lower-severity bugs before Codex triage, and requires implementation on a feature branch with a pull request.
---

# Codex PR Review Branch

## Core rule

Every code review must be **compact, complete, and handed to Codex for final triage**.

Sonnet/Claude/other reviewers may identify candidate bugs and provisional severity, but they must not discard or defer candidate bugs based on severity. Codex receives the full candidate-bug ledger and is responsible for final validation, severity, implementation priority, and PR execution.

The review must end with a Codex-ready prompt that creates or uses a feature branch and opens a PR.

## When to use

Use this skill for:

- reviewing code, commits, diffs, branches, PRs, or release candidates;
- converting review feedback into Codex implementation work;
- fixing review findings;
- auditing a branch before tagging or release;
- preparing a PR from review findings.

## Non-negotiables

1. Never commit directly to `main`, `master`, `trunk`, `release`, or a protected branch.
2. Before edits, inspect branch and working tree.
3. If the working tree has uncommitted user changes, stop before editing.
4. Every candidate bug must appear exactly once in the candidate-bug ledger.
5. No candidate bug may be deferred by Sonnet/Claude/Max because it is P2/P3/medium/low.
6. All candidate bugs must be sent to Codex for final triage.
7. Codex may close a candidate only by marking it fixed, not reproducible, duplicate, intentional behavior, or out of scope with evidence.
8. Avoid repeated context. The review ledger gets short evidence and fix hints; the Codex prompt references IDs.
9. One coherent implementation attempt = one feature branch and one PR.
10. If remote auth, GitHub CLI, or permissions are unavailable, still provide exact PR commands.

## Required preflight before editing

```bash
git status --short
git branch --show-current
git remote -v
```

If on a protected branch:

```bash
git switch -c <branch-name>
```

Branch naming:

- `fix/<topic>`
- `feature/<topic>`
- `docs/<topic>`
- `chore/<topic>`

Examples:

```bash
git switch -c fix/reqtrace-v2-1-5-bug-triage
git switch -c feature/agent-query-api
git switch -c docs/delegation-adr
```

## Priority labels

Use priority labels only as **reviewer-provisional severity**, not as scope gates.

| Priority | Meaning |
|---|---|
| P0 | Candidate release-blocking correctness/security/data/CI bug |
| P1 | Candidate merge-blocking trust or validation bug |
| P2 | Candidate real bug or edge case |
| P3 | Candidate cleanup, polish, performance, maintainability, or weak-signal bug |

P2/P3 findings are still candidate bugs. They go to Codex. Do not move them to a deferred section before Codex triage.

## Compact review format

Use this exact structure:

```markdown
# Code Review

## Verdict

GREENLIGHT | YELLOWLIGHT | REDLIGHT

## Release risk

One paragraph, max 4 sentences. Mention only the highest-risk reason.

## Candidate-bug ledger

| ID | Reviewer pri | Candidate bug | Evidence | Suggested fix |
|---|---|---|---|---|
| F1 | P0 | <short bug> | <file:line or source> | <short fix> |
| F2 | P1 | <short bug> | <file:line or source> | <short fix> |
| F3 | P3 | <short bug> | <file:line or source> | <short fix> |

## Codex handoff scope

- Branch: `<branch-name>`
- Send all findings to Codex: F1, F2, F3, ...
- No findings deferred by this review.
- Codex must validate and triage each finding before implementation.

## Verification

```bash
<commands>
```

## Codex triage + implementation prompt

```text
<compact Codex prompt>
```
```

If there are no findings, still include a Codex prompt for branch-safe verification and PR preparation.

## Candidate-bug ledger rules

The ledger is the source of truth.

- Each candidate gets an ID: `F1`, `F2`, `F3`.
- The Codex prompt must reference IDs instead of repeating full explanations.
- Evidence should be compact: `scripts/reqtrace.py:717`, `tests/test_x.py`, or `review note`.
- Do not create separate "deferred" sections.
- Do not omit lower-severity findings.
- Do not call a candidate "non-bug" unless the review has direct evidence. Otherwise send it to Codex.

## Codex prompt template

Use this compact prompt. Do not repeat all review prose.

```text
You are Codex working in this repository.

Goal:
Independently validate, triage, and fix the candidate bugs from the review.

Branch:
Create or use branch: <branch-name>. Do not work on main/master/trunk/release.

Rules:
- Inspect the code before accepting any finding as real.
- Triage every finding ID: F1, F2, F3, ...
- Do not defer a confirmed bug merely because it is lower severity.
- For each finding, classify it as exactly one of:
  - fixed
  - not-reproducible
  - duplicate
  - intentional-behavior
  - out-of-scope
- If a finding is not fixed, provide code-based evidence for the classification.
- Preserve public behavior not explicitly changed.
- Add or update tests for every fixed behavior.
- Keep changes focused on these findings.
- Open a PR or provide exact PR commands if you cannot open one.

Files:
- <file>
- <file>

Candidate findings:
- F1 — <short candidate bug + evidence + suggested fix>
- F2 — <short candidate bug + evidence + suggested fix>
- F3 — <short candidate bug + evidence + suggested fix>

Implementation:
1. Reproduce or inspect each finding.
2. Fix all confirmed bugs.
3. Add regression tests.
4. Run verification.
5. Produce a PR summary with final status for every finding ID.

Verification:
<commands>

PR:
Title: <title>
Body:
## Summary
- <bullets>

## Finding status
- F1: fixed / not-reproducible / duplicate / intentional-behavior / out-of-scope — <evidence>
- F2: fixed / not-reproducible / duplicate / intentional-behavior / out-of-scope — <evidence>
- F3: fixed / not-reproducible / duplicate / intentional-behavior / out-of-scope — <evidence>

## Verification
- <commands/results>
```

## Implementation workflow

When implementing:

1. Run preflight.
2. Create or switch to the named branch.
3. Validate every candidate finding.
4. Fix all confirmed bugs.
5. Add/update tests for every fixed behavior.
6. Run verification.
7. Commit if requested.
8. Push branch and open PR if possible.
9. If PR creation is unavailable, output exact commands.

Preferred commands:

```bash
git switch -c <branch-name>
git add <paths>
git commit -m "<type>: <message>"
git push -u origin <branch-name>
gh pr create --title "<title>" --body "<body>"
```

Do not run destructive commands such as `git reset --hard`, `git clean -fd`, force-push, or branch deletion unless explicitly requested after repository state is inspected.

## PR body minimum

```markdown
## Summary
- <change>
- <change>

## Verification
- [ ] <command/result>
- [ ] <command/result>

## Finding status
- F1: <status> — <evidence>
- F2: <status> — <evidence>
- F3: <status> — <evidence>
```

Every finding ID from the candidate-bug ledger must appear in the PR body.

## Reqtrace verification defaults

For Reqtrace work, prefer:

```bash
python -m pytest tests/ -v
python scripts/reqtrace.py generate
python scripts/reqtrace.py check --strict
python scripts/reqtrace.py check --strict --format json
python scripts/reqtrace.py scan --format json
python scripts/reqtrace.py report --format json
```

## Downstream boundary

If an item may belong downstream rather than core, still send it to Codex for triage. Do not pre-defer it.

Examples:

| Item | Codex triage instruction |
|---|---|
| Grep proxy | Decide whether current branch should fix docs/delegation only or implement scheduled core behavior |
| HTML report | Decide whether JSON renderer belongs downstream or current scope |
| Blame/provenance | Decide whether current code has a bug or only a future feature request |
| Collaborative editing | Classify as downstream/out-of-scope only with evidence |
| Presets | Classify as docs/delegation unless explicitly scheduled |

## Final self-check

Before responding, confirm:

- Review is compact.
- Every candidate bug appears once in the ledger.
- No lower-severity bug was deferred by the reviewer.
- Codex prompt includes every finding ID.
- Codex is instructed to triage every finding.
- Branch name is present.
- PR title/body or PR commands are present.
- No direct-to-main workflow is suggested.
