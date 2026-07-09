import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./relayroute-test.db")
os.environ.setdefault("JWT_SECRET", "relayroute-test-secret")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("MONGODB_URL", "")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "")

from app.core.config import get_settings
from app.core.security import Principal, create_token, hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.delivery import User, UserRole


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def create_user(role: UserRole, email: str) -> User:
    with SessionLocal() as db:
        user = User(
            email=email,
            display_name=email.split("@", 1)[0].title(),
            password_hash=hash_password("secure-password"),
            role=role.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def bearer(user: User) -> dict[str, str]:
    token = create_token(
        Principal(user_id=user.id, email=user.email, role=user.role), get_settings()
    )
    return {"Authorization": f"Bearer {token}"}


def delivery_payload(idempotency_key: str = "idem-0001") -> dict[str, object]:
    return {
        "idempotency_key": idempotency_key,
        "pickup_address": "Warehouse 18, Udaipur",
        "pickup": {"latitude": 24.5854, "longitude": 73.7125},
        "dropoff_address": "Customer Tower, Sector 4",
        "dropoff": {"latitude": 24.6120, "longitude": 73.6890},
        "package": {"weightKg": 2.4, "category": "electronics"},
    }
