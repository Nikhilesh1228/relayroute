# RelayRoute: Real-Time Delivery Tracking Backend

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-WebSockets-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis GEO](https://img.shields.io/badge/Redis-GEO%20Indexing-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Kafka](https://img.shields.io/badge/Kafka-Outbox%20Pattern-231F20?style=flat&logo=apachekafka&logoColor=white)](https://kafka.apache.org/)

RelayRoute is an asynchronous, event-driven backend service designed for real-time courier tracking, driver presence management, live customer updates, and message routing.

## 📌 System Architecture
RelayRoute solves the problem of high-frequency location updates and reliable state delivery through:
- **Redis GEO Spatial Indexing:** Fast store and lookup of active courier latitude/longitude coordinates.
- **WebSocket Streaming Gateway:** Bi-directional live location broadcasts to customer web/mobile interfaces.
- **Transactional Outbox Pattern:** Ensures zero message loss when relaying state changes to Apache Kafka event streams.
- **Multi-Store Persistence:** PostgreSQL for orders and accounts, MongoDB for real-time delivery chat logs.

---

## ✨ Key Features
- **Live Location Streaming:** Low-latency WebSockets handling driver updates and consumer subscriptions.
- **Spatial Proximity Queries:** Redis GEO commands (`GEOADD`, `GEORADIUS`) for nearest courier dispatch.
- **Guaranteed Event Delivery:** Relays database mutations to Kafka via transactional outbox workers.
- **Secured Communications:** JWT authentication for WebSocket handshake and REST endpoints.

---

## 🛠️ Tech Stack
- **Core Framework:** Python, FastAPI, WebSockets
- **State & Messaging:** Redis (GEO), PostgreSQL, MongoDB, Apache Kafka
- **Migrations & Tools:** Alembic, SQLAlchemy, Docker Compose

---

## 🚀 Quick Start
1. Clone the repository:
   ```bash
   git clone https://github.com/Nikhilesh1228/relayroute.git
   cd relayroute
   ```

2. Launch environment with Docker Compose:
   ```bash
   docker compose up --build -d
   ```

3. Access Endpoints:
   - REST Documentation: `http://localhost:8000/docs`
   - WebSocket Connection: `ws://localhost:8000/ws/tracking/{delivery_id}`
