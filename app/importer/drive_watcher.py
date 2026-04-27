import json
import os
import time
import uuid
from pathlib import Path

from app.importer.google_client import get_drive_service

DRIVE_UPLOAD_FOLDER_ID = os.getenv("DRIVE_UPLOAD_FOLDER_ID")
IMPORTER_SERVICE_URL = os.getenv("IMPORTER_SERVICE_URL")
WEBHOOK_PATH = "/admin/course-import/webhook"

WATCH_STATE_FILE = "/tmp/drive_watch_state.json"


def register_drive_watch() -> dict:
    """
    Register or renew a Google Drive watch channel.
    If an old channel is recorded, stop it first to prevent duplicates.
    """
    drive = get_drive_service()

    old_state = _load_watch_state()
    if old_state and old_state.get("channel_id") and old_state.get("resource_id"):
        try:
            stop_drive_watch(
                channel_id=old_state["channel_id"],
                resource_id=old_state["resource_id"]
            )
        except Exception:
            pass

    channel_id = str(uuid.uuid4())
    webhook_url = f"{IMPORTER_SERVICE_URL}{WEBHOOK_PATH}"

    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
        "expiration": _expiry_ms(days=6)
    }

    response = drive.files().watch(
        fileId=DRIVE_UPLOAD_FOLDER_ID,
        body=body
    ).execute()

    state = {
        "channel_id": response.get("id"),
        "resource_id": response.get("resourceId"),
        "expiration": response.get("expiration"),
        "webhook_url": webhook_url
    }

    _save_watch_state(state)
    return state


def stop_drive_watch(channel_id: str, resource_id: str) -> bool:
    """
    Stop an active Drive watch channel.
    """
    drive = get_drive_service()
    drive.channels().stop(body={
        "id": channel_id,
        "resourceId": resource_id
    }).execute()

    state = _load_watch_state()
    if state and state.get("channel_id") == channel_id:
        _clear_watch_state()

    return True


def get_active_watch() -> dict | None:
    return _load_watch_state()


def _load_watch_state() -> dict | None:
    path = Path(WATCH_STATE_FILE)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _save_watch_state(data: dict) -> None:
    Path(WATCH_STATE_FILE).write_text(json.dumps(data))


def _clear_watch_state() -> None:
    path = Path(WATCH_STATE_FILE)
    if path.exists():
        path.unlink()


def _expiry_ms(days: int) -> str:
    expiry = int((time.time() + days * 86400) * 1000)
    return str(expiry)