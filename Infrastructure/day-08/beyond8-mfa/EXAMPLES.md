# CLAUDE.md

Real-world C# examples demonstrating the four principles. Each example shows what LLMs commonly do wrong and how to fix it.

---

## 1. Think Before Coding

### Example 1: Hidden Assumptions

**User Request:** "Add an endpoint to get user orders"

**❌ What LLMs Do (Wrong Assumptions)**

```csharp
app.MapGet("/orders", async (AppDbContext db) =>
    await db.Orders.ToListAsync());
```

**Problems:**

- Returns the EF entity directly — exposes internal model, breaks layering
- No auth — any anonymous caller can access all orders
- No pagination — loads the full table into memory
- Missing `.Where(o => o.DeletedAt == null)` — soft-deleted orders leak through
- No `CancellationToken` — request cancellation is ignored

**✅ What Should Happen (Surface Assumptions)**

```
Before implementing, I need to clarify:

1. **Scope**: All orders, or only the authenticated user's orders?
2. **Auth**: .RequireAuthorization() or a specific role (e.g. Admin)?
3. **Pagination**: Should this use PaginationRequest (Page, PageSize)?
4. **Response shape**: OrderResponse DTO, or a different projection?

Simplest valid default: paginated list filtered to the caller's orders,
any authenticated user. Shall I proceed with that?
```

### Example 2: Multiple Interpretations

**User Request:** "Make order queries faster"

**❌ What LLMs Do (Pick Silently)**

```csharp
// Adds Redis cache + compiled query + split query + indexes — all at once
private static readonly Func<AppDbContext, Guid, Task<Order?>> _getOrder =
    EF.CompileAsyncQuery(...);

public async Task<OrderResponse?> GetByIdAsync(Guid id, CancellationToken ct)
{
    var cached = await _cache.GetAsync($"order:{id}", ct);
    if (cached is not null) return Deserialize(cached);
    // ...
}
```

**Problems:**

- Added caching, compiled queries, and infra changes without knowing the bottleneck
- Redis adds an operational dependency that may not be needed
- Each optimization has tradeoffs — none were discussed

**✅ What Should Happen (Present Tradeoffs)**

```
"Faster queries" could mean:

1. **Eliminate unnecessary data** — .AsNoTracking().Select(projection)
   No infra change, immediate gain for read-only paths. Effort: 30 min.

2. **Cache results** — IMemoryCache (single instance, low overhead)
   or IDistributedCache/Redis (multi-instance, shared state). Effort: 2–4 hours.

3. **Compiled queries** — measurable only on hot paths called thousands of times/sec.
   Effort: 1 hour, but profile first.

Which scenario is actually slow? I can check with a query plan if you share the endpoint.
```

---

## 2. Simplicity First

### Example 1: Over-abstraction

**User Request:** "Add discount calculation to the order"

**❌ What LLMs Do (Overengineered)**

```csharp
public interface IDiscountStrategy
{
    decimal Calculate(decimal amount);
}

public class PercentageDiscountStrategy(decimal percent) : IDiscountStrategy
{
    public decimal Calculate(decimal amount) => amount * (percent / 100m);
}

public class DiscountCalculatorFactory
{
    public IDiscountStrategy Create(DiscountType type, decimal value) => type switch
    {
        DiscountType.Percentage => new PercentageDiscountStrategy(value),
        _ => throw new NotSupportedException()
    };
}
// 60+ lines for a single formula that may never change
```

**Problems:**

- Strategy pattern adds three types for one rule that exists today
- Factory creates an abstraction for a switch with one case
- Each new developer must navigate three files to understand one calculation

**✅ What Should Happen (Simple)**

```csharp
public static decimal CalculateDiscount(decimal amount, decimal percentOff)
    => amount * (percentOff / 100m);
```

**When to add complexity:** Only when a second discount type actually arrives. Refactor then.

### Example 2: Speculative Features

**User Request:** "Save user preferences"

