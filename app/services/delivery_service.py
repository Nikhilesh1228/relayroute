from datetime import UTC, datetime
from typing import Any, cast

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.adapters import events
from app.core.security import Principal
from app.models.delivery import (
    Delivery,
    DeliveryEvent,
    DeliveryStatus,
    HandoffOffer,
    HandoffStatus,
    User,
    UserRole,
)
from app.schemas.delivery import DeliveryCreate, HandoffCreate

TRANSITIONS = {
    DeliveryStatus.ASSIGNED.value: {DeliveryStatus.PICKED_UP.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.PICKED_UP.value: {DeliveryStatus.IN_TRANSIT.value},
    DeliveryStatus.IN_TRANSIT.value: {DeliveryStatus.DELIVERED.value},
}


def _audit(
    db: Session,
    *,
    delivery_id: str,
    event_type: str,
    actor_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        DeliveryEvent(
            delivery_id=delivery_id,
            event_type=event_type,
            actor_id=actor_id,
            details=details or {},
        )
    )


def get_delivery(db: Session, delivery_id: str) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


def assert_access(delivery: Delivery, principal: Principal) -> None:
    allowed = principal.role == UserRole.DISPATCHER.value or principal.user_id in {
        delivery.customer_id,
        delivery.courier_id,
    }
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delivery access denied")


def create_delivery(db: Session, payload: DeliveryCreate, customer_id: str) -> Delivery:
    existing = db.scalar(
        select(Delivery).where(Delivery.idempotency_key == payload.idempotency_key)
    )
    if existing:
        if existing.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Idempotency key reused"
            )
        return existing
    delivery = Delivery(
        idempotency_key=payload.idempotency_key,
        customer_id=customer_id,
        pickup_address=payload.pickup_address,
        pickup_latitude=payload.pickup.latitude,
        pickup_longitude=payload.pickup.longitude,
        dropoff_address=payload.dropoff_address,
        dropoff_latitude=payload.dropoff.latitude,
        dropoff_longitude=payload.dropoff.longitude,
        package=payload.package,
    )
    db.add(delivery)
    db.flush()
    _audit(db, delivery_id=delivery.id, event_type="delivery.created", actor_id=customer_id)
    events.enqueue(
        db,
        topic="delivery.created",
        event_key=delivery.id,
        payload={"delivery_id": delivery.id, "customer_id": customer_id},
    )
    db.commit()
    db.refresh(delivery)
    events.publish_best_effort(db)
    return delivery


