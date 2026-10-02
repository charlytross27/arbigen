"""Authenticated identities for DB integration tests, without HTTP registration overhead."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.database.models import AuthSession, User


def authenticated_headers(connection: Connection) -> dict[str, str]:
    token = token_urlsafe(32)
    csrf_token = token_urlsafe(32)
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        user = User(email=f"test-{uuid4()}@example.com", name="Test user", password_hash="test-only")
        session.add(user)
        session.flush()
        session.add(AuthSession(
            token_hash=sha256(token.encode()).hexdigest(), user_id=user.id, csrf_token=csrf_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        ))
        session.commit()
    return {"Cookie": f"arbigen_session={token}", "Origin": "http://localhost:4200", "X-CSRF-Token": csrf_token}
