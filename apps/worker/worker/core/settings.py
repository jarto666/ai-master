from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()