# Edge Cases

## Multiple Ordinals In The Same File

A file can contain multiple implementation occurrences for the same requirement when each occurrence has a distinct ordinal.

## Same Ordinal Repeated In The Same File

Repeating the same ordinal in the same file is usually accidental. Keep one trace near the strongest implementation evidence or assign distinct ordinals when there are truly separate occurrences.

## Same Ordinal Repeated Across Different Files

Repeating the same ordinal across different files creates ambiguous implementation evidence. Use a unique ordinal for each validated occurrence.

## Requirement Rename

Requirement renames are allowed only when the meaning is preserved. Update code comments and ledger entries together.

## Requirement Semantic Replacement

Semantic changes should create or reference a new requirement instead of silently renaming old traces.

## File Rename Or Move

File moves do not require rewriting code comments because `@file` remains literal. They do require regenerating or updating resolved ledger entries.

## Generated Files

Generated files should be ignored. Put traces in source files or tests that humans maintain.

## Tests And Source Files

Tests and source files use the same hook. Their role is inferred from the path.

## Ledger Maintenance

The docs ledger can be append-only or regenerated, as long as it contains validated expanded traces.

## Missing Trace Review

If a pull request changes behavior but not traces, a reviewer should ask whether a trace is missing.
