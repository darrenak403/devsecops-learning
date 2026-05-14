# API Design — REST + ASP.NET Core Minimal API

URL structure, route groups, response envelope, pagination, validation wiring, authorization, and soft delete. No C# language patterns (see dotnet-patterns.md), no security policy (see security.md).

## URL Rules

```
# Plural nouns, kebab-case, versioned, no verbs in path
GET    /api/v1/orders
GET    /api/v1/orders/{orderId}
POST   /api/v1/orders
PATCH  /api/v1/orders/{orderId}

# Sub-resources — max 3 path segments after /api/v1
GET    /api/v1/orders/{orderId}/items     ✅
POST   /api/v1/auth/login                ✅  (verb ok for non-CRUD action)

# Too deep → flatten to independent resource
GET    /api/v1/projects/{id}/items/{iid}/tags/{tid}   ❌  → /api/v1/tags/{tid}
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

Handlers are **thin**: parse → validate → call service → return result. No business logic.

```csharp
// GET — no validation needed
private static async Task<IResult> GetByIdAsync(
    [FromRoute] Guid orderId,
    [FromServices] IOrderService service,
    CancellationToken ct = default)
    => (await service.GetByIdAsync(orderId, ct)).ToHttpResult();

// POST/PUT/PATCH — validate first, always
private static async Task<IResult> CreateAsync(
    [FromBody] CreateOrderRequest req,
    [FromServices] IValidator<CreateOrderRequest> validator,
    [FromServices] IOrderService service,
    CancellationToken ct = default)
{
    if (!req.ValidateRequest(validator, out var result)) return result!;
    return (await service.CreateAsync(req, ct)).ToHttpResult();
}
```

**Rules:**
- `ValidateRequest` + `ToHttpResult` are project extension methods — always use them, never inline
- Services return `ApiResponse<T>` — never throw for expected failures (404, 400, 409)
- `ICurrentUserService` injected when handler needs caller identity

---

## Route Group Structure

One file per resource: `{Module}Endpoints.cs` in the Api layer.

```csharp
public static class OrderEndpoints
{
    public static IEndpointRouteBuilder MapOrderApi(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/v1/orders");
        group.MapGet("/", GetAllAsync).RequireAuthorization();
        group.MapGet("/{orderId:guid}", GetByIdAsync).RequireAuthorization();
        group.MapPost("/", CreateAsync).RequireAuthorization(p => p.RequireRole(RoleConstants.Admin));
        group.WithTags("Orders").RequireRateLimiting("Fixed");
        return app;
    }
    // handlers below...
}
```

---

## Pagination — `[AsParameters]`

```csharp
// Request DTO — inherit PaginationRequest to get Page, PageSize, etc.
public class GetOrdersRequest : PaginationRequest
{
    public string? Search { get; set; }
    public OrderStatus? Status { get; set; }
}

// Handler
private static async Task<IResult> GetAllAsync(
    [AsParameters] GetOrdersRequest req,
    [FromServices] IOrderService service,
    CancellationToken ct = default)
    => (await service.GetPagedAsync(req, ct)).ToHttpResult();
```

---

## Authorization

```csharp
.RequireAuthorization()                                          // any authenticated user
.RequireAuthorization(p => p.RequireRole(RoleConstants.Admin))  // specific role
.AllowAnonymous()                                                // explicitly public
```

Every endpoint must have one of the three — no implicit defaults. Always use `RoleConstants` — never magic strings.

---

## Soft Delete

```csharp
// Handler marks deleted — never hard deletes
entity.DeletedAt = DateTime.UtcNow;
entity.DeletedBy = currentUser.UserId;
await _uow.SaveChangesAsync(ct);
```

Every query on soft-deletable entities **must** filter: `.Where(x => x.DeletedAt == null)`.

---

## Validator — Structural Rules Only

```csharp
public class CreateOrderRequestValidator : AbstractValidator<CreateOrderRequest>
{
    public CreateOrderRequestValidator()
    {
        RuleFor(x => x.CustomerId).NotEmpty();
        RuleFor(x => x.Items).NotEmpty();
    }
}
```

Validators check shape and format only — no DB lookups, no business rules. Business rules live in the service layer.
