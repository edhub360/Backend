import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from courses.app.utils.logging import setup_logging
from courses.app.routes.courses import router as courses_router
from fastapi.middleware.cors import CORSMiddleware

logger = setup_logging()

app = FastAPI(title="Course Service API")

# ← FIXED ORDER: logging middleware first so it wraps everything including CORS
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request {request.method} {request.url}")
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled error: {exc}")
        raise
    logger.info(f"Response status: {response.status_code}")
    return response

# ← CORSMiddleware added AFTER @app.middleware so it runs closer to the route
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router, prefix="/courses", tags=["courses"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )