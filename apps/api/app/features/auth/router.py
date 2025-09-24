from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.auth import (
    OIDC_AUDIENCE,
    OIDC_ISSUER,
    get_cookie_name,
    verify_oidc_token,
    sign_internal_jwt,
    require_user,
)
from app.core.settings import settings
from app.features.users.service import get_or_create_user
from app.core.db import db

router = APIRouter()


COOKIE_NAME = get_cookie_name()
COOKIE_DOMAIN = settings.AUTH_COOKIE_DOMAIN
COOKIE_SECURE = settings.AUTH_COOKIE_SECURE
COOKIE_SAMESITE = settings.AUTH_COOKIE_SAMESITE


@router.post("/auth/session")
async def establish_session(request: Request, response: Response) -> Dict[str, Any]:
    # Validate external OIDC token from Authorization header
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide OIDC token via Authorization header",
        )
    oidc_token = auth_header.split(" ", 1)[1]

    oidc_claims = verify_oidc_token(oidc_token)

    # Extract user identity
    email = oidc_claims.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC token missing email")

    # Try common locations for a display name
    name: str | None = (
        oidc_claims.get("name")
        or (oidc_claims.get("user_metadata") or {}).get("name")
        or (oidc_claims.get("user_metadata") or {}).get("full_name")
        or (oidc_claims.get("raw_user_meta_data") or {}).get("name")
    )

    # Upsert user and issue our own compact JWT
    user_doc = await get_or_create_user(email=email, name=name)
    user_id = str(user_doc["_id"])  # MongoDB ObjectId -> str

    internal_jwt = sign_internal_jwt(email=email, user_id=user_id, expires_in_seconds=settings.INTERNAL_JWT_EXPIRES_SECONDS)

    response.set_cookie(
        key=COOKIE_NAME,
        value=internal_jwt,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,  # 'lax' recommended
        domain=COOKIE_DOMAIN,
        max_age=settings.INTERNAL_JWT_EXPIRES_SECONDS,
        path="/",
    )
    return {"ok": True, "id": user_id, "email": email, "aud": oidc_claims.get("aud", OIDC_AUDIENCE), "iss": oidc_claims.get("iss", OIDC_ISSUER)}


@router.get("/auth/profile")
async def get_profile(request: Request) -> Dict[str, Any]:
    """Return the current user's profile using our internal JWT.

    Looks up the user document in MongoDB and returns a minimal profile.
    """
    claims = require_user(request)
    user_id = claims.get("id")
    email = claims.get("email")

    users = db.get_collection("users")
    doc = await users.find_one({"email": email})

    if not doc:
        # Should not happen because we upsert on session establishment, but handle gracefully
        return {"id": user_id, "email": email, "name": None}

    # Normalize ObjectId and datetimes
    profile: Dict[str, Any] = {
        "id": str(doc.get("_id", user_id)),
        "email": doc.get("email", email),
        "name": doc.get("name"),
    }
    return profile


@router.post("/auth/logout")
async def logout(response: Response) -> Dict[str, Any]:
    response.delete_cookie(key=COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")
    return {"ok": True}


