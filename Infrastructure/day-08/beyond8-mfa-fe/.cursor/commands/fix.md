---
description: Analyze and fix a bug quickly
---

Fix the issue described below with a minimal, safe patch.

Issue details:
$ARGUMENTS

Execution requirements:
- Reproduce or reason about root cause first.
- Apply the smallest change that resolves the bug.
- Preserve existing behavior outside the bug scope.
- Run relevant lint/tests for changed files when possible.
- Return: root cause, changed files, and verification steps.
