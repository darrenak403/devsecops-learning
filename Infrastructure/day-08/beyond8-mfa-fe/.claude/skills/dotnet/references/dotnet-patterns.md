# C# / .NET Patterns

Pure C# language and runtime patterns. No API routing, no test framework, no security policy — those live in their own references.

## Immutability

| Type | Construct | Mutability rule |
|------|-----------|-----------------|
| Value object | `sealed record Money(decimal Amount, string Currency)` | Immutable — records are copy-on-"change" |
| DTO | `required` + `init` properties | Settable only at construction |
| Entity | Class with `private set` | Mutable only via domain methods |

```csharp
public class Order
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public OrderStatus Status { get; private set; } = OrderStatus.Pending;

    public void Complete() => Status = OrderStatus.Completed;
}
```

---

## Dependency Injection

Register all application services as **scoped** (one per HTTP request). Use **primary constructor** (C# 12) — no field declarations needed:

```csharp
public class OrderService(IUnitOfWork uow, ILogger<OrderService> logger) : IOrderService { }
```

Never inject `IConfiguration` directly into services — bind via `IOptions<T>` instead (see Options Pattern).

---

## Options Pattern

```csharp
public sealed class SmtpOptions
{
    public const string SectionName = "Smtp";
    public required string Host { get; init; }
    public required int Port { get; init; }
}

builder.Services.Configure<SmtpOptions>(builder.Configuration.GetSection(SmtpOptions.SectionName));

public class EmailService(IOptions<SmtpOptions> options) { }
```

---

## Generic Repository + Unit of Work

**Invariants:**
- `SaveChangesAsync` lives on `IUnitOfWork` only — repositories never call it
- Repositories only touch the change tracker (`Add`, `Update`, `Remove`, `FindAsync`)
- Domain-specific queries go in typed repositories that extend `GenericRepository<T>`
- `IUnitOfWork` lazy-inits repos: `_orders ??= new OrderRepository(db)`

```csharp
// Application layer — interface only
public interface IGenericRepository<T> where T : class
{
    Task<T?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<List<T>> GetAllAsync(CancellationToken ct = default);
    Task AddAsync(T entity, CancellationToken ct = default);
    void Update(T entity);
    void Remove(T entity);
}

public interface IUnitOfWork : IDisposable
{
    IOrderRepository Orders { get; }
    IProductRepository Products { get; }
    Task<int> SaveChangesAsync(CancellationToken ct = default);
}
```

Infrastructure implements `GenericRepository<T>` via `db.Set<T>()`. Typed repositories (`OrderRepository : GenericRepository<Order>, IOrderRepository`) add domain queries with `AsNoTracking().Where(...)`.

---

## Async / Await

- Async all the way — never `.Result` or `.Wait()` (thread starvation)
- Parallel independent I/O: `await Task.WhenAll(taskA, taskB)`
- `CancellationToken`: accept in every async method, pass it down the entire call chain — never ignore it

---

## Clean Code

```csharp
// Extension methods — explicit, named conversions (Application/Infrastructure layer, never Domain)
public static OrderResponse ToResponse(this Order o) => new(o.Id, o.CustomerId, o.Status.ToString());
public static Order ToEntity(this CreateOrderRequest r) => new() { CustomerId = r.CustomerId };

// Pattern matching — switch expression over enum/status
var label = order.Status switch
{
    OrderStatus.Pending   => "Awaiting confirmation",
    OrderStatus.Completed => "Done",
    _                     => throw new UnreachableException()
};

// C# 12 collection expressions
List<string> tags = ["urgent", "new-customer"];
string[] roles   = [RoleConstants.Admin, RoleConstants.Manager];
```

Nullable discipline: annotate types, propagate `?`, don't suppress with `!` unless proven non-null.

---

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| `async void` | Return `Task` (except event handlers) |
| `.Result` or `.Wait()` | `await` |
| `catch (Exception) { }` (swallow) | Handle or rethrow with context |
| `new Service()` inside class | Constructor injection |
| `dynamic` in business logic | Generics or explicit types |
| Extracting 3-line guard chain into helper | Keep inline — abstraction hides intent |
| Method flag parameters (`bool isAdmin`) | Split into separate methods |
| `IConfiguration["key"]` in services | `IOptions<T>` |
