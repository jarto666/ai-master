from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = ""
    RABBITMQ_URL: str = ""
    RMQ_EXCHANGE: str = ""
    RMQ_EXCHANGE_TYPE: str = ""
    RMQ_QUEUE: str = ""
    RMQ_ROUTING_KEY: str = ""

    # Events (worker -> API)
    RMQ_EVENTS_EXCHANGE: str = ""
    RMQ_EVENTS_EXCHANGE_TYPE: str = ""
    RMQ_EVENTS_QUEUE: str = ""
    RMQ_EVENTS_ROUTING_KEY: str = ""

    S3_ENDPOINT: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""

    API_PORT: int = 4000

    AUTH_COOKIE_NAME: str = ""
    OIDC_AUDIENCE: str = ""
    SUPABASE_PROJECT_REF: str = ""
    OIDC_ISSUER: str = f""
    OIDC_JWKS_URL: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Internal JWT (issued by our API) config
    INTERNAL_JWT_SECRET: str = ""
    INTERNAL_JWT_ALGORITHM: str = ""
    INTERNAL_JWT_EXPIRES_SECONDS: int = 60 * 60 * 24 * 365  # 1 year

    AUTH_COOKIE_DOMAIN: str = ""
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()