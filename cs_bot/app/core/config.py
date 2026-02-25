from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Chatbot Service"
    DEBUG: bool = False

    GEMINI_API_KEY: str           # ✅ matches --set-env-vars key name
    DATABASE_URL: str             # ✅ matches --set-env-vars key name
    REDIS_URL: str                # ✅ matches --set-env-vars key name

    CHAT_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    VECTOR_COLLECTION: str = "website_docs"
    RETRIEVER_TOP_K: int = 4
    SESSION_TTL_SECONDS: int = 3600

    COLLECTION_TABLE: str = "csbot_collection"
    EMBEDDING_TABLE: str = "csbot_embedding"

    class Config:
        env_file = ".env"          # only used locally, ignored in Cloud Run

settings = Settings()