def assign_courier(
    db: Session, delivery_id: str, courier_id: str, expected_version: int, actor_id: str
) -> Delivery:
    courier = db.get(User, courier_id)
    if courier is None or courier.role != UserRole.COURIER.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid courier"
        )
    result = cast(
        CursorResult[Any],
        db.execute(
            update(Delivery)
            .where(
                Delivery.id == delivery_id,
                Delivery.status == DeliveryStatus.CREATED.value,
                Delivery.version == expected_version,
            )
            .values(
                courier_id=courier_id,
                status=DeliveryStatus.ASSIGNED.value,
                version=expected_version + 1,
                updated_at=datetime.now(UTC),
            )
        ),
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment conflict")
    _audit(
        db,
        delivery_id=delivery_id,
        event_type="delivery.assigned",
        actor_id=actor_id,
        details={"courier_id": courier_id},
    )
    events.enqueue(
        db,
        topic="delivery.assigned",
        event_key=delivery_id,
        payload={"delivery_id": delivery_id, "courier_id": courier_id},
    )
    db.commit()
    events.publish_best_effort(db)
    return get_delivery(db, delivery_id)


def update_status(
    db: Session,
    delivery_id: str,
    target: DeliveryStatus,
    expected_version: int,
    principal: Principal,
) -> Delivery:
    delivery = get_delivery(db, delivery_id)
    assert_access(delivery, principal)
    if principal.role == UserRole.COURIER.value and delivery.courier_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Courier not assigned")
    if target.value not in TRANSITIONS.get(delivery.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Invalid status transition"
        )
    result = cast(
        CursorResult[Any],
        db.execute(
            update(Delivery)
            .where(Delivery.id == delivery_id, Delivery.version == expected_version)
            .values(
                status=target.value,
                version=expected_version + 1,
                updated_at=datetime.now(UTC),
            )
        ),
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delivery changed; reload")
    _audit(
        db,
        delivery_id=delivery_id,
        event_type="delivery.status.changed",
        actor_id=principal.user_id,
        details={"from": delivery.status, "to": target.value},
    )
    events.enqueue(
        db,
        topic="delivery.status.changed",
        event_key=delivery_id,
        payload={"delivery_id": delivery_id, "status": target.value},
    )
    db.commit()
    events.publish_best_effort(db)
    return get_delivery(db, delivery_id)


def propose_handoff(
    db: Session, delivery_id: str, payload: HandoffCreate, courier_id: str
) -> HandoffOffer:
    delivery = get_delivery(db, delivery_id)
    if delivery.courier_id != courier_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Courier not assigned")
    if delivery.status not in {
        DeliveryStatus.ASSIGNED.value,
        DeliveryStatus.PICKED_UP.value,
        DeliveryStatus.IN_TRANSIT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Delivery cannot be relayed"
        )
    expires_at = payload.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Expiry must be future")
    offer = HandoffOffer(
        delivery_id=delivery_id,
        from_courier_id=courier_id,
        meetup_latitude=payload.meetup.latitude,
        meetup_longitude=payload.meetup.longitude,
        reason=payload.reason,
        expires_at=expires_at,
    )
    db.add(offer)
    db.flush()
    _audit(
        db,
        delivery_id=delivery_id,
        event_type="handoff.proposed",
        actor_id=courier_id,
        details={"handoff_id": offer.id},
    )
    events.enqueue(
        db,
        topic="delivery.handoff.proposed",
        event_key=delivery_id,
        payload={"delivery_id": delivery_id, "handoff_id": offer.id},
    )
    db.commit()
    db.refresh(offer)
    events.publish_best_effort(db)
    return offer


def accept_handoff(db: Session, offer_id: str, courier_id: str) -> HandoffOffer:
    offer = db.scalar(select(HandoffOffer).where(HandoffOffer.id == offer_id).with_for_update())
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handoff not found")
    expires_at = offer.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if offer.status != HandoffStatus.OPEN.value or expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Handoff is not open")
    if offer.from_courier_id == courier_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cannot accept own handoff"
        )
    delivery = db.scalar(select(Delivery).where(Delivery.id == offer.delivery_id).with_for_update())
    if delivery is None or delivery.courier_id != offer.from_courier_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Delivery assignment changed"
        )
    delivery.courier_id = courier_id
    delivery.relay_count += 1
    delivery.version += 1
    offer.to_courier_id = courier_id
    offer.status = HandoffStatus.ACCEPTED.value
    offer.accepted_at = datetime.now(UTC)
    _audit(
        db,
        delivery_id=delivery.id,
        event_type="handoff.accepted",
        actor_id=courier_id,
        details={
            "handoff_id": offer.id,
            "from_courier_id": offer.from_courier_id,
            "to_courier_id": courier_id,
        },
    )
    events.enqueue(
        db,
        topic="delivery.handoff.accepted",
        event_key=delivery.id,
        payload={
            "delivery_id": delivery.id,
            "handoff_id": offer.id,
            "from_courier_id": offer.from_courier_id,
            "to_courier_id": courier_id,
        },
    )
    db.commit()
    db.refresh(offer)
    events.publish_best_effort(db)
    return offer


def timeline(db: Session, delivery_id: str, principal: Principal) -> list[DeliveryEvent]:
    delivery = get_delivery(db, delivery_id)
    assert_access(delivery, principal)
    return list(
        db.scalars(
            select(DeliveryEvent)
            .where(DeliveryEvent.delivery_id == delivery_id)
            .order_by(DeliveryEvent.created_at)
        )
    )
