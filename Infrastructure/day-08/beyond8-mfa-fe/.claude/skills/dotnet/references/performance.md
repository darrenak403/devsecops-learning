# Performance — .NET / EF Core / Caching

Query optimization, caching patterns, async performance, and HTTP output caching. No API routing (see api-design.md), no security policy (see security.md).

## EF Core Query Rules

| Rule | Reason |
|------|--------|
| `.AsNoTracking()` on all read-only queries | Avoids change tracker overhead — reads never need tracking |
| `.Select()` to project to DTO | Fetches only needed columns; never return the entity from a query |
| `.Include()` only what the caller uses | Eager-load every nav = cartesian explosion on joins |
| `.AsSplitQuery()` when Include causes row multiplication | Two SQL queries beats N×M rows |
| `.AnyAsync()` instead of `Count() > 0` | Stops at first row |
| Pre-check in `.Where()` before `.ToListAsync()` | Never `.ToList()` then filter in memory |

**Compiled queries** — use on hot paths called thousands of times/second:

```csharp
private static readonly Func<AppDbContext, Guid, Task<Order?>> GetOrderById =
    EF.CompileAsyncQuery((AppDbContext db, Guid id) =>
        db.Orders.AsNoTracking().FirstOrDefault(o => o.Id == id && o.DeletedAt == null));
```

---

## Caching Decision

| Scenario | Use |
|----------|-----|
| Single instance, non-critical (can differ across pods) | `IMemoryCache` |
| Multi-instance, shared state, session data | `IDistributedCache` (Redis via `AddServiceRedis`) |
| Cache entire HTTP response | Output caching (middleware level) |

**Cache key convention:** `"{service}:{entity}:{id-or-filter}"` — e.g., `"order:123"`, `"products:active"`.

### IMemoryCache pattern

```csharp
if (cache.TryGetValue("products:active", out List<ProductDto>? cached)) return cached!;
var dtos = (await uow.Products.GetActiveAsync(ct)).Select(p => p.ToDto()).ToList();
cache.Set("products:active", dtos, TimeSpan.FromMinutes(5));
return dtos;
```

### IDistributedCache pattern

```csharp
var bytes = await cache.GetAsync(key, ct);
if (bytes is not null) return JsonSerializer.Deserialize<UserSession>(bytes);

await cache.SetAsync(key, JsonSerializer.SerializeToUtf8Bytes(session),
    new DistributedCacheEntryOptions
    {
        AbsoluteExpirationRelativeToNow = TimeSpan.FromHours(1),
        SlidingExpiration = TimeSpan.FromMinutes(20)
    }, ct);
```

Always set absolute expiry — never cache without TTL.

---

## HTTP Output Caching

```csharp
builder.Services.AddOutputCache(options =>
    options.AddPolicy("LongCache", b => b.Expire(TimeSpan.FromMinutes(10))));

app.UseOutputCache(); // before route mapping

group.MapGet("/", GetAllAsync).CacheOutput("LongCache");
group.MapGet("/{id:guid}", GetByIdAsync)
    .CacheOutput(b => b.SetVaryByRouteValue("id").Expire(TimeSpan.FromMinutes(5)));
```

Invalidate after mutations: `await outputCacheStore.EvictByTagAsync("tag-name", ct)`.

---

## Async Performance

```csharp
// ValueTask — when result is usually synchronous (cache hit, guard clause)
public ValueTask<bool> IsActiveAsync(Guid id)
{
    if (_local.TryGetValue(id, out bool v)) return ValueTask.FromResult(v);
    return new ValueTask<bool>(FetchFromDbAsync(id));
}

// Parallel independent I/O
var (orders, metrics) = (GetRecentOrdersAsync(ct), GetMetricsAsync(ct));
await Task.WhenAll(orders, metrics);
return new Dashboard(await orders, await metrics);
```

**CancellationToken:** accept in every async method, pass the entire call chain — never default to `CancellationToken.None` internally.

---

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| `Task.Result` / `.Wait()` | `await` — sync-over-async causes thread starvation |
| Loading full entity for one field | `.Select()` projection |
| Re-querying inside a loop | Batch load before loop, look up in dictionary |
| `IMemoryCache` in multi-instance deployment | `IDistributedCache` |
| Caching without TTL | Always set absolute expiry |
| Ignoring `CancellationToken` | Accept `ct` everywhere, propagate down |
