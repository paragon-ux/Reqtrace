# Reqtrace

Reqtrace is a minimal convention for tracing implementation evidence back to an existing requirement.

The existing requirement remains the source of truth. Code comments contain only structural trace handles. Grep resolves backwards references from code to requirement handles. The documentation ledger stores validated expanded handles after implementation work has been checked.

Reqtrace is deliberately small: requirement handle, implementation ordinal, `@file`, grep, and a docs ledger.
