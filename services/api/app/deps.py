from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuthSession, User
from app.security import decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not access_token:
        return None
    try:
        payload = decode_access_token(access_token)
    except Exception:
        return None

    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_id == payload.get("jti"), AuthSession.revoked_at.is_(None))
        .first()
    )
    if session is None:
        return None

    return db.query(User).filter(User.id == payload.get("sub"), User.deleted_at.is_(None)).first()


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
