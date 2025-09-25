from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # RabbitMQ
    RABBITMQ_URL: str = ""
    RMQ_EXCHANGE: str = ""
    RMQ_EXCHANGE_TYPE: str = ""
    RMQ_QUEUE: str = ""
    RMQ_ROUTING_KEY: str = ""

    # Events (worker -> API)
    RMQ_EVENTS_EXCHANGE: str = ""
    RMQ_EVENTS_EXCHANGE_TYPE: str = ""
    RMQ_EVENTS_ROUTING_KEY_PROCESSING: str = ""
    RMQ_EVENTS_ROUTING_KEY_DONE: str = ""
    RMQ_EVENTS_ROUTING_KEY_FAILED: str = ""

    # S3/MinIO
    S3_ENDPOINT: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
