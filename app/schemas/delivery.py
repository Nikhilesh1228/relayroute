from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.delivery import DeliveryStatus


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DeliveryCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    pickup_address: str = Field(min_length=5, max_length=500)
    pickup: Location
    dropoff_address: str = Field(min_length=5, max_length=500)
    dropoff: Location
    package: dict[str, Any]


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    customer_id: str
    courier_id: str | None
    pickup_address: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_address: str
    dropoff_latitude: float
    dropoff_longitude: float
    package: dict[str, Any]
    status: str
    version: int
    relay_count: int
    created_at: datetime
    updated_at: datetime


class AssignCourierRequest(BaseModel):
    courier_id: str
    expected_version: int = Field(ge=1)


class StatusUpdateRequest(BaseModel):
    status: DeliveryStatus
    expected_version: int = Field(ge=1)


class HandoffCreate(BaseModel):
    meetup: Location
    reason: str = Field(min_length=5, max_length=1000)
    expires_at: datetime


class HandoffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    delivery_id: str
    from_courier_id: str
    to_courier_id: str | None
    meetup_latitude: float
    meetup_longitude: float
    reason: str
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class CourierLocationUpdate(Location):
    delivery_id: str | None = None


class NearbyCourier(BaseModel):
    courier_id: str
    distance_km: float


class ChatMessage(BaseModel):
    delivery_id: str
    sender_id: str
    sender_role: str
    text: str
    sent_at: datetime


class DeliveryEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    delivery_id: str
    event_type: str
    actor_id: str
    details: dict[str, Any]
    created_at: datetime
