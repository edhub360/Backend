from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.importer.sheet_template import create_course_template
from app.importer.sheet_reader import read_course_rows
from app.importer.transformer import transform_row
from app.importer.drive_watcher import register_drive_watch, stop_drive_watch
from app.course_importer import upsert_courses
from typing import Optional

router = APIRouter(prefix="/admin/course-import", tags=["Course Import"])


@router.post("/template")
async def create_template():
    """Creates a Google Sheet with correct headers in the upload folder."""
    try:
        return create_course_template()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/{spreadsheet_id}")
async def process_sheet(spreadsheet_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger import from a specific spreadsheet."""
    raw_rows = read_course_rows(spreadsheet_id)
    transformed = [transform_row(r) for r in raw_rows]
    result = await upsert_courses(db, transformed)
    return {"spreadsheet_id": spreadsheet_id, **result}


@router.post("/watch/register")
async def register_watch():
    """
    Register Drive push notification.
    Call once after deployment — re-call every 6 days to renew.
    """
    try:
        return register_drive_watch()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watch/stop")
async def stop_watch(channel_id: str, resource_id: str):
    """Stop an active Drive watch channel."""
    try:
        stop_drive_watch(channel_id, resource_id)
        return {"stopped": True, "channel_id": channel_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def drive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_changed: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None)
):
    """
    Google Drive calls this POST endpoint when a file is added to the watched folder.
    Drive sends metadata in headers, not body.
    """
    # Drive sends a 'sync' ping when watch is first registered — ignore it
    if x_goog_resource_state == "sync":
        return {"status": "sync acknowledged"}

    # Only process when a file is added or updated
    if x_goog_resource_state not in ("add", "update", "change"):
        return {"status": "ignored", "state": x_goog_resource_state}

    # Find the newly added Google Sheet in the folder
    from app.importer.google_client import get_drive_service
    import os

    folder_id = os.getenv("DRIVE_UPLOAD_FOLDER_ID")
    drive = get_drive_service()

    # Get the most recently added Google Sheet in the folder
    results = drive.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
        orderBy="createdTime desc",
        pageSize=1,
        fields="files(id, name, createdTime)"
    ).execute()

    files = results.get("files", [])
    if not files:
        return {"status": "no sheets found"}

    spreadsheet_id = files[0]["id"]
    spreadsheet_name = files[0]["name"]

    # Run import
    raw_rows = read_course_rows(spreadsheet_id)
    transformed = [transform_row(r) for r in raw_rows]
    result = await upsert_courses(db, transformed)

    return {
        "status": "imported",
        "spreadsheet_id": spreadsheet_id,
        "file_name": spreadsheet_name,
        **result
    }