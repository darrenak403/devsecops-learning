# Testing — TDD + Strategy

TDD workflow, test pyramid, and test organization. Language-independent.

## The TDD Cycle

**RED → GREEN → REFACTOR** — always in this order.

1. **RED**: Write a failing test describing desired behavior
2. **GREEN**: Write the minimum code to make it pass — nothing more
3. **REFACTOR**: Clean up while keeping tests green

Never write implementation before a failing test exists.

---

## Test Pyramid

```
         ┌──────┐
         │  E2E │          ← few, slow, catch integration gaps
         ├──────────┤
         │Integration│     ← real DB/services, test boundaries
         ├──────────────┤
         │   Unit Tests   │ ← fast, isolated, most of the suite
         └────────────────┘
```

- **Unit tests**: business logic, service layer, pure functions — mock external dependencies
- **Integration tests**: persistence layer, external service clients — use real infrastructure (containers > in-memory)
- **E2E / contract tests**: API surface, auth flows, critical paths only

---

## What to Test

| Layer | What to test |
|-------|-------------|
| Domain | Invariants, domain logic, value object rules |
| Application / Service | Return values, side effects (calls to repos/services), error cases |
| Validators | All valid + invalid input cases |
| Infrastructure / Repository | Real queries against real DB (not mocked) |
| Transport / Handler | Auth, routing, request parsing, response shape |

---

## Key Principles

- Test **observable behavior** (return values, HTTP status codes, side effects), not implementation internals
- Each test is fully **self-contained** — no shared mutable state between tests
- Use **real infrastructure** for integration tests — in-memory substitutes hide real bugs
- **Arrange / Act / Assert** — one logical assertion per test, clear structure
- Test names describe **behavior**, not implementation: `GetById_WhenNotFound_Returns404` not `testGetById`

---

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| Write implementation first | Tests first — RED before GREEN |
| In-memory DB | Real DB in containers |
| Mocking the thing under test | Mock only external dependencies |
| Tests depending on each other | Each test is self-contained |
| Testing private methods | Test through the public interface |
| Sleeping/waiting in tests | Polling helper or proper async test support |

---

## Coverage Targets

- **80%+** overall — enforced in CI
- **100%** for auth/permission logic — no exceptions
- Avoid chasing coverage numbers — an untested sad path matters more than a trivially-covered happy path
