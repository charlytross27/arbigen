"""Private registration and revocable, server-side browser sessions."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.models import AuthSession, User
from app.database.session import get_session


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
password_hash = PasswordHash.recommended()
SESSION_DAYS = 7


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=12, max_length=128)
    invitation_code: str = Field(min_length=1, max_length=256)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        name = " ".join(value.split())
        if not name:
            raise ValueError("El nombre es obligatorio.")
        return name


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str


class AuthRead(BaseModel):
    user: UserRead
    csrf_token: str


def _cookie_name(settings: Settings) -> str:
    return "__Host-arbigen_session" if settings.environment == "production" else "arbigen_session"


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def verify_request_origin(request: Request, settings: Settings = Depends(get_settings)) -> None:
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="Origen no permitido.")


def current_session(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> tuple[AuthSession, User]:
    token = request.cookies.get(_cookie_name(settings))
    if not token or len(token) > 128:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    row = session.get(AuthSession, _token_hash(token))
    expires_at = row.expires_at if row is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if row is None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="La sesión expiró. Inicia sesión de nuevo.")
    user = session.get(User, row.user_id)
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        verify_request_origin(request, settings)
        supplied = request.headers.get("x-csrf-token", "")
        if not compare_digest(supplied, row.csrf_token):
            raise HTTPException(status_code=403, detail="Token de seguridad inválido.")
    return row, user


def current_user_id(identity: tuple[AuthSession, User] = Depends(current_session)) -> UUID:
    return identity[1].id


def _issue_session(session: Session, user: User, response: Response, settings: Settings) -> AuthRead:
    token = token_urlsafe(32)
    csrf_token = token_urlsafe(32)
    session.add(AuthSession(
        token_hash=_token_hash(token), user_id=user.id, csrf_token=csrf_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    ))
    session.commit()
    response.set_cookie(
        key=_cookie_name(settings), value=token, max_age=SESSION_DAYS * 86400,
        httponly=True, secure=settings.environment == "production", samesite="strict", path="/",
    )
    return AuthRead(user=UserRead.model_validate(user), csrf_token=csrf_token)


@lru_cache
def _dummy_password_hash() -> str:
    return password_hash.hash("invalid-password-for-equal-work")


@router.post("/register", response_model=AuthRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_request_origin)])
def register(
    payload: RegisterRequest,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthRead:
    configured_code = settings.auth_registration_code
    if not configured_code:
        raise HTTPException(status_code=503, detail="El registro privado aún no está configurado.")
    if not compare_digest(payload.invitation_code, configured_code):
        raise HTTPException(status_code=403, detail="Código de invitación inválido.")
    email = str(payload.email).lower()
    if email.endswith(".invalid"):
        raise HTTPException(status_code=422, detail="Usa una dirección de correo válida.")
    user = User(email=email, name=payload.name, password_hash=password_hash.hash(payload.password))
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear la cuenta con ese correo.") from None
    return _issue_session(session, user, response, settings)


@router.post("/login", response_model=AuthRead, dependencies=[Depends(verify_request_origin)])
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthRead:
    user = session.scalar(select(User).where(User.email == str(payload.email).lower()))
    stored_hash = user.password_hash if user and user.password_hash else _dummy_password_hash()
    valid = password_hash.verify(payload.password, stored_hash)
    if not user or not user.password_hash or not valid:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    return _issue_session(session, user, response, settings)


@router.get("/me", response_model=AuthRead)
def me(identity: tuple[AuthSession, User] = Depends(current_session)) -> AuthRead:
    auth_session, user = identity
    return AuthRead(user=UserRead.model_validate(user), csrf_token=auth_session.csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    identity: tuple[AuthSession, User] = Depends(current_session),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    session.delete(identity[0])
    session.commit()
    response.delete_cookie(
        _cookie_name(settings), path="/", secure=settings.environment == "production",
        httponly=True, samesite="strict",
    )
