import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.utils.logging import setup_logging
from app.routes.courses import router as courses_router
from fastapi.middleware.cors import CORSMiddleware

logger = setup_logging()

app = FastAPI(title="Course Service API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router, prefix="/courses", tags=["courses"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
