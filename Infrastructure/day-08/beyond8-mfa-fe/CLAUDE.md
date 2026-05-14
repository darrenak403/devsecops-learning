# CLAUDE

## Priority and Scope

- This file defines agent behavior for this repository.
- **Priority order:** Project Rules > General Guidelines.
- If rules conflict, follow project-specific rules in this file.

## Project Rules (Non-Negotiable)

### Core Principles

YAGNI · KISS · DRY · Brutal honesty over diplomacy · Challenge every assumption

### Delivery Guardrails

1. **Plan fidelity**
   - Implement only what the approved plan describes.
   - Do not change API contracts, response shapes, or migration strategy unless explicitly approved.
   - If deviation is needed, stop and ask first.

2. **Todo discipline**
   - Reuse existing todos; do not duplicate.
   - Keep exactly one todo in `in_progress`.
   - Mark `completed` only with verification evidence.

3. **Backward compatibility by default**
   - Preserve existing behavior unless user approves a breaking change.
   - If optimization conflicts with compatibility, keep compatibility and propose phased migration.

4. **Verification before completion**
   - Run relevant lint/tests for changed scope before claiming done.
   - Report exact commands and outcomes.
   - If verification cannot run, state why and provide manual commands.

5. **No hidden scope expansion**
   - Keep edits minimal and directly tied to request/plan.
   - Surface unexpected issues; do not silently refactor unrelated areas.

### Frontend Implementation Patterns

- **Client-only API safety:** guard `window`, clipboard, OCR, and browser APIs.
- **Progressive enhancement:** every convenience path has a fallback path.
- **State locality:** keep transient UI state near components; lift only when reused.
- **Typed input boundaries:** normalize/validate before parser or renderer calls.
- **Bundle control:** lazy-load heavy client libraries where possible.
- **Format compatibility:** preserve markdown/question format contracts unless requested.
- **User-flow validation:** verify changed UI by lint/type-check + quick path test.

## `.claude` Conventions

### Structure

```
.claude/
  agents/
  commands/
  skills/
  rules/
  hooks/
```

### Path-Scoped Rules

| File | Activates for |
|------|---------------|
| `.claude/rules/agents.md` | `.claude/agents/**` |
| `.claude/rules/commands.md` | `.claude/commands/**` |
| `.claude/rules/skills.md` | `.claude/skills/**` |

### Personal Override

`CLAUDE.local.md` (gitignored) is allowed for personal, non-committed preferences.

## General Coding Guidelines

Use these when project rules do not provide stricter constraints.

### 1) Think Before Coding

- State assumptions explicitly.
- If multiple interpretations exist, clarify before implementation.
- Prefer simpler solutions and call out tradeoffs.
- Stop and ask when requirements are ambiguous.

### 2) Simplicity First

- Implement the minimum that solves the request.
- No speculative abstraction/configuration.
- No unrelated defensive code for impossible paths.

### 3) Surgical Changes

- Touch only what the task requires.
- Match existing style and architecture.
- Remove only dead code created by your own edits.

### 4) Goal-Driven Execution

- Convert requests into verifiable outcomes.
- For multi-step work, state brief step + verification pairs.
- Do not claim completion without evidence.

---

**Quality signal:** good outcomes mean smaller diffs, fewer rewrites, and explicit verification.

## Tooling Reference

- GitNexus operational policy is centralized in `AGENTS.md` (single source of truth; avoid duplication here).

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **beyond8-mfa-fe** (978 symbols, 1505 relationships, 30 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/beyond8-mfa-fe/context` | Codebase overview, check index freshness |
| `gitnexus://repo/beyond8-mfa-fe/clusters` | All functional areas |
| `gitnexus://repo/beyond8-mfa-fe/processes` | All execution flows |
| `gitnexus://repo/beyond8-mfa-fe/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
