from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import MetaData

from app.core.config import get_settings
from app.db.session import engine
from app.db.base import Base
from app.api.v1.study_plan import router as study_plan_router

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables (dev only – in prod use Alembic)
Base.metadata.create_all(bind=engine)

app.include_router(study_plan_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
