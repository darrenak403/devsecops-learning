---
name: phase2-construction-guide
description: Detailed workflow for Phase 2 Mob Construction — how to propose domain models, layer structure, integration flows, and ADRs from validated requirements, producing an architecture document
---

# Phase 2: Mob Construction — Detailed Guide

## Entry Conditions

- Phase 1 requirements document is complete and mob-confirmed
- OR: user explicitly skips Phase 1 with an existing validated requirements document

**Before starting:** read the completed requirements document in full. Never propose architecture without understanding the validated requirements.

## Opening Statement

Open by stating the goal: "Translate validated requirements into architectural decisions before writing code. I'll propose domain models, layers, integration flows, and record decisions as ADRs. Mob confirms each."

---

## Step 1 — Domain Model Proposal

Identify candidate entities from nouns in the user stories and requirements.

Present to mob:

```
From the requirements, I've identified these candidate domain entities:

- [Entity]: [one-line responsibility]
- [Entity]: [one-line responsibility]
...

Proposed aggregate boundaries:
- Aggregate [A] owns: [Entity1, Entity2] — because [reason]
- Aggregate [B] owns: [Entity3] — because [reason]

Questions:
1. Are any entities missing or incorrectly named?
2. Do the aggregate boundaries reflect how your business thinks about these concepts?
3. Are there entities here that are out of scope for this project?
```

Wait for mob response before proceeding.

### Domain modelling rules

- **Entities**: have identity (an ID), change over time, exist independently
- **Value objects**: no identity, defined by their attributes, immutable (e.g., Money, Address)
- **Aggregate root**: the only entry point to a cluster of related entities — external objects hold a reference only to the root
- **Domain service**: an operation that doesn't naturally belong to one entity (e.g., TransferFunds)
- Start with 3–8 entities; do not over-model in this phase

---

## Step 2 — Layer Structure Proposal

Propose a logical layer structure appropriate for the project type.

Present to mob:

```
Proposed layer structure:

  Domain layer      — entities, value objects, domain events, repository interfaces, domain services
  Application layer — use cases, DTOs, input validators, application services
  Infrastructure layer — repository implementations, ORM configs, external service adapters
  Host/API layer    — endpoint registration, middleware, dependency injection config

Dependency rule: outer layers depend on inner layers. Domain has no external dependencies.

Questions:
1. Does your team already follow an architectural style? If so, how does this compare?
2. Are there cross-cutting concerns (logging, caching, auth) that need explicit placement?
3. Should any of these layers be separate deployable units (microservices)?
```

Wait for mob response.

### Layer responsibility reference (technology-agnostic)

| Layer | Contains | Does NOT contain |
|-------|----------|-----------------|
| Domain | Entities, value objects, domain events, repository interfaces, domain services | Framework code, DB queries, HTTP |
| Application | Use cases, DTOs, validators, orchestration | DB access, HTTP requests |
| Infrastructure | Repo implementations, ORM, external clients | Business logic |
| Host/API | Routing, middleware, DI, startup | Business logic, DB queries |

---

## Step 3 — Integration and Data Flows

Based on integration points in requirements, map external dependencies.

Present to mob:

```
External integration points identified:

- [System X]: [purpose] | Direction: [inbound/outbound] | Protocol: [REST/event/DB/...]
- [System Y]: [purpose] | Direction: [inbound/outbound] | Protocol: [...]

Key data flows:
[Flow name, e.g., "Submit Order"]
  Client → API layer → Application (use case) → Domain → Infrastructure (persist) → Response

Questions:
1. Are these integration points accurate?
2. Are flows synchronous (request/response) or asynchronous (events/queues)?
3. Is this a monolith or are there service boundaries within the project itself?
```

Offer Mermaid sequence diagrams if the mob prefers visual output.

---

## Step 4 — ADR Recording

For each significant architectural decision reached during steps 1–3, record a formal ADR.

Present each ADR to the mob for confirmation before adding to the document:

```
I want to record this architectural decision:

ADR-00X: [short decision title]
Status: Proposed
Context: [what problem or trade-off this addresses]
Decision: [the specific choice made]
Consequences: [what becomes easier / what becomes harder]
Alternatives considered: [what was rejected and why]

Do you accept, reject, or want to modify this decision?
```

Only mark Status as "Accepted" after mob confirms.

### Common ADR categories — prompt these if not already decided

| Category | Typical decision to record |
|----------|--------------------------|
| Data persistence | SQL vs NoSQL; ORM vs raw queries; which DB engine |
| API style | REST vs GraphQL vs gRPC; versioning strategy |
| Authentication | JWT vs session; auth server vs in-process |
| Error handling | Global handler vs per-endpoint; error response shape |
| Event model | Sync vs async; message broker choice if async |
| Caching | No cache vs in-memory vs distributed; cache invalidation strategy |
| Observability | Structured logging format; tracing; metrics exposure |

---

## Phase 2 Validation Checkpoint

After all files are written and confirmed individually, do a final check:

```
All architecture files are complete:
  ✓ docs/architecture/01-domain-model.md
  ✓ docs/architecture/02-layers.md
  ✓ docs/architecture/03-integrations.md
  ✓ docs/architecture/adr/ADR-NNN-*.md  (one per confirmed decision)

Before closing Phase 2:
1. Do the ADRs reflect the decisions the mob agreed on?
2. Are there architectural risks not captured in 03-integrations.md?
3. Is the team ready to begin implementation?

Confirm when ready. Implementation may start only after this confirmation.
```

Only finalise on explicit mob confirmation.

---

## Handling Disagreement & Uncertainty

**Disagreement:** State both positions neutrally → ask "What are the driving constraints?" → offer trade-off comparison → if unresolved, record as ADR Status: "Proposed" with a note + flag in Risks.

**Uncertainty:** Propose a default, state the assumption and reasoning, record as ADR Status: "Proposed" to revisit later.

---

## Output File Mapping

| Step | Write to |
|------|----------|
| Step 1 — domain model | `docs/architecture/01-domain-model.md` |
| Step 2 — layers | `docs/architecture/02-layers.md` |
| Step 3 — integrations + flows | `docs/architecture/03-integrations.md` |
| Step 4 — each ADR | `docs/architecture/adr/ADR-NNN-[kebab-title].md` |

For ADRs: copy `docs/architecture/adr/ADR-000-template.md`, rename with next sequential number and a kebab-case title (e.g. `ADR-001-use-postgresql.md`). Write each ADR as a separate file immediately after mob confirms it.
