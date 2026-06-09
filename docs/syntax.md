# Syntax

Reqtrace has one code marker and one resolved ledger form.

## Unresolved Code Handle

Code comments use this form:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

Example:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

The requirement handle must come from an existing upstream requirement source. The code comment does not define the requirement.

## Resolved Documentation Trace

Documentation ledgers use the expanded form:

```txt
<REQUIREMENT>/<ORDINAL>/<repo-relative-file-path>
```

Example resolved trace:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Grammar

```txt
REQUIREMENT = upstream requirement handle, commonly uppercase words separated by hyphens
ORDINAL     = three digits, starting at 001
@file       = literal placeholder meaning "this file"
```

Recommended regex:

```regex
@reqtrace\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\/([0-9]{3})\/@file
```

## Expansion Rule

`@file` must remain literal in code comments. It is expanded only when the trace is resolved.

If this comment appears in `examples/refresh-token/src/validation.js`:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

then the resolved trace is:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```

## Search Levels

Search the whole requirement family:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTATION" .
```

Search one implementation ordinal:

```bash
grep -R "@reqtrace AUTH-SESSION-ROTATION/003" .
```

Search all Reqtrace handles:

```bash
grep -R "@reqtrace" .
```
