# syntax=docker/dockerfile:1.6

# 1) Base image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    APP_DIR=/app

WORKDIR ${APP_DIR}

# 2) System deps (build + runtime)
# - libpq is not required by asyncpg, but we keep minimal tools
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#      build-essential curl ca-certificates && \
#    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates libpq-dev && \
    rm -rf /var/lib/apt/lists/*


# 3) Install Python deps first (better layer caching)
# Copy only requirements to leverage Docker layer cache
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4) Copy application code
# Assuming your app files: main.py, database.py, models.py, schemas.py
# and package directory structure if any (e.g., studenthub/)
COPY . .

# 5) Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser ${APP_DIR}
USER appuser

# 6) Expose and run
EXPOSE 8080
# If your app file is `main.py` and FastAPI instance is `app`
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
