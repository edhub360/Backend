from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.api.v1.study_plan import router as study_plan_router

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

settings = get_settings()
logging.info(
    "STUDY-PLAN SETTINGS: JWT_ALGORITHM=%s, JWT_SECRET_KEY_PREFIX=%s",
    settings.JWT_ALGORITHM,
    settings.JWT_SECRET_KEY[:6],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Do NOT call Base.metadata.create_all(bind=engine) with async engine.
# Use migrations (Alembic) or a separate sync script instead.

app.include_router(study_plan_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
