from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    qdrant_url:str = "http://localhost:6333"
    redis_url: str = "http://localhost:6379"
    google_api_key:str
    cohere_api_key:str
    postgres_user:str
    postgres_password:str

    class Config:
        env_file = ".env"

settings = Settings()