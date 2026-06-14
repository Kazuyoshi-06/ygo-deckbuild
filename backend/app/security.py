import hmac
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ALGORITHM = "HS256"
_TOKEN_TTL_HOURS = 72


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, settings.secret_key, algorithm=_ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def verify_password(plain: str) -> bool:
    return hmac.compare_digest(plain.encode(), settings.auth_password.encode())
