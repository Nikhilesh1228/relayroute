from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.adapters import presence
from app.core.security import Principal, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.delivery import (
    AssignCourierRequest,
    CourierLocationUpdate,
    DeliveryCreate,
    DeliveryEventRead,
    DeliveryRead,
    HandoffCreate,
    HandoffRead,
    NearbyCourier,
    StatusUpdateRequest,
)
from app.services import delivery_service

router = APIRouter(prefix="/deliveries", tags=["deliveries"])
Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: DeliveryCreate,
    db: Db,
    principal: Annotated[Principal, Depends(require_roles("customer"))],
) -> DeliveryRead:
    return DeliveryRead.model_validate(
        delivery_service.create_delivery(db, payload, principal.user_id)
    )


@router.post("/couriers/location", status_code=204)
def update_courier_location(
    payload: CourierLocationUpdate,
    principal: Annotated[Principal, Depends(require_roles("courier"))],
) -> None:
    presence.update_location(principal.user_id, payload.latitude, payload.longitude)


@router.get("/couriers/nearby", response_model=list[NearbyCourier])
def nearby_couriers(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    _principal: Annotated[Principal, Depends(require_roles("dispatcher"))],
    radius_km: Annotated[float, Query(gt=0, le=50)] = 5.0,
) -> list[NearbyCourier]:
    return [
        NearbyCourier(courier_id=courier_id, distance_km=distance)
        for courier_id, distance in presence.nearby_couriers(latitude, longitude, radius_km)
    ]


@router.get("/{delivery_id}", response_model=DeliveryRead)
def get_delivery(
    delivery_id: str,
    db: Db,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DeliveryRead:
    delivery = delivery_service.get_delivery(db, delivery_id)
    delivery_service.assert_access(delivery, principal)
    return DeliveryRead.model_validate(delivery)


@router.post("/{delivery_id}/assign", response_model=DeliveryRead)
def assign_courier(
    delivery_id: str,
    payload: AssignCourierRequest,
    db: Db,
    principal: Annotated[Principal, Depends(require_roles("dispatcher"))],
) -> DeliveryRead:
    return DeliveryRead.model_validate(
        delivery_service.assign_courier(
            db,
            delivery_id,
            payload.courier_id,
            payload.expected_version,
            principal.user_id,
        )
    )


@router.post("/{delivery_id}/status", response_model=DeliveryRead)
def update_status(
    delivery_id: str,
    payload: StatusUpdateRequest,
    db: Db,
    principal: Annotated[Principal, Depends(require_roles("courier", "dispatcher"))],
) -> DeliveryRead:
    return DeliveryRead.model_validate(
        delivery_service.update_status(
            db, delivery_id, payload.status, payload.expected_version, principal
        )
    )


@router.post("/{delivery_id}/handoffs", response_model=HandoffRead, status_code=201)
def propose_handoff(
    delivery_id: str,
    payload: HandoffCreate,
    db: Db,
    principal: Annotated[Principal, Depends(require_roles("courier"))],
) -> HandoffRead:
    return HandoffRead.model_validate(
        delivery_service.propose_handoff(db, delivery_id, payload, principal.user_id)
    )


@router.post("/handoffs/{offer_id}/accept", response_model=HandoffRead)
def accept_handoff(
    offer_id: str,
    db: Db,
    principal: Annotated[Principal, Depends(require_roles("courier"))],
) -> HandoffRead:
    return HandoffRead.model_validate(
        delivery_service.accept_handoff(db, offer_id, principal.user_id)
    )


@router.get("/{delivery_id}/timeline", response_model=list[DeliveryEventRead])
def timeline(
    delivery_id: str,
    db: Db,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[DeliveryEventRead]:
    return [
        DeliveryEventRead.model_validate(event)
        for event in delivery_service.timeline(db, delivery_id, principal)
    ]
