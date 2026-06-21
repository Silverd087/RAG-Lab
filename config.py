from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    qdrant_url:str = "http://localhost:6333"
    redis_url: str = "http://localhost:6379"
    google_api_key:str
    cohere_api_key:str
    postgres_user:str
    postgres_password:str
    postgres_host:str
    postgres_db:str
    postgres_test_db:str
    minio_port:int
    minio_access_keys:str
    minio_secret_keys:str
    minio_bucket_name:str
    class Config:
        env_file = ".env"

settings = Settings()