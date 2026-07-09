from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import Principal, create_token
from app.models.delivery import User, UserRole

from .conftest import bearer, create_user, delivery_payload


def token_for(user: User) -> str:
    return create_token(
        Principal(user_id=user.id, email=user.email, role=user.role), get_settings()
    )


def test_delivery_chat_websocket_echoes_authorized_messages(client: TestClient) -> None:
    customer = create_user(UserRole.CUSTOMER, "customer@example.com")
    courier = create_user(UserRole.COURIER, "courier@example.com")
    dispatcher = create_user(UserRole.DISPATCHER, "dispatcher@example.com")
    delivery = client.post(
        "/api/v1/deliveries", json=delivery_payload(), headers=bearer(customer)
    ).json()
    client.post(
        f"/api/v1/deliveries/{delivery['id']}/assign",
        json={"courier_id": courier.id, "expected_version": 1},
        headers=bearer(dispatcher),
    )

    with client.websocket_connect(
        f"/api/v1/ws/deliveries/{delivery['id']}/chat?token={token_for(customer)}"
    ) as websocket:
        websocket.send_json({"text": "Please call before arrival"})
        message = websocket.receive_json()

    assert message["delivery_id"] == delivery["id"]
    assert message["sender_role"] == "customer"
    assert message["text"] == "Please call before arrival"


def test_presence_endpoints_gracefully_degrade_without_redis(client: TestClient) -> None:
    courier = create_user(UserRole.COURIER, "courier@example.com")
    dispatcher = create_user(UserRole.DISPATCHER, "dispatcher@example.com")

    location = client.post(
        "/api/v1/deliveries/couriers/location",
        json={"latitude": 24.5854, "longitude": 73.7125},
        headers=bearer(courier),
    )
    assert location.status_code == 204

    nearby = client.get(
        "/api/v1/deliveries/couriers/nearby",
        params={"latitude": 24.5854, "longitude": 73.7125, "radius_km": 5},
        headers=bearer(dispatcher),
    )
    assert nearby.status_code == 200
    assert nearby.json() == []
