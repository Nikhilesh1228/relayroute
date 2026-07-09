from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import Principal, create_token, get_current_principal
from app.db.session import get_db
from app.models.delivery import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


def _token(user: User, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(auth_service.as_principal(user), settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    return _token(auth_service.register(db, payload), settings)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    return _token(auth_service.authenticate(db, payload.email, payload.password), settings)


@router.get("/me", response_model=Principal)
def me(principal: Annotated[Principal, Depends(get_current_principal)]) -> Principal:
    return principal
