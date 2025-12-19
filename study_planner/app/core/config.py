from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "Edhub360 Study Plan Service"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "https://edhub360.github.io", "https://app.edhub360.com"]

    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5432/study_plan_db"

    JWT_SECRET_KEY: str = "change-this-in-prod"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
