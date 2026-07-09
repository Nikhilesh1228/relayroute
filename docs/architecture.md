# RelayRoute architecture

RelayRoute is a backend-focused delivery coordination platform. It is designed around a
simple rule: PostgreSQL owns the delivery truth, while Redis, MongoDB, and Kafka handle
fast auxiliary workloads that can safely degrade when unavailable.

## Components

| Area | Technology | Responsibility |
| --- | --- | --- |
| API | FastAPI | REST endpoints, WebSocket delivery chat, metrics, health checks |
| Auth | JWT | Customer, courier, and dispatcher role gates |
| Transactional store | PostgreSQL / SQLAlchemy | Users, deliveries, handoff offers, audit events, outbox |
| Presence | Redis GEO | Short-lived courier location lookup |
| Chat history | MongoDB | Append-only chat messages per delivery |
| Event streaming | Kafka + outbox table | Delivery-created, assigned, status, and handoff events |
| Operations | Docker, Alembic, GitHub Actions | Local stack, migrations, lint, types, tests |

## Delivery lifecycle

1. A customer creates a delivery with an idempotency key.
2. A dispatcher assigns a courier with optimistic version checking.
3. The courier moves the delivery through allowed status transitions.
4. A courier can propose a relay handoff before expiry.
5. Another courier accepts the handoff, which atomically changes the active courier.
6. Every important action writes an audit event and an outbox event in the same transaction.

## Reliability choices

- Idempotency prevents duplicate delivery creation from client retries.
- Version checks prevent stale dispatcher/courier updates.
- The outbox pattern avoids losing domain events during database/Kafka failures.
- Redis, MongoDB, and Kafka calls are best-effort in development so the core workflow can
  still run locally with only SQLite/PostgreSQL.

