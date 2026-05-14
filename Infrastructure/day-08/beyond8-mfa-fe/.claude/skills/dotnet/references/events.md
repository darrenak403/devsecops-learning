# Events — MassTransit + RabbitMQ

Event contracts, publishing, consumers, retry, idempotency, and logging. No Aspire wiring (see aspire.md), no C# patterns (see dotnet-patterns.md).

## Event Contract Design

```csharp
// Shared.Common/Contracts/BaseEvent.cs — abstract, not interface
public abstract class BaseEvent
{
    public Guid EventId { get; } = Guid.NewGuid();
    public DateTime OccurredAt { get; } = DateTime.UtcNow;
    public abstract string EventType { get; }
}
```

**Naming convention:** `{service}.{entity}.{action}.v{version}`
```csharp
public class OrderCreatedEvent : BaseEvent
{
    public override string EventType => "order-service.order.created.v1";
    public Guid OrderId { get; set; }
    public Guid CustomerId { get; set; }
    // Denormalize what consumers will need — minimize extra queries in consumers
    public string CustomerEmail { get; set; } = string.Empty;
}
```

**Contract location:** `MyProject.{Source}.Contracts/Events/` — separate project. Never in Application or Domain.

---

## Publishing

**Rule:** Always publish *after* `SaveChangesAsync`. Never inside a transaction that could roll back.

```csharp
await unitOfWork.SaveChangesAsync(ct);
await publishEndpoint.Publish(new OrderCreatedEvent { OrderId = order.Id, ... }, ct);
```

---

## Consumers

**Auto-discovered** — no manual registration. Location: `{Service}.Application/Consumers/`.

**Consumer invariants:**
- Log `MessageId` at start (Debug) and end (Information)
- Only log-then-rethrow on failure — let MassTransit handle retry
- Keep business logic idempotent — the same message may arrive multiple times

```csharp
public class OrderCreatedConsumer(ILogger<OrderCreatedConsumer> logger, IUnitOfWork uow)
    : IConsumer<OrderCreatedEvent>
{
    public async Task Consume(ConsumeContext<OrderCreatedEvent> context)
    {
        var msg = context.Message;
        var messageId = context.MessageId?.ToString() ?? Guid.NewGuid().ToString();
        logger.LogDebug("Processing {EventType} — MessageId: {MessageId}", msg.EventType, messageId);

        try
        {
            await DoWorkAsync(msg, context.CancellationToken);
            logger.LogInformation("{EventType} processed — MessageId: {MessageId}", msg.EventType, messageId);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error processing {EventType} — MessageId: {MessageId}", msg.EventType, messageId);
            throw; // let MassTransit retry
        }
    }
}
```

---

## Idempotency

Prefer catching unique constraint violations over pre-checking — avoids race conditions:

```csharp
try
{
    await uow.Notifications.AddAsync(new Notification { OrderId = msg.OrderId }, ct);
    await uow.SaveChangesAsync(ct);
}
catch (DbUpdateException ex) when (ex.InnerException?.Message.Contains("unique") == true)
{
    logger.LogWarning("Duplicate event skipped — OrderId: {OrderId}", msg.OrderId);
}
```

---

## Consumer Chaining

A consumer can publish downstream events after `SaveChangesAsync`. Inject `IPublishEndpoint` alongside `IUnitOfWork` — same pattern as publishing in services.

---

## Retry Policy (Global)

Configure once in shared bootstrapping — no per-consumer overrides:

```csharp
cfg.UseMessageRetry(retry =>
    retry.Exponential(5, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(5)));
```

5 retries with exponential backoff (2s → 7s → 12s → 17s → 22s), then error queue.

---

## Event vs Sync HTTP

| Scenario | Use |
|----------|-----|
| Side effects in other services (notifications, analytics) | Event (MassTransit) |
| Need a return value to continue current request | Sync HTTP client |
| Payment — initiate sync, react to outcome | Sync HTTP + consume `PaymentSucceededEvent` |
| Fire-and-forget after domain action | Event (MassTransit) |

---

## Adding a New Event

| Step | Where |
|------|-------|
| Define contract (extends `BaseEvent`) | `{Source}.Contracts/Events/` |
| Add Contracts project reference | Consuming service's `.csproj` |
| Publish after `SaveChangesAsync` | Source service |
| Create consumer | `{Consumer}.Application/Consumers/` |

No registration needed — auto-discovered.

---

## Logging Conventions

Always include `MessageId` to trace through retries:

```csharp
logger.LogDebug("Processing {EventType} — MessageId: {MessageId}", msg.EventType, messageId);
logger.LogInformation("{EventType} processed — MessageId: {MessageId}", msg.EventType, messageId);
logger.LogWarning("{EventType} skipped — {Reason}", msg.EventType, reason);
logger.LogError(ex, "Error {EventType} — MessageId: {MessageId}", msg.EventType, messageId);
```
