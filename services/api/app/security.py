import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

JWT_ALGORITHM = "HS256"

# ponytail: calls bcrypt directly instead of going through passlib's
# CryptContext. passlib 1.7.4 (last release, effectively unmaintained) has a
# known incompatibility with bcrypt>=4 that misfires its own self-test and
# raises spuriously on ordinary short passwords. bcrypt's own API is a
# two-function interface, so the abstraction layer wasn't buying anything.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> tuple[str, str, datetime]:
    """Returns (token, token_id, expires_at)."""
    settings = get_settings()
    token_id = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_ttl_minutes)
    payload = {"sub": user_id, "jti": token_id, "exp": expires_at}
    token = jwt.encode(payload, settings.auth_secret, algorithm=JWT_ALGORITHM)
    return token, token_id, expires_at


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.auth_secret, algorithms=[JWT_ALGORITHM])
