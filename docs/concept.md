# Concept

Wiki links and graph servers can create maintenance surfaces. Reverse indexes can become extra state that must be generated, hosted, updated, and trusted.

Reqtrace uses a reserved pattern already searchable by normal repository tools. Code comments carry structural trace handles, while the requirement remains defined by the upstream requirement source.

A Reqtrace handle is a structural reference, not a hyperlink:

```txt
@reqtrace AUTH-SESSION-ROTATION/001/@file
```

The handle says:

```txt
requirement handle = AUTH-SESSION-ROTATION
implementation ordinal = 001
location = this file
```

The file path returned by grep supplies the occurrence location. The repository itself provides the lookup mechanism.

## Boundary

Reqtrace is not a requirement system. It does not create requirements, decide whether a requirement should be renamed, or decide whether a requirement has changed meaning.

Reqtrace begins when an upstream process has already supplied a requirement handle. It only records implementation or test evidence against that handle.

## Why This Is Useful

A pull request agent, coding agent, or human reviewer can use one grep pattern to find all traces for a requirement family:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTATION" .
```

Optional scripts can prove that the trace ledger matches the code comments, but the core convention does not depend on a server, daemon, database, or generated graph.
