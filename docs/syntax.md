# Syntax

Unresolved code handle:

```txt
@reqtrace <REQUIREMENT>/<ORDINAL>/@file
```

Resolved documentation trace:

```txt
<REQUIREMENT>/<ORDINAL>/<repo-relative-file-path>
```

Grammar:

```txt
REQUIREMENT = uppercase words separated by hyphens
ORDINAL = three digits, starting at 001
@file = literal placeholder meaning "this file"
```

Example:

```js
// @reqtrace AUTH-SESSION-ROTATION/001/@file
```

Resolved:

```txt
AUTH-SESSION-ROTATION/001/examples/refresh-token/src/validation.js
```
