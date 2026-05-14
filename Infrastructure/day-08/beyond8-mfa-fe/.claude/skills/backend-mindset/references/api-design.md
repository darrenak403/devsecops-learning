# API Design — REST Principles

URL structure, HTTP semantics, handler shape, pagination, authorization. Language-independent.

## URL Rules

```
# Plural nouns, kebab-case, versioned, no verbs in path
GET    /api/v1/orders
GET    /api/v1/orders/{orderId}
POST   /api/v1/orders
PATCH  /api/v1/orders/{orderId}
DELETE /api/v1/orders/{orderId}

# Sub-resources — max 3 path segments after /api/v1
GET    /api/v1/orders/{orderId}/items     ✅
POST   /api/v1/auth/login                ✅  (verb ok for non-CRUD action)

# Too deep → flatten to independent resource
GET    /api/v1/projects/{id}/items/{iid}/tags/{tid}   ❌
```

## HTTP Methods & Status Codes

| Operation | Method | Success | Error |
|-----------|--------|---------|-------|
| List | GET | 200 | — |
| Get one | GET | 200 | 404 |
| Create | POST | 201 | 400 |
| Full update | PUT | 200 | 400 / 404 |
| Partial update | PATCH | 200 | 400 / 404 |
| Soft delete | DELETE | 204 | 404 |
| Not authenticated | any | — | 401 |
| Wrong role | any | — | 403 |
| Business conflict | any | — | 409 |

---

## Handler Shape

Handlers are **thin**: parse → validate → call service → return result. No business logic in handlers.

```
receive request
  ↓
validate input (shape/format only — no business rules)
  ↓
call service
  ↓
serialize response
```

Services handle business logic and return a result envelope — never throw for expected failures (404, 400, 409).

---

## Pagination

Standard query params: `page`, `pageSize`, `search`, domain-specific filters.

Response: `{ data: [...], total, page, pageSize }` — always include total for client-side paging.

---

## Authorization

Every endpoint must explicitly declare its auth requirement — no implicit defaults:
- Authenticated only (any valid token)
- Role/scope required (specific permission)
- Public (explicitly marked, not just "no auth added")

---

## Soft Delete

Mark deleted with `deletedAt` timestamp + `deletedBy` — never hard delete records that may be referenced.

Every query on soft-deletable resources must filter out deleted records — never let deleted data leak into responses.

---

## Validators

Structural rules only at the transport layer (format, required fields, max length).
Business rules (uniqueness, ownership, state machine transitions) live in the service layer.
