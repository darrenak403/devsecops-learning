# Events — Event-Driven Patterns

Inter-service messaging, event contracts, consumers, retry, idempotency. Language-independent.

## When to Use Events

Use events (not direct HTTP calls) when:
- The producer doesn't need the consumer's result synchronously
- Multiple consumers may react to the same fact
- You want to decouple services so either can fail/restart independently
- The operation is long-running or involves side effects outside the transaction boundary

---

## Event Contract Design

Events represent **facts** that happened, not commands:
- Good: `OrderPlaced`, `UserRegistered`, `PaymentFailed`
- Bad: `SendEmail`, `UpdateInventory`

### Contract rules
- Include all data consumers will need — don't make them call back to get more
- Include `eventId` (for deduplication), `occurredAt` timestamp, and `version`
- Treat published contracts as **breaking changes** — bump version if shape changes, keep old version running until consumers migrate
- Use a flat structure where possible — avoid deep nesting

```json
{
  "eventId": "uuid",
  "eventType": "order.placed",
  "version": "1",
  "occurredAt": "ISO-8601",
  "data": { ... }
}
```

---

## Consumer Design

- Consumers must be **idempotent** — the same message delivered twice must produce the same result
  - Store processed `eventId` values; skip if already seen
- Each consumer handles **one** event type — single responsibility
- Keep consumer logic thin: validate → apply → persist → acknowledge
- Don't call other services synchronously inside a consumer (risk of cascade failure)

---

## Retry & Dead Letter

- Configure retry with backoff (e.g., 3 retries: 5s, 30s, 5m)
- After max retries, route to a dead-letter queue (DLQ) — never silently drop messages
- Monitor DLQ — a growing DLQ is an incident
- Reprocess from DLQ after fixing the root cause

---

## Ordering & Consistency

- Message brokers typically guarantee **at-least-once** delivery, not exactly-once → idempotency is mandatory
- Don't assume ordering across different event types
- For strict ordering (e.g., account events for one user), use a partition/shard key based on the aggregate ID

---

## Outbox Pattern

For operations that must publish an event AND write to DB atomically:
1. Write event to an `outbox` table in the same DB transaction as the domain change
2. A background process reads the outbox and publishes to the broker
3. Mark outbox entry as published after broker ACK

This prevents the "wrote to DB but failed to publish" split-brain problem.
