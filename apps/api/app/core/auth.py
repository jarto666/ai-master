
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from jwt import PyJWKClient, decode as jwt_decode
from jwt import InvalidTokenError
from app.core.settings import settings


AUTH_COOKIE_NAME = settings.AUTH_COOKIE_NAME
OIDC_AUDIENCE = settings.OIDC_AUDIENCE

# Support generic OIDC provider via env, or fall back to Supabase if SUPABASE_PROJECT_REF is set
SUPABASE_PROJECT_REF = settings.SUPABASE_PROJECT_REF
OIDC_ISSUER = settings.OIDC_ISSUER
OIDC_JWKS_URL = settings.OIDC_JWKS_URL


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


def _extract_bearer_from_authorization_header(authorization: Optional[str]) -> Optional[str]:
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

    print(f"request.headers: {request.headers}")
    token_from_header = _extract_bearer_from_authorization_header(
        request.headers.get("authorization") or request.headers.get("Authorization")
    )
    print(f"token_from_header: {token_from_header}")
    if token_from_header:
        return token_from_header
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")


def require_user(request: Request) -> Dict[str, Any]:
    print(f"require_user")
    if not OIDC_ISSUER or not OIDC_JWKS_URL:
        _raise_misconfigured()
    token = _get_token_from_request(request)
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_cookie_name() -> str:
    return AUTH_COOKIE_NAME


