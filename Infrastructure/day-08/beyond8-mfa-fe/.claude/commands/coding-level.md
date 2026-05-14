---
name: coding-level
description: Set Claude's coding explanation level for this session/project (0=ELI5 → 5=God Mode)
---

Set the coding explanation depth. Levels 0–5 control how much context, rationale, and explanation Claude adds.

## Levels

| # | Name | Style |
|---|------|-------|
| 0 | ELI5 | No assumed knowledge — analogies, step-by-step, everything explained |
| 1 | Junior | Explains WHY, mentor tone, encourages learning |
| 2 | Mid-level | Design patterns, brief trade-off notes |
| 3 | Senior | Trade-offs and architecture first, no syntax hand-holding |
| 4 | Tech Lead | Risk analysis, business impact, team/ops implications |
| 5 | God Mode | Zero hand-holding, code-first, terse — default |

## Usage

```
/coding-level          # show current level + interactive menu
/coding-level 3        # set directly
/coding-level reset    # remove config (back to God Mode default)
```

## How to execute this command

Read the argument `$ARGUMENTS`:

**No argument** — show the current level (read `.claude/coding-level.json` if it exists, else level 5) and print the level table above. Ask the user to pick a number 0–5.

**Argument is a number 0–5** — write `.ck.json` at the project root:
```json
{ "codingLevel": <N> }
```
Confirm with one line: `Coding level set to <N> (<Name>). Takes effect next session.`

**Argument is `reset`** — delete `.ck.json` if it exists. Confirm: `Coding level reset to default (5 — God Mode).`

**Argument is anything else** — print usage and the level table.

The file lives at the project root as `.ck.json`. Do NOT write to `~/.claude/` or `.claude/`.
