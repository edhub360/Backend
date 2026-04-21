import os
from app.importer.google_client import get_drive_service
import uuid

DRIVE_UPLOAD_FOLDER_ID = os.getenv("DRIVE_UPLOAD_FOLDER_ID")

# Your Cloud Run importer service public URL
# e.g. https://course-importer-service-xxxx-uc.a.run.app
IMPORTER_SERVICE_URL = os.getenv("IMPORTER_SERVICE_URL")
WEBHOOK_PATH = "/admin/course-import/webhook"


def register_drive_watch() -> dict:
    """
    Registers a push notification with Google Drive.
    Google will POST to IMPORTER_SERVICE_URL/webhook whenever
    a file is created/changed in the watched folder.
    Call this once after deployment, or re-call every 7 days (max expiry).
    """
    drive = get_drive_service()

    channel_id = str(uuid.uuid4())  # unique channel ID for this watch
    webhook_url = f"{IMPORTER_SERVICE_URL}{WEBHOOK_PATH}"

    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
        "expiration": _expiry_ms(days=6)  # max is 7 days for Drive
    }

    response = drive.files().watch(
        fileId=DRIVE_UPLOAD_FOLDER_ID,
        body=body
    ).execute()

    return {
        "channel_id": response.get("id"),
        "resource_id": response.get("resourceId"),
        "expiration": response.get("expiration"),
        "webhook_url": webhook_url
    }


def stop_drive_watch(channel_id: str, resource_id: str) -> bool:
    """
    Stops an existing Drive watch channel.
    Call this before re-registering to avoid duplicate notifications.
    """
    drive = get_drive_service()
    drive.channels().stop(body={
        "id": channel_id,
        "resourceId": resource_id
    }).execute()
    return True


def _expiry_ms(days: int) -> str:
    """Returns expiry timestamp in milliseconds as string (required by Drive API)."""
    import time
    expiry = int((time.time() + days * 86400) * 1000)
    return str(expiry)