from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_user
from app.models import AuthSession, User
from app.rate_limit import make_rate_limiter
from app.schemas import LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "access_token"
# ponytail: a tighter limit than chat's, since login/register are classic
# credential-stuffing/brute-force and mass-signup targets.
auth_rate_limit = make_rate_limiter(max_requests=10)


def _set_auth_cookie(response: Response, db: Session, user: User) -> None:
    token, token_id, expires_at = create_access_token(user.id)
    db.add(AuthSession(user_id=user.id, token_id=token_id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        expires=expires_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    _set_auth_cookie(response, db, user)
    return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin, preferred_language=user.preferred_language)


@router.post("/login", response_model=UserResponse, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    user = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    _set_auth_cookie(response, db, user)
    return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin, preferred_language=user.preferred_language)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)) -> None:
    if user:
        db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
            {"revoked_at": datetime.now(timezone.utc)}
        )
        db.commit()
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(require_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin, preferred_language=user.preferred_language)
