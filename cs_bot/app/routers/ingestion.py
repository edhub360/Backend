from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingestion_service import ingest_urls, ingest_json
from app.core.config import settings

router = APIRouter()

def _check_admin(x_admin_key: str):
    if x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

# POST /ingest/urls — ingest from list of URLs
@router.post("/urls", response_model=IngestResponse)
async def ingest_from_urls(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    x_admin_key: str = Header(...),
):
    _check_admin(x_admin_key)
    background_tasks.add_task(_run_ingest_urls, req.urls)
    return IngestResponse(
        status="ingestion started in background",
        urls=req.urls,
        chunks_added=0,
    )

# POST /ingest/json — ingest from data/website_content.json
@router.post("/json")
async def ingest_from_json(
    x_admin_key: str = Header(...),
):
    _check_admin(x_admin_key)
    count = await ingest_json()
    return {"status": "ok", "chunks_ingested": count}

async def _run_ingest_urls(urls: list[str]):
    count = await ingest_urls(urls)
    print(f"[Ingestion] Added {count} chunks from {urls}")
