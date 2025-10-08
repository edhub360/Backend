import os
from google.cloud import storage
from google.auth import default
import io
from typing import Optional
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime

# Initialize GCS client
try:
    credentials, project_id = default()
    client = storage.Client(credentials=credentials, project=project_id)
except Exception as e:
    print(f"WARNING: Could not initialize GCS client: {e}")
    client = None

BUCKET_NAME = os.getenv("GCS_BUCKET", "arctic-sentry-467317-s7-studenthub-data")

def upload_file_to_gcs(file: UploadFile, file_content: Optional[bytes] = None) -> str:
    """Upload file to Google Cloud Storage and return the public URL"""
    try:
        if not client:
            raise Exception("GCS client not initialized")
        
        bucket = client.bucket(BUCKET_NAME)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = file.filename.replace(" ", "_").replace("/", "_")
        blob_name = f"uploads/{timestamp}_{unique_id}_{safe_filename}"
        
        blob = bucket.blob(blob_name)
        
        # Upload the file content
        if file_content:
            # Use provided file content
            blob.upload_from_string(file_content, content_type=file.content_type)
        else:
            # Read from file stream
            file_data = file.file.read()
            blob.upload_from_string(file_data, content_type=file.content_type)
        
        # DON'T make blob public - this causes the ACL error
        # blob.make_public()  # Comment out or remove this line
        
        # Return the GCS URL (authenticated access required)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        print(f"DEBUG: File uploaded to GCS: {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"DEBUG: GCS upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

def delete_file_from_gcs(file_url: str) -> bool:
    """Delete file from Google Cloud Storage"""
    try:
        if not client:
            print("WARNING: GCS client not initialized")
            return False
        
        # Extract blob name from URL
        if BUCKET_NAME in file_url:
            blob_name = file_url.split(f"{BUCKET_NAME}/")[-1]
        else:
            print("WARNING: Invalid GCS URL format")
            return False
        
        bucket = client.bucket(BUCKET_NAME)
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

def get_signed_url(file_url: str, expiration_minutes: int = 60) -> Optional[str]:
    """Generate a signed URL for private file access"""
    try:
        if not client:
            print("WARNING: GCS client not initialized")
            return None
        
        # Extract blob name from URL
        if BUCKET_NAME in file_url:
            blob_name = file_url.split(f"{BUCKET_NAME}/")[-1]
        else:
            return None
        
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)
        
        from datetime import timedelta
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        
        return url
        
    except Exception as e:
        print(f"DEBUG: Signed URL generation failed: {e}")
        return None
