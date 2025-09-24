import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import (
    OIDC_AUDIENCE,
    OIDC_ISSUER,
    get_cookie_name,
    require_user,
)

router = APIRouter()


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


COOKIE_NAME = get_cookie_name()
COOKIE_DOMAIN = os.environ.get("AUTH_COOKIE_DOMAIN")
COOKIE_SECURE = _bool_env("AUTH_COOKIE_SECURE", True)
COOKIE_SAMESITE = os.environ.get("AUTH_COOKIE_SAMESITE", "lax")


@router.post("/auth/session")
async def establish_session(request: Request, response: Response) -> Dict[str, Any]:
    # Reuse the same verification used by protected routes.
    print(f"establish_session")
    claims = require_user(request)
    print(f"claims: {claims}")

    # Align cookie expiry to token expiry when available.
    max_age: int | None = None
    if "exp" in claims:
        exp_dt = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        seconds = int((exp_dt - now).total_seconds())
        if seconds > 0:
            max_age = seconds

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # If token came via Authorization header, re-extract it
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide token via cookie or Authorization header")
        token = auth_header.split(" ", 1)[1]

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,  # 'lax' recommended
        domain=COOKIE_DOMAIN,
        max_age=max_age,
        path="/",
    )
    return {"ok": True, "sub": claims.get("sub"), "aud": claims.get("aud", OIDC_AUDIENCE), "iss": claims.get("iss", OIDC_ISSUER)}


@router.post("/auth/logout")
async def logout(response: Response) -> Dict[str, Any]:
    response.delete_cookie(key=COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")
    return {"ok": True}


