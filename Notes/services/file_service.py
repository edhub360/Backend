import os
from google.cloud import storage
from fastapi import UploadFile

GCS_BUCKET = os.getenv("GCS_BUCKET")

async def save_file_to_gcs(file: UploadFile) -> str:
    client = storage.Client()
    bucket = client.get_bucket(GCS_BUCKET)
    blob = bucket.blob(file.filename)
    content = await file.read()
    blob.upload_from_string(content, file.content_type)
    return f"https://storage.googleapis.com/{GCS_BUCKET}/{file.filename}"
