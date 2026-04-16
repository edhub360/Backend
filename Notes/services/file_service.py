import os
from google.cloud import storage
from fastapi import UploadFile


async def save_file_to_gcs(file: UploadFile) -> str:
    bucket_name = os.getenv("GCS_BUCKET")
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(file.filename)
    content = await file.read()
    blob.upload_from_string(content, file.content_type)
    return f"https://storage.googleapis.com/{bucket_name}/{file.filename}"