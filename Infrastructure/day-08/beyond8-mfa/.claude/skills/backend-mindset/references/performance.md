# Performance — Query, Caching, Async

Query patterns, caching strategy, and async principles. Language-independent.

## Query Patterns

### N+1 Problem
Never query inside a loop. Load all needed data before the loop, look up in a map/dict.

```
# Wrong — 1 query for list + 1 query per item
items = get_all_items()
for item in items:
    item.owner = get_user(item.owner_id)   # N queries

# Right — 2 queries total
items = get_all_items()
owner_ids = {item.owner_id for item in items}
owners = get_users_by_ids(owner_ids)       # 1 query
owner_map = {u.id: u for u in owners}
for item in items:
    item.owner = owner_map[item.owner_id]
```

### Projection
Only fetch columns the caller needs — never return full entities when a DTO subset is sufficient.

### Pagination
Always paginate list endpoints. Never return unbounded result sets.

### Read vs Write
Read-only queries don't need change tracking — disable it for performance (ORM-specific but universal concept).

---

## Caching Strategy

| Scenario | Cache type |
|----------|-----------|
| Single instance, non-critical, per-pod OK | In-process cache (e.g., memory cache) |
| Multi-instance, shared state | Distributed cache (Redis, Memcached) |
| Full HTTP response | HTTP output / CDN cache |

**Always set TTL** — never cache without expiry.

**Cache key convention:** `"{service}:{entity}:{id-or-filter}"` — e.g., `"order:123"`, `"products:active"`.

**Invalidation:** Evict or update on write — don't rely on TTL expiry alone for mutable data.

Cache-aside pattern:
```
1. Check cache → hit? return cached value
2. Miss → query source
3. Store in cache with TTL
4. Return value
```

---

## Async Patterns

- **Parallel independent I/O**: when two calls don't depend on each other, run them concurrently
- **CancellationToken**: accept in every async function, propagate down the entire call chain — never swallow or ignore
- **Don't block async**: sync-blocking an async call (`.Result`, `.Wait()`) causes thread starvation under load

---

## Anti-Patterns

| Anti-pattern | Fix |
|---|---|
| Query inside loop (N+1) | Batch load, look up in map |
| Full entity when only 2 fields needed | Project to DTO |
| Unbounded list query | Paginate |
| `cache.get()` without TTL | Always set absolute expiry |
| In-process cache in multi-instance deployment | Distributed cache |
| Ignoring CancellationToken | Accept and propagate everywhere |
| Sync-blocking async calls | Await properly |