**❌ What LLMs Do (Unnecessary Features)**

```csharp
public async Task SavePreferencesAsync(
    Guid userId,
    UserPreferences prefs,
    bool merge = true,
    bool notify = false,
    bool validate = true,
    CancellationToken ct = default)
{
    if (validate) await ValidateAsync(prefs, ct);
    var existing = merge ? await GetAsync(userId, ct) : new();
    existing.MergeWith(prefs);
    await _cache.RemoveAsync($"prefs:{userId}", ct);
    if (notify) await _events.PublishAsync(new PreferencesChangedEvent(userId), ct);
    // ...
}
```

**Problems:**

- `merge`, `notify`, and `validate` flags were never asked for
- Cache invalidation, event publishing, and merge strategy add complexity before any requirement
- Five boolean-ish parameters — callers can't tell what combination is correct

**✅ What Should Happen (Just What Was Asked)**

```csharp
public async Task SavePreferencesAsync(Guid userId, UserPreferences prefs, CancellationToken ct)
{
    var user = await _uow.Users.GetByIdAsync(userId, ct) ?? throw new NotFoundException();
    user.SetPreferences(prefs);
    await _uow.SaveChangesAsync(ct);
}
```

**Add later if needed:** Caching when latency is measured, events when a subscriber exists, merging when the requirement arrives.

---

## 3. Surgical Changes

### Example 1: Drive-by Refactoring

**User Request:** "Fix the bug where soft-deleted orders still appear in the list"

**❌ What LLMs Do (Too Much)**

```diff
  private async Task<List<OrderResponse>> GetOrdersAsync(CancellationToken ct)
  {
-     var orders = await _uow.Orders.GetAllAsync(ct);
-     return orders.Select(o => o.ToResponse()).ToList();
+     return await _uow.Orders
+         .Query()
+         .AsNoTracking()
+         .Where(o => o.DeletedAt == null)
+         .Select(o => new OrderResponse(o.Id, o.Status.ToString()))
+         .ToListAsync(ct);
  }
```

**Problems:**

- The bug fix is `.Where(o => o.DeletedAt == null)` — everything else is unrequested
- Changed method chain style, added `.AsNoTracking()`, inlined the projection
- Reformatted surrounding whitespace
- Each change is reasonable alone — together they make the diff hard to review

**✅ What Should Happen (Surgical)**

```diff
  private async Task<List<OrderResponse>> GetOrdersAsync(CancellationToken ct)
  {
      var orders = await _uow.Orders.GetAllAsync(ct);
-     return orders.Select(o => o.ToResponse()).ToList();
+     return orders.Where(o => o.DeletedAt == null).Select(o => o.ToResponse()).ToList();
  }
```

**Only changed:** The one line that filters out soft-deleted records.

### Example 2: Style Drift

**User Request:** "Add logging to the order creation service"

**❌ What LLMs Do (Reformat Everything)**

```diff
- public class OrderService(IUnitOfWork uow) : IOrderService
+ public class OrderService : IOrderService
  {
+     private readonly IUnitOfWork _uow;
+     private readonly ILogger<OrderService> _logger;
+
+     /// <summary>Creates the order service.</summary>
+     public OrderService(IUnitOfWork uow, ILogger<OrderService> logger)
+     {
+         _uow = uow;
+         _logger = logger;
+     }
+
      public async Task<ApiResponse<OrderResponse>> CreateAsync(
-         CreateOrderRequest req, CancellationToken ct)
+         CreateOrderRequest req,
+         CancellationToken ct = default)
      {
+         _logger.LogInformation("Creating order for customer {CustomerId}", req.CustomerId);
```

**Problems:**

