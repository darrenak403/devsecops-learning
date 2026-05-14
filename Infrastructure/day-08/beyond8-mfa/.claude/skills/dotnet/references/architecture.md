# Architecture — Clean Architecture Layers

Apply strict dependency direction: inner layers know nothing about outer layers.

## Dependency Rule

```
Api / Transport Layer       ← HTTP in/out, routing, auth, middleware
  └─ depends on → Application, Common

Application Layer           ← Business logic, use cases, DTOs, validators, mappings
  └─ depends on → Domain, Common

Infrastructure Layer        ← Data access (EF Core), external services (email, storage)
  └─ depends on → Application, Domain, Common (implements interfaces)

Domain Layer                ← Entities, repository interfaces — NO external dependencies
Common / Shared             ← Response envelope, pagination, error types, shared interfaces
```

**The rule:** Dependencies flow inward only. Nothing in inner layers knows about outer layers. Infrastructure implements interfaces defined in Domain/Application.

---

## Layer Responsibilities

### Domain — What exists

- Entities (state + simple invariants, no HTTP or DB dependencies)
- Repository interfaces (`IUserRepository`, `IGenericRepository<T>`)
- Domain constants (roles, statuses, allowed values)
- Value objects and domain events (if applicable)

**No:** ORM attributes beyond simple column mapping, DTOs, business orchestration, external packages.

### Application — What to do

- Services: orchestrate repositories + external services, return response envelopes
- DTOs: request/response shapes
- Validators: structural rules at entry points (FluentValidation)
- Mappings: explicit conversion functions (`ToResponse()`, `ToEntity()`, `ApplyUpdate()`)
- Error/message constants: all user-facing error codes defined here
- Service interfaces registered via DI

### Infrastructure — How to persist / communicate

- ORM context, entity configurations, migrations
- Repository implementations
- External service clients (email, file storage, payment, SMS)
- Seed data

### Api / Transport — How to expose

- Route/endpoint definitions (one module per resource)
- Thin handlers: parse request → validate → call service → serialize response
- Bootstrapping: wire DI, middleware, route groups
- **No business logic here**

### Common / Shared — Plumbing

- Response envelope (`ApiResponse<T>`, success/failure helpers)
- Pagination request/response types
- Validation extension utilities
- Global error handler / exception middleware
- Shared interfaces (`ICurrentUserService`, `ICacheService`)

---

## What Goes Where — Quick Reference

| Thing                     | Layer          | Location pattern                               |
| ------------------------- | -------------- | ---------------------------------------------- |
| Entity / model            | Domain         | `domain/entities/{Name}`                       |
| Domain constant           | Domain         | `domain/constants/{Name}Constants`             |
| Repository interface      | Domain         | `domain/repositories/I{Name}Repository`        |
| Service interface         | Application    | `application/interfaces/I{Name}Service`        |
| Service implementation    | Application    | `application/services/{Name}Service`           |
| Request / response DTO    | Application    | `application/dtos/{module}/`                   |
| Validator                 | Application    | `application/validators/{module}/`             |
| Mapping functions         | Application    | `application/mappings/{Name}Mappings`          |
| Error / message constants | Application    | `application/constants/messages/`              |
| ORM config / migration    | Infrastructure | `infrastructure/persistence/`                  |
| Repository implementation | Infrastructure | `infrastructure/repositories/{Name}Repository` |
| External service client   | Infrastructure | `infrastructure/services/`                     |
| Endpoint / route          | Api            | `api/endpoints/{Module}Endpoints`              |
| App bootstrapping / DI    | Api            | `api/bootstrap/`                               |

---

## Boundary Rules

**Domain must NOT contain:** DTOs, ORM query builders, HTTP types, references to Application or Infrastructure.

**Application must NOT contain:** DB context, ORM queries, HTTP context, endpoint registration, references to Infrastructure.

**Infrastructure must NOT contain:** Business rules, DTOs, endpoint logic — only persistence and external I/O.

**Api must NOT contain:** Business logic, direct DB access, complex data transformation — delegate to Application.

---

## Checklist: Adding a New Feature

```
Domain
[ ] Entity in domain/entities/
[ ] Repository interface in domain/repositories/
[ ] Domain constants if needed (roles, statuses, enum-like values)

Application
[ ] Service interface
[ ] Service implementation
[ ] Request + response DTOs
[ ] Mapping functions
[ ] Validator (structural rules only)
[ ] Error message constants
[ ] Service registered in DI

Infrastructure
[ ] Repository implementation
[ ] ORM entity configuration
[ ] Migration (if schema changes)
[ ] External service client (if needed)

Api
[ ] Endpoint / route handler
[ ] Route registered in app bootstrapping
```

---

## Migration Rules

Never create migrations manually — always use the ORM migration tool:

```bash
dotnet ef migrations add <Name>                    # EF Core
dotnet ef migrations add <Name> --project src/MyProject.Infrastructure --startup-project src/MyProject.Api
```

**Commit migration files together** with the entity change that triggered them.

**Deploy order:** apply migrations to production DB _before_ deploying new code — never after.
