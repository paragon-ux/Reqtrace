# Rules

1. Requirements are named outside the codebase trace comments.
2. A Reqtrace handle never defines a requirement.
3. The ordinal is an implementation ordinal, not a sub-requirement.
4. `@file` must remain literal in code comments.
5. Documentation ledgers must contain resolved traces, not `@file`.
6. Every implementation pass must end with a grep pass.
7. Every valid trace must be appended to the requirement's trace ledger.
8. Invalid traces must be removed or fixed.
9. Requirement renames are allowed only when meaning is preserved.
10. Semantic changes should create or reference a new requirement, not silently rename old traces.
11. File moves do not require rewriting code comments; they require regenerating or updating resolved ledger entries.
12. No server, daemon, database, or graph resolver is required.