- Rewrote primary constructor (C# 12) back to field injection — style regression
- Added XML `<summary>` tag nobody asked for
- Changed method signature formatting
- Added `= default` to `CancellationToken` without being asked

**✅ What Should Happen (Match Existing Style)**

```diff
- public class OrderService(IUnitOfWork uow) : IOrderService
+ public class OrderService(IUnitOfWork uow, ILogger<OrderService> logger) : IOrderService
  {
      public async Task<ApiResponse<OrderResponse>> CreateAsync(
          CreateOrderRequest req, CancellationToken ct)
      {
+         logger.LogInformation("Creating order for customer {CustomerId}", req.CustomerId);
```

**Matched:** Primary constructor style, no docstring, existing parameter formatting.

---

## 4. Goal-Driven Execution

### Example 1: Fix Without Reproducing

**User Request:** "Order total is calculated wrong when a discount is applied"

**❌ What LLMs Do (Fix Without a Test)**

```csharp
// Immediately changes CalculateTotalAsync without confirming the bug
public decimal CalculateTotalAsync(IEnumerable<OrderItem> items, decimal discountPercent)
    => items.Sum(i => i.Price * i.Quantity) * (1 - discountPercent / 100m);
```

**Problems:**

- No failing test means we don't know if this actually reproduces the reported issue
- No regression protection — next change can silently break it again
- The "fix" might not match the real bug

**✅ What Should Happen (Reproduce First)**

```csharp
// 1. Write a test that fails and reproduces the issue
[Fact]
public void CalculateTotal_With10PercentDiscount_Returns90()
{
    var items = new[] { new OrderItem("SKU-1", qty: 1, price: 100m) };
    var total = OrderService.CalculateTotal(items, discountPercent: 10m);
    total.Should().Be(90m); // currently returns 100 — confirms bug
}

// Verify: test fails (RED — bug reproduced)

// 2. Fix the calculation
public static decimal CalculateTotal(IEnumerable<OrderItem> items, decimal discountPercent)
    => items.Sum(i => i.Price * i.Quantity) * (1 - discountPercent / 100m);

// Verify: test passes (GREEN)
```

### Example 2: Multi-Step with Verification

**User Request:** "Add rate limiting to the API"

**❌ What LLMs Do (All at Once)**

```csharp
// Full Redis-backed sliding window rate limiter with per-endpoint config,
// monitoring hooks, and retry-after headers — 200 lines, one commit
```

**✅ What Should Happen (Incremental with Verification)**

```
Plan:

1. Add fixed window limiter in Program.cs
   Verify: curl /api/v1/orders 11× → first 10 succeed, 11th returns 429

2. Apply to route groups via .RequireRateLimiting("Fixed")
   Verify: existing integration tests still pass

3. Per-endpoint rates if /auth and /orders need different limits
   Verify: [Theory] tests cover both thresholds independently

Each step is independently deployable. Start with step 1?
```

---

## Anti-Patterns Summary

| Principle           | Anti-Pattern                                       | Fix                                                    |
| ------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| Think Before Coding | Returns EF entity from endpoint without asking     | Return response DTO — clarify response shape first     |
| Think Before Coding | Silently picks caching strategy                    | Present IMemoryCache vs Redis tradeoff, ask which fits |
| Simplicity First    | Strategy pattern for a single discount rule        | One static method; extract when second case arrives    |
| Simplicity First    | Flag parameters (`bool merge`, `bool notify`)      | Add each parameter only when the requirement exists    |
| Surgical Changes    | Converts primary constructor to field injection    | Keep existing DI style — change only what was asked    |
| Surgical Changes    | `.AsNoTracking()` added while fixing unrelated bug | One changed line per reported issue                    |
| Goal-Driven         | Fixes calculation without a failing test           | Write RED test first, then make it pass                |
| Goal-Driven         | Full feature in one commit, no verification gates  | Incremental steps, each independently verifiable       |

## Key Insight

The "wrong" examples aren't obviously bad — they often follow design patterns and best practices. The problem is **timing**: complexity is added before it's needed, which makes the code harder to review, harder to test, and harder to reason about.

The "right" versions are:

- Easier to read and review
- Faster to implement
- Safe to change later

**Good code solves today's problem simply. Complexity earns its place when a second requirement arrives.**
