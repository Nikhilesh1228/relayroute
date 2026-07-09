# RelayRoute

RelayRoute is an original backend project for real-time delivery coordination. It combines
delivery lifecycle APIs, courier geospatial presence, WebSocket chat, Kafka-ready domain
events, and an audited relay-handoff workflow where one courier can transfer an active
delivery to another courier without losing the delivery timeline.

## Why this project exists

Most delivery demos stop at CRUD. RelayRoute focuses on backend decisions interviewers
actually ask about:

- role-based JWT authentication for customers, couriers, and dispatchers
- idempotent delivery creation for safe retries
- optimistic version checks for concurrent assignment/status updates
- Redis GEO for nearby-courier lookup
- MongoDB for append-only delivery chat history
- Kafka outbox events for reliable event streaming
- WebSocket chat with access checks against the delivery owner/courier/dispatcher

## Tech stack

- Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic
- PostgreSQL in Docker, SQLite for local tests
- Redis GEO, MongoDB, Kafka
- Pytest, Ruff, mypy, Docker, GitHub Actions

## Run locally

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

API docs open at `http://localhost:8000/docs`.

## Run the full stack

```bash
docker compose up --build
```

## Key API paths

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | public | Register customer or courier |
| POST | `/api/v1/deliveries` | customer | Create a delivery with idempotency |
| POST | `/api/v1/deliveries/{id}/assign` | dispatcher | Assign a courier |
| POST | `/api/v1/deliveries/{id}/status` | courier/dispatcher | Move delivery status |
| POST | `/api/v1/deliveries/{id}/handoffs` | courier | Propose relay handoff |
| POST | `/api/v1/deliveries/handoffs/{offer_id}/accept` | courier | Accept relay handoff |
| WS | `/api/v1/ws/deliveries/{id}/chat?token=...` | participant | Delivery chat |

More details are in [`docs/architecture.md`](docs/architecture.md) and
[`docs/interview-guide.md`](docs/interview-guide.md).
