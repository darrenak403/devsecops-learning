# Architecture — Clean Architecture Layers

Apply strict dependency direction: inner layers know nothing about outer layers.

## Dependency Rule

```
Transport Layer       ← HTTP in/out, routing, auth, middleware
  └─ depends on → Application, Common

Application Layer     ← Business logic, use cases, DTOs, validators, mappings
  └─ depends on → Domain, Common

Infrastructure Layer  ← Data access, external services (email, storage, queues)
  └─ depends on → Application, Domain, Common (implements interfaces)

Domain Layer          ← Entities, repository interfaces — NO external dependencies
Common / Shared       ← Response envelope, pagination, error types, shared interfaces
```

Dependencies flow inward only. Infrastructure implements interfaces defined in Domain/Application — never the reverse.

---

## Layer Responsibilities

### Domain — What exists
- Entities (state + invariants, no HTTP or DB dependencies)
- Repository interfaces
- Domain constants, value objects, domain events

### Application — What to do
- Services: orchestrate repositories + external services
- DTOs: request/response shapes
- Validators: structural rules at entry points
- Mappings: explicit conversion functions
- Error/message constants

### Infrastructure — How to persist / communicate
- ORM context, entity configs, migrations
- Repository implementations
- External service clients (email, file storage, payments)

### Transport — How to expose
- Route/endpoint definitions
- Thin handlers: parse request → validate → call service → serialize response
- Bootstrapping: wire DI, middleware
- **No business logic here**

### Common / Shared — Plumbing
- Response envelope, pagination types
- Global error handler
- Shared interfaces

---

## Boundary Rules

- **Domain must NOT contain:** DTOs, ORM query builders, HTTP types, references to outer layers
- **Application must NOT contain:** DB context, ORM queries, HTTP context, endpoint registration
- **Infrastructure must NOT contain:** Business rules, DTOs, endpoint logic
- **Transport must NOT contain:** Business logic, direct DB access

---

## Checklist: Adding a New Feature

```
Domain
[ ] Entity
[ ] Repository interface
[ ] Domain constants if needed

Application
[ ] Service interface + implementation
[ ] Request + response DTOs
[ ] Mapping functions
[ ] Validator (structural rules only)
[ ] Error message constants

Infrastructure
[ ] Repository implementation
[ ] ORM entity configuration + migration

Transport
[ ] Endpoint / route handler (thin)
[ ] Route registered in bootstrapping
```
