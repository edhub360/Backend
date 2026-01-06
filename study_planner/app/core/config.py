from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Edhub360 Study Plan Service"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://edhub360.github.io/StudentHub/",
        "https://app.edhub360.com",
    ]

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ADMIN_USER_ID: str = "96665584-8a26-48fb-9d3d-c6041fc3baa2"  # Admin for predefined plans
    class Config:
        env_file = ".env"  # optional: keep for local dev only

@lru_cache
def get_settings() -> Settings:
    return Settings()
