from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.delivery import UserRole

from .conftest import bearer, create_user, delivery_payload


def create_delivery(client: TestClient, customer_headers: dict[str, str]) -> dict[str, object]:
    response = client.post("/api/v1/deliveries", json=delivery_payload(), headers=customer_headers)
    assert response.status_code == 201
    return response.json()


def test_delivery_creation_is_idempotent_and_audited(client: TestClient) -> None:
    customer = create_user(UserRole.CUSTOMER, "customer@example.com")

    first = create_delivery(client, bearer(customer))
    second = client.post("/api/v1/deliveries", json=delivery_payload(), headers=bearer(customer))

    assert second.status_code == 201
    assert second.json()["id"] == first["id"]

    timeline = client.get(f"/api/v1/deliveries/{first['id']}/timeline", headers=bearer(customer))
    assert timeline.status_code == 200
    assert [event["event_type"] for event in timeline.json()] == ["delivery.created"]


def test_dispatcher_assignment_status_transitions_and_conflicts(
    client: TestClient,
) -> None:
    customer = create_user(UserRole.CUSTOMER, "customer@example.com")
    courier = create_user(UserRole.COURIER, "courier@example.com")
    dispatcher = create_user(UserRole.DISPATCHER, "dispatcher@example.com")
    delivery = create_delivery(client, bearer(customer))

    assigned = client.post(
        f"/api/v1/deliveries/{delivery['id']}/assign",
        json={"courier_id": courier.id, "expected_version": 1},
        headers=bearer(dispatcher),
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["version"] == 2

    stale = client.post(
        f"/api/v1/deliveries/{delivery['id']}/assign",
        json={"courier_id": courier.id, "expected_version": 1},
        headers=bearer(dispatcher),
    )
    assert stale.status_code == 409

    picked_up = client.post(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "picked_up", "expected_version": 2},
        headers=bearer(courier),
    )
    assert picked_up.status_code == 200
    assert picked_up.json()["version"] == 3

    invalid_jump = client.post(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "delivered", "expected_version": 3},
        headers=bearer(courier),
    )
    assert invalid_jump.status_code == 409


def test_relay_handoff_changes_courier_and_preserves_timeline(
    client: TestClient,
) -> None:
    customer = create_user(UserRole.CUSTOMER, "customer@example.com")
    courier_a = create_user(UserRole.COURIER, "courier-a@example.com")
    courier_b = create_user(UserRole.COURIER, "courier-b@example.com")
    dispatcher = create_user(UserRole.DISPATCHER, "dispatcher@example.com")
    delivery = create_delivery(client, bearer(customer))

    client.post(
        f"/api/v1/deliveries/{delivery['id']}/assign",
        json={"courier_id": courier_a.id, "expected_version": 1},
        headers=bearer(dispatcher),
    )
    offer = client.post(
        f"/api/v1/deliveries/{delivery['id']}/handoffs",
        json={
            "meetup": {"latitude": 24.6000, "longitude": 73.7000},
            "reason": "Battery low; handing off near the pickup corridor",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
        headers=bearer(courier_a),
    )
    assert offer.status_code == 201

    own_offer = client.post(
        f"/api/v1/deliveries/handoffs/{offer.json()['id']}/accept",
        headers=bearer(courier_a),
    )
    assert own_offer.status_code == 409

    accepted = client.post(
        f"/api/v1/deliveries/handoffs/{offer.json()['id']}/accept",
        headers=bearer(courier_b),
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    fetched = client.get(f"/api/v1/deliveries/{delivery['id']}", headers=bearer(dispatcher))
    assert fetched.json()["courier_id"] == courier_b.id
    assert fetched.json()["relay_count"] == 1

    timeline = client.get(
        f"/api/v1/deliveries/{delivery['id']}/timeline", headers=bearer(dispatcher)
    )
    event_names = [event["event_type"] for event in timeline.json()]
    assert "handoff.proposed" in event_names
    assert "handoff.accepted" in event_names
