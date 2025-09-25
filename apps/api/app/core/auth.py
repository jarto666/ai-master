from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, Optional

from app.core.settings import settings
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError, PyJWKClient
from jwt import decode as jwt_decode
from jwt import encode as jwt_encode

AUTH_COOKIE_NAME = settings.AUTH_COOKIE_NAME
OIDC_AUDIENCE = settings.OIDC_AUDIENCE

# Support generic OIDC provider via env, or fall back to Supabase if SUPABASE_PROJECT_REF is set
SUPABASE_PROJECT_REF = settings.SUPABASE_PROJECT_REF
OIDC_ISSUER = settings.OIDC_ISSUER
OIDC_JWKS_URL = settings.OIDC_JWKS_URL

# Internal JWT configuration
INTERNAL_JWT_SECRET = settings.INTERNAL_JWT_SECRET
INTERNAL_JWT_ALGORITHM = settings.INTERNAL_JWT_ALGORITHM
INTERNAL_JWT_EXPIRES_SECONDS = settings.INTERNAL_JWT_EXPIRES_SECONDS


def _raise_misconfigured() -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="OIDC issuer/JWKS not configured",
    )


@lru_cache(maxsize=1)
def get_jwk_client() -> PyJWKClient:
    if not OIDC_JWKS_URL:
        _raise_misconfigured()
    return PyJWKClient(OIDC_JWKS_URL)


def _extract_bearer_from_authorization_header(
    authorization: Optional[str],
) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1]


def _get_token_from_request(request: Request) -> str:
    # Prefer cookie, fallback to Authorization header
    token_from_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if token_from_cookie:
        return token_from_cookie

    token_from_header = _extract_bearer_from_authorization_header(
        request.headers.get("authorization") or request.headers.get("Authorization")
    )
    if token_from_header:
        return token_from_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
    )


def require_user(request: Request) -> Dict[str, Any]:
    """Validate our internal JWT from cookie or Authorization header.

    Returns claims containing at least 'id' and 'email'.
    """
    token = _get_token_from_request(request)
    try:
        claims = jwt_decode(
            token,
            INTERNAL_JWT_SECRET,
            algorithms=[INTERNAL_JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        if "id" not in claims or "email" not in claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return claims
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def verify_oidc_token(token: str) -> Dict[str, Any]:
    """Verify an external OIDC provider token using JWKS.

    Used only during session establishment to authenticate the user
    before issuing our own internal JWT.
    """
    if not OIDC_ISSUER or not OIDC_JWKS_URL:
        _raise_misconfigured()
    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token).key
        claims = jwt_decode(
            token,
            signing_key,
            algorithms=["RS256", "RS512", "ES256"],
            audience=OIDC_AUDIENCE,
            issuer=OIDC_ISSUER,
            options={"verify_at_hash": False},
        )
        return claims
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_cookie_name() -> str:
    return AUTH_COOKIE_NAME


def sign_internal_jwt(
    *, email: str, user_id: str, expires_in_seconds: Optional[int] = None
) -> str:
    """Create a short payload JWT containing only 'id' and 'email'.

    Adds standard 'iat' and 'exp' for security.
    """
    now = datetime.now(tz=timezone.utc)
    ttl = (
        expires_in_seconds
        if expires_in_seconds is not None
        else INTERNAL_JWT_EXPIRES_SECONDS
    )
    payload: Dict[str, Any] = {
        "id": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt_encode(payload, INTERNAL_JWT_SECRET, algorithm=INTERNAL_JWT_ALGORITHM)
