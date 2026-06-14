from fastapi import Cookie, HTTPException

from app.config import settings
from app.security import decode_token


async def get_current_user(session: str | None = Cookie(default=None)) -> str:
    if not settings.auth_enabled:
        return settings.auth_username
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = decode_token(session)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return username
