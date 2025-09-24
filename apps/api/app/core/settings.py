from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017/mastering"
    RABBITMQ_URL: str = "amqp://app:app@localhost:5678/"
    RMQ_EXCHANGE: str = "mastering.jobs"
    RMQ_EXCHANGE_TYPE: str = "direct"
    RMQ_QUEUE: str = "mastering.process"
    RMQ_ROUTING_KEY: str = "process"

    S3_ENDPOINT: str = "http://localhost:9000"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "minio123"
    S3_BUCKET: str = "audio"

    API_PORT: int = 4000

    AUTH_COOKIE_NAME: str = "auth_token"
    OIDC_AUDIENCE: str = "authenticated"
    SUPABASE_PROJECT_REF: str = "xx"
    OIDC_ISSUER: str = f""
    OIDC_JWKS_URL: str = "https://xx.supabase.co/auth/v1/keys"
    # Optional: when using Supabase (HS256-signed tokens), set this to your project's JWT secret
    SUPABASE_JWT_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()