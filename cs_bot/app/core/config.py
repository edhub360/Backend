from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Chatbot Service"
    DEBUG: bool = False

    GEMINI_API_KEY: str
    DATABASE_URL: str        # comes in as postgresql+asyncpg://...
    REDIS_URL: str

    CHAT_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    VECTOR_COLLECTION: str = "website_docs"
    RETRIEVER_TOP_K: int = 4
    SESSION_TTL_SECONDS: int = 3600

    COLLECTION_TABLE: str = "csbot_collection"
    EMBEDDING_TABLE: str = "csbot_embedding"

    @property
    def PGVECTOR_URL(self) -> str:
        # langchain-postgres needs psycopg3, not asyncpg
        # Convert: postgresql+asyncpg://... → postgresql+psycopg://...
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://"
        )

    class Config:
        env_file = ".env"

settings = Settings()
