---
name: phase1-elaboration-guide
description: Detailed workflow for Phase 1 Mob Elaboration — structured question rounds to transform a business idea into a validated requirements document with user stories and acceptance criteria
---

# Phase 1: Mob Elaboration — Detailed Guide

## Entry Conditions

- User has provided a seed: idea, problem statement, feature request, or ticket
- No validated requirements document exists yet

## Opening Statement (present to mob)

```
Starting Phase 1: Mob Elaboration.

Goal: transform your idea into a validated requirements document before any code is written.

I will ask questions in rounds — max 5 per round. Answer as completely or briefly as you like.
The mob should review and discuss each round together before responding.

Round 1 begins now.
```

---

## Round 1 — Domain Understanding

Ask 3–5 of these (select based on what the seed already answered):

1. "What problem does this solve, and for whom?"
2. "Who are the primary users? Describe their day before and after this exists."
3. "What does success look like 6 months after launch? Give a concrete metric if possible."
4. "What triggered this project — a specific pain point, a missed opportunity, or a compliance need?"
5. "Are there existing solutions your users use today? What do they dislike about them?"

Wait for full answers before proceeding to Round 2.

---

## Round 2 — Scope and Constraints

Ask 3–5 of these:

1. "What is explicitly out of scope for this first phase or release?"
2. "What constraints exist? (regulatory, team size, timeline, budget, existing tech)"
3. "What other systems or services must this interact with?"
4. "What are your non-negotiable quality requirements? (uptime, response time, security level, compliance)"
5. "Is there an MVP definition — the smallest version that still delivers value?"

Wait for full answers before proceeding to Round 3.

---

## Round 3 — User Story Proposal

Based on rounds 1–2, synthesise 3–7 user stories. Present them together:

```
Based on what you've told me, here are the user stories I've identified:

Story 1: As a [role], I want to [goal] so that [reason].
Story 2: As a [role], I want to [goal] so that [reason].
...

For each story, tell me:
  (A) Confirmed — captures the need correctly
  (B) Modified — the need is right but wording or scope is off (describe the change)
  (C) Rejected — this is not a real need
  (D) Missing — add a story I haven't captured
```

Revise stories based on feedback. Repeat until mob marks all stories as (A).

### User story rules

- Format: "As a [role], I want to [goal] so that [reason]"
- One story per discrete user need — never bundle two needs into one story
- No implementation language — describe WHAT, not HOW
- Stories must be independently testable

---

## Round 4 — Acceptance Criteria

For each confirmed story, propose 3–5 acceptance criteria:

```
Story 1: [title]
Proposed criteria:
  - Given [precondition], When [action], Then [outcome]  ← happy path
  - Given [precondition], When [invalid action], Then [error outcome]  ← failure path
  - Given [precondition], When [edge case], Then [outcome]  ← edge case

Mark each: (A) Confirmed / (B) Modified / (C) Rejected / (D) Add more
```

Repeat for all confirmed stories.

### Acceptance criteria rules

- Format: Given / When / Then — no exceptions
- Each criterion must be unambiguous and verifiable by a tester
- Always include at least one failure path per story
- No implementation details — describe observable outcomes only

---

## Handling Uncertainty

When mob cannot answer a question:
1. State the assumption explicitly: "I'll assume [X]. Is that reasonable?"
2. If confirmed: record assumption in the Assumptions section of the document
3. If uncertain: record as an Open Question — do NOT block progress

Assumptions are risks. Flag high-risk assumptions clearly.

---

## Phase 1 Validation Checkpoint

After all 4 files are written and confirmed individually, do a final check:

```
All 4 requirement files are complete:
  ✓ docs/requirements/01-vision.md
  ✓ docs/requirements/02-scope.md
  ✓ docs/requirements/03-user-stories.md
  ✓ docs/requirements/04-constraints.md

Before advancing to Phase 2:
1. Does each file fully represent what you want to build?
2. Are any user stories missing or misrepresented?
3. Are there open questions in 04-constraints.md that block architecture decisions?

Confirm when ready to proceed to Phase 2.
```

Only advance on explicit confirmation ("confirmed", "looks good", "proceed", etc.).

---

## Question Bank by Category

Use these when the standard rounds need supplementing:

**Vision**
- "If this project is a success, what headline would describe it?"
- "What business goal does this support? (revenue, retention, compliance, efficiency)"

**Actor / User**
- "Are there admin or internal users in addition to end users?"
- "Who has read access vs write access?"
- "Are there guest/anonymous users?"

**Scope**
- "Is this a greenfield system or an addition to an existing one?"
- "Will this replace something currently done manually or by another tool?"

**Constraint**
- "Is there a hard deadline? Why?"
- "Are there data residency or privacy requirements?"

**Integration**
- "Does data flow in, out, or both directions with external systems?"
- "Are integrations synchronous (API calls) or async (events/queues)?"

**Risk**
- "What assumptions, if wrong, would invalidate the entire approach?"
- "What has been tried before and failed? Why?"

---

## Output File Mapping

| Round | Write to |
|-------|----------|
| Round 1 — domain | `docs/requirements/01-vision.md` |
| Round 2 — scope | `docs/requirements/02-scope.md` |
| Round 3+4 — stories + AC | `docs/requirements/03-user-stories.md` |
| Constraints + sign-off | `docs/requirements/04-constraints.md` |

Write each file immediately after its round is confirmed. Do not batch writes.
