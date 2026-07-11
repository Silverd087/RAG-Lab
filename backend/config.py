from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    qdrant_url:str = "http://localhost:6333yy"
    redis_url: str = "redis://localhost:6379"
    rabbitmq_url:str = "amqp://guest:guest@localhost:5672//"
    google_api_key:str
    cohere_api_key:str
    postgres_user:str
    postgres_password:str
    postgres_host:str = "localhost"
    postgres_db:str
    postgres_test_db:str
    minio_endpoint:str = "localhost:9000"
    minio_root_user:str
    minio_root_password:str
    minio_bucket_name:str
    anthropic_api_key:str
    voyage_api_key:str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()