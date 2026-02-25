from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingestion_service import ingest_urls
from app.core.config import settings

router = APIRouter()

@router.post("", response_model=IngestResponse)
async def ingest(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    x_admin_key: str = Header(...),  # simple admin protection
):
    # Protect ingestion endpoint with a secret key
    if x_admin_key != settings.OPENAI_API_KEY:  # replace with a dedicated ADMIN_KEY
        raise HTTPException(status_code=403, detail="Forbidden")

    background_tasks.add_task(_run_ingest, req.urls)

    return IngestResponse(
        status="ingestion started in background",
        urls=req.urls,
        chunks_added=0,  # background task, count not available immediately
    )

async def _run_ingest(urls: list[str]):
    count = await ingest_urls(urls)
    print(f"[Ingestion] Added {count} chunks from {urls}")
