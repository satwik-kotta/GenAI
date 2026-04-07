import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import SessionToken, User
from app.utils.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def verify_google_id_token(token_value: str) -> dict:
    settings = get_settings()
    if not settings.google_oauth_allowed_client_ids:
        raise ValueError("Missing GOOGLE_OAUTH_ALLOWED_CLIENT_IDS or GOOGLE_OAUTH_CLIENT_ID")

    payload = id_token.verify_oauth2_token(
        token_value,
        google_requests.Request(),
        clock_skew_in_seconds=60,
    )

    audience = payload.get("aud")
    if audience not in settings.google_oauth_allowed_client_ids:
        raise ValueError("Token audience is not an allowed Google OAuth client id")

    return payload


def create_or_update_user(db: Session, token_payload: dict) -> User:
    google_sub = token_payload.get("sub")
    email = token_payload.get("email")
    name = token_payload.get("name") or email or "Google User"
    picture_url = token_payload.get("picture")

    if not google_sub or not email:
        raise ValueError("Google token missing required user fields")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            picture_url=picture_url,
        )
        db.add(user)
    else:
        user.email = email
        user.name = name
        user.picture_url = picture_url

    db.commit()
    db.refresh(user)
    return user


def create_session_token(db: Session, user: User) -> SessionToken:
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(days=settings.session_expiry_days)

    session = SessionToken(
        user_id=user.id,
        token=secrets.token_urlsafe(48),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    token_value = credentials.credentials
    session = db.query(SessionToken).filter(SessionToken.token == token_value).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")

    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session token expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return user
