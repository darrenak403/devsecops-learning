# Security — .NET / ASP.NET Core

Security-specific concerns only: secrets, input validation, SQL injection, authentication/authorization, error responses, PII logging, rate limiting, and dependency auditing. No API routing structure (see api-design.md), no C# language patterns (see dotnet-patterns.md).

## 1. Secrets Management

Never put secrets in `appsettings.json`. Use User Secrets in dev, environment variables in prod.

```bash
dotnet user-secrets set "Jwt:SecretKey" "your-key" --project src/MyProject.Api
dotnet user-secrets set "ConnectionStrings:Default" "Host=..." --project src/MyProject.Api
```

```csharp
// Bind via IOptions<T> — never read IConfiguration["key"] directly in services
builder.Services.Configure<JwtOptions>(builder.Configuration.GetSection("Jwt"));

public class TokenService(IOptions<JwtOptions> opts)
{
    private readonly JwtOptions _jwt = opts.Value;
}
```

**Verify:** No hardcoded keys/passwords; `.env` in `.gitignore`; prod secrets in env vars or vault.

---

## 2. Input Validation

All POST/PUT/PATCH requests validated before reaching the service layer.

```csharp
// Handler — validate first, always
private static async Task<IResult> CreateAsync(
    [FromBody] CreateItemRequest req,
    [FromServices] IValidator<CreateItemRequest> validator,
    [FromServices] IItemService service,
    CancellationToken ct = default)
{
    var validation = await validator.ValidateAsync(req, ct);
    if (!validation.IsValid)
        return Results.ValidationProblem(validation.ToDictionary());

    return (await service.CreateAsync(req, ct)).ToHttpResult();
}

// Validator — structural rules only (no DB lookups, no business logic)
public class CreateItemRequestValidator : AbstractValidator<CreateItemRequest>
{
    public CreateItemRequestValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        RuleFor(x => x.Type).IsInEnum();
    }
}
```

File uploads: validate size + MIME type + extension before processing.

---

## 3. SQL Injection

EF Core LINQ is parameterized by default. Danger only with raw SQL.

```csharp
// SAFE — LINQ + soft-delete filter
var item = await db.Items
    .Where(i => i.Id == id && i.DeletedAt == null)
    .FirstOrDefaultAsync(ct);

// SAFE — raw SQL with parameter
await db.Items.FromSqlRaw("SELECT * FROM items WHERE id = {0}", id).ToListAsync(ct);

// NEVER — string interpolation in raw SQL
// db.Items.FromSqlRaw($"SELECT * WHERE id = '{id}'")
```

---

## 4. Authentication & Authorization

```csharp
// JWT configured globally — use ICurrentUserService, never parse HttpContext.User directly
private static async Task<IResult> UpdateAsync(
    [FromRoute] Guid itemId,
    [FromBody] UpdateItemRequest req,
    [FromServices] IItemService service,
    [FromServices] ICurrentUserService? currentUser,
    CancellationToken ct = default)
{
    var updatedBy = currentUser?.IsAuthenticated == true ? currentUser.UserId : (Guid?)null;
    return (await service.UpdateAsync(itemId, req, updatedBy, ct)).ToHttpResult();
}
```

Every endpoint must have either `.RequireAuthorization()` or `.AllowAnonymous()` — no implicit defaults.

Ownership check before mutations:

```csharp
if (item.OwnerId != currentUser.UserId && !currentUser.IsInRole(RoleConstants.Admin))
    return ApiResponse<T>.Failure(403, "Forbidden");
```

---

## 5. Error Responses

Never expose stack traces or exception messages to clients.

```csharp
// CORRECT
return ApiResponse<T>.Failure(404, "Item not found");
return (await service.GetAsync(id, ct)).ToHttpResult();

// WRONG — leaks internals
return Results.Problem(detail: ex.ToString(), statusCode: 500);
```

Global exception handler returns generic 500 without inner exception details.

---

## 6. PII & Credentials in Logs

```csharp
// WRONG — credentials in logs
logger.LogInformation("Login: email={Email} password={Password}", email, password);

// CORRECT — log identifier only
logger.LogInformation("Login attempt: userId={UserId}", userId);

// Mask PII (phone, card numbers)
logger.LogInformation("OTP sent to {Phone}", phone[..3] + "****" + phone[^2..]);
```

---

## 7. Rate Limiting

```csharp
// Attach per route group — mandatory on auth and upload endpoints
authGroup.WithTags("Auth").RequireRateLimiting("Strict");
uploadGroup.WithTags("Upload").RequireRateLimiting("Fixed");
```

---

## 8. Dependency Audit

```bash
dotnet list package --vulnerable   # known CVEs
dotnet outdated                    # stale packages
```

---

## Pre-Deployment Checklist

- [ ] No hardcoded secrets — User Secrets / env / vault
- [ ] All POST/PUT/PATCH validate before service call
- [ ] EF Core uses LINQ — no raw SQL string interpolation
- [ ] Every endpoint has `RequireAuthorization()` or `AllowAnonymous()`
- [ ] Caller identity via `ICurrentUserService`, not `HttpContext.User` directly
- [ ] Role constants used — not magic strings
- [ ] No stack traces in error responses
- [ ] No credentials or PII in logs
- [ ] Rate limiting on auth and upload endpoints
- [ ] File uploads validate size, MIME type, and extension
- [ ] HTTPS enforced in production
- [ ] Soft delete only — queries filter `DeletedAt == null`
- [ ] `dotnet list package --vulnerable` clean
