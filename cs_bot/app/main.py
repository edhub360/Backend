from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_vector_store
from app.core.redis import init_redis, get_redis
from app.routers import chat, ingestion

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_vector_store()
    init_redis()
    yield
    # Shutdown
    await get_redis().aclose()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to your frontend domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ingestion.router, prefix="/ingest", tags=["Ingestion"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
