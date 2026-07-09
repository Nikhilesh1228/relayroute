# RelayRoute interview preparation

Do not memorize only the resume bullet. Run the endpoints and explain the trade-offs.

## Project explanation

“RelayRoute is a real-time delivery backend. Customers create deliveries, dispatchers
assign couriers, and couriers update status or transfer work through a relay-handoff
workflow. PostgreSQL stores the source of truth, Redis GEO tracks live courier presence,
MongoDB stores chat history, Kafka receives delivery events through a transactional
outbox, and FastAPI WebSockets support delivery chat.”

## Follow-up questions

### Why is PostgreSQL the source of truth?

Delivery assignment, status, version, and relay count need transactions and constraints.
PostgreSQL gives strong consistency for these decisions. Redis, MongoDB, and Kafka are
supporting systems, not decision-makers.

### What is the relay-handoff feature?

The current courier can open a handoff offer with a meetup point, reason, and expiry.
Another courier accepts it. The service checks expiry, prevents accepting your own offer,
locks the delivery, changes the active courier, increments the relay count, and writes an
audit event.

### Why use optimistic versioning?

Two dispatchers or couriers may update the same delivery at the same time. The expected
version makes stale updates fail with a conflict instead of silently overwriting newer
state.

### Why use Redis GEO?

Courier location changes frequently and expires quickly. Redis GEO supports fast
nearby-courier lookup without burdening the transactional database.

### Why store chat in MongoDB?

Chat messages are append-only documents with flexible metadata. MongoDB works well for
that shape, while delivery ownership and access control are still validated against
PostgreSQL before a WebSocket connection opens.

### What problem does the outbox solve?

If the service writes PostgreSQL and Kafka separately, it can commit one and fail the
other. The outbox writes the event inside the database transaction, then a publisher
retries Kafka delivery later.

### What would you improve for production?

Use managed Postgres/Redis/Kafka, move outbox publishing to a worker, add refresh tokens,
rate limits, OpenTelemetry tracing, dead-letter topics, WebSocket fan-out through Redis
pub/sub, stronger authorization policies, and load tests for peak delivery windows.

## Hands-on checklist

1. Register a customer and courier, then create a delivery.
2. Insert or seed a dispatcher and assign a courier.
3. Attempt a stale update and explain the 409 conflict.
4. Open a WebSocket chat and send a delivery message.
5. Propose and accept a relay handoff; show the timeline entries.

