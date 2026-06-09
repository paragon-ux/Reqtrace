# Concept

Wiki links and graph servers can create maintenance surfaces. Reverse indexes can become extra state that must be generated, hosted, updated, and trusted.

Reqtrace uses a reserved pattern already searchable by normal repository tools. The codebase carries a fresh self-reference to implementation ordinals, while the requirement document remains the source of truth.

A Reqtrace handle is a structural reference, not a hyperlink:

```txt
@reqtrace AUTH-SESSION-ROTATION/001/@file
```

The handle says:

```txt
requirement = AUTH-SESSION-ROTATION
ordinal = 001
location = this file
```

The file path returned by grep supplies the occurrence location. That means the repository itself provides the lookup mechanism.

Pull request agents can validate by grep without custom commands. Optional scripts can prove that the ledger matches the code comments, but the core convention does not depend on a server, daemon, database, or generated graph.

## Why It Is Not a Requirement System

Reqtrace does not create requirements. It only traces implementation evidence back to an existing requirement handle.

The ordinal is not a sub-requirement. It is an implementation ordinal: a numbered occurrence of validated implementation or test evidence under the requirement.
