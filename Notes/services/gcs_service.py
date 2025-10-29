import os
from google.cloud import storage
from google.auth import default as gauth_default
from fastapi import UploadFile, HTTPException
from typing import Optional
import uuid
from datetime import datetime, timedelta

print("DEBUG: Rebuilding gcs_service.py! Should see this on every deployment.")

# Module-level private client variable
_client = None
_credentials = None
_project_id = None

BUCKET_NAME = os.getenv("GCS_BUCKET", "arctic-sentry-467317-s7-studenthub-data")


def get_gcs_client() -> storage.Client:
    """Lazy initializer & singleton getter for GCS client"""
    global _client, _credentials, _project_id

    if _client is not None:
        return _client

    try:
        _credentials, _project_id = gauth_default()
        print("DEBUG: GCS project id:", _project_id)
        print("DEBUG: GCS_BUCKET env:", BUCKET_NAME)
        print("DEBUG: GCS credentials class:", type(_credentials))
        print("DEBUG: Service account email (if available):", getattr(_credentials, 'service_account_email', 'N/A'))

        _client = storage.Client(credentials=_credentials, project=_project_id)
        print("DEBUG: GCS client created successfully")

        # Optional check: list buckets to confirm access
        try:
            buckets = list(_client.list_buckets())
            print("DEBUG: Accessible GCS buckets:", [b.name for b in buckets])
        except Exception as e:
            print("WARNING: Cannot list buckets:", e)

        return _client

    except Exception as e:
        print(f"WARNING: Could not initialize GCS client: {e}")
        _client = None
        raise e


def upload_file_to_gcs(file: UploadFile, file_content: Optional[bytes] = None, client: Optional[storage.Client] = None) -> str:
    """Upload file to Google Cloud Storage using provided or singleton client"""
    try:
        actual_client = client or get_gcs_client()
        if actual_client is None:
            raise Exception("GCS client not initialized")

        bucket = actual_client.bucket(BUCKET_NAME)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = file.filename.replace(" ", "_").replace("/", "_")
        blob_name = f"uploads/{timestamp}_{unique_id}_{safe_filename}"

        blob = bucket.blob(blob_name)

        if file_content:
            blob.upload_from_string(file_content, content_type=file.content_type)
        else:
            file_data = file.file.read()
            blob.upload_from_string(file_data, content_type=file.content_type)

        # Do NOT make blob public for security reasons
        # blob.make_public()

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        print(f"DEBUG: File uploaded to GCS: {public_url}")

        return public_url

    except Exception as e:
        print(f"DEBUG: GCS upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


def delete_file_from_gcs(file_url: str, client: Optional[storage.Client] = None) -> bool:
    """Delete file from Google Cloud Storage"""
    try:
        actual_client = client or get_gcs_client()
        if actual_client is None:
            print("WARNING: GCS client not initialized")
            return False

        if BUCKET_NAME in file_url:
            blob_name = file_url.split(f"{BUCKET_NAME}/")[-1]
        else:
            print("WARNING: Invalid GCS URL format")
            return False

        bucket = actual_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)

        if blob.exists():
            blob.delete()
            print(f"DEBUG: File deleted from GCS: {file_url}")
            return True
        else:
            print(f"DEBUG: File not found in GCS: {file_url}")
            return False

    except Exception as e:
        print(f"DEBUG: GCS deletion failed: {e}")
        return False


def get_signed_url(file_url: str, expiration_minutes: int = 60, client: Optional[storage.Client] = None) -> Optional[str]:
    """Generate a signed URL for private file access"""
    try:
        actual_client = client or get_gcs_client()
        if actual_client is None:
            print("WARNING: GCS client not initialized")
            return None

        if BUCKET_NAME in file_url:
            blob_name = file_url.split(f"{BUCKET_NAME}/")[-1]
        else:
            return None

        bucket = actual_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )

        return url

    except Exception as e:
        print(f"DEBUG: Signed URL generation failed: {e}")
        return None
