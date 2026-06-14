from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from app.config import settings
from app.security import create_token, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "session"
_COOKIE_TTL = 72 * 3600


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(data: LoginIn, response: Response) -> dict:
    if not settings.auth_enabled:
        return {"username": settings.auth_username, "auth_enabled": False}

    if data.username != settings.auth_username or not verify_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(data.username)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_TTL,
        secure=settings.environment == "production",
    )
    return {"username": data.username, "auth_enabled": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me(session: str | None = Cookie(default=None)) -> dict:
    if not settings.auth_enabled:
        return {"username": settings.auth_username, "auth_enabled": False}
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = decode_token(session)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"username": username, "auth_enabled": True}
