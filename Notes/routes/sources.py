import os
import io
import logging
from uuid import UUID
from typing import Optional
from models import Embedding  

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from utils.auth import get_current_user, AuthUser
from db import get_session
from models import Source, Notebook
from schemas import Source as SourceSchema
from services.extract_service import extract_text_from_file_content, extract_from_url, extract_from_youtube
from services.gcs_service import get_gcs_client, upload_file_to_gcs
from services.embedding_service import store_embeddings_for_source

logger = logging.getLogger(__name__)

# Mirrors NotebookCreate.tsx — single source of truth per layer
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB


def validate_uploaded_file(file: UploadFile) -> None:
    """Validate extension, MIME type. Raises HTTPException(422) on violation."""
    ext = os.path.splitext(file.filename or "")[1].lower()

    if not ext:
        raise HTTPException(
            status_code=422,
            detail="File has no extension. Only PDF, DOCX, PPTX, TXT are supported."
        )
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. "
                   f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if file.content_type and file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid MIME type '{file.content_type}' for '{file.filename}'. "
                   f"File may be corrupted or misnamed."
        )


router = APIRouter()

@router.post("/")
async def add_source(
    notebook_id: UUID = Form(...),
    type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    website_url: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add a new source to a notebook."""
    try:
        logger.info(f"Adding source type={type} notebook_id={notebook_id} user_id={user.user_id}")

        # Verify notebook exists and belongs to user
        result = await session.execute(
            select(Notebook).where(
                Notebook.id == notebook_id,
                Notebook.user_id == user.user_id
            )
        )
        notebook = result.scalar_one_or_none()
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        extracted_text = ""
        source_metadata = {}
        filename = None
        file_url = None

        if type == "file":
            if not file:
                raise HTTPException(status_code=400, detail="File is required for file type")

            # Validate before reading content — fail fast
            validate_uploaded_file(file)

            logger.info(f"Processing file upload: {file.filename}")
            file_content = await file.read()
            logger.info(f"File size: {len(file_content)} bytes")

            if len(file_content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")

            # Size check after read — content_length header can be spoofed
            if len(file_content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=422,
                    detail=f"File exceeds 20MB limit "
                           f"({len(file_content) / 1024 / 1024:.1f}MB uploaded)."
                )

            # Upload to GCS
            try:
                file.file = io.BytesIO(file_content)
                client = get_gcs_client()
                file_url = upload_file_to_gcs(file, file_content, client=client)
                logger.info(f"File uploaded to GCS: {file_url}")
            except Exception as e:
                logger.error(f"GCS upload failed: {e}")
                raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

            # Extract text
            try:
                extracted_text, source_metadata = extract_text_from_file_content(
                    file_content, file.filename
                )
                logger.info(f"Text extracted: {len(extracted_text)} characters")
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
                extracted_text = f"Text extraction failed: {str(e)}"
                source_metadata = {"error": str(e)}

            filename = file.filename

        elif type == "website":
            if not website_url:
                raise HTTPException(status_code=400, detail="Website URL is required")
            logger.info(f"Processing website URL: {website_url}")
            try:
                extracted_text, source_metadata = await extract_from_url(website_url)
                logger.info(f"Website extracted: {len(extracted_text)} characters")
            except Exception as e:
                logger.error(f"Website extraction failed: {e}")
                extracted_text = f"Website extraction failed: {str(e)}"
                source_metadata = {"error": str(e), "url": website_url}

        elif type == "youtube":
            if not youtube_url:
                raise HTTPException(status_code=400, detail="YouTube URL is required")
            logger.info(f"Processing YouTube URL: {youtube_url}")
            try:
                extracted_text, source_metadata = await extract_from_youtube(youtube_url)
                logger.info(f"YouTube extracted: {len(extracted_text)} characters")
            except Exception as e:
                logger.error(f"YouTube extraction failed: {e}")
                extracted_text = f"YouTube extraction failed: {str(e)}"
                source_metadata = {"error": str(e), "url": youtube_url}

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type. Must be 'file', 'website', or 'youtube'"
            )

        # Create source record
        source = Source(
            notebook_id=notebook_id,
            type=type,
            filename=filename,
            file_url=file_url,
            website_url=website_url,
            youtube_url=youtube_url,
            extracted_text=extracted_text,
            source_metadata=source_metadata  # was shadowed by metadata param before
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        logger.info(f"Source created: {source.id}")

        # Generate embeddings for substantial text
        embedding_success = False
        if extracted_text and len(extracted_text.strip()) > 50:
            try:
                embeddings = await store_embeddings_for_source(source, session)
                embedding_success = len(embeddings) > 0
                logger.info(f"Generated {len(embeddings)} embeddings for source {source.id}")
            except Exception as e:
                logger.error(f"Embedding generation failed for source {source.id}: {e}")
                # Non-fatal — source is saved, embeddings can be regenerated
        else:
            logger.warning(
                f"Skipping embeddings — insufficient text "
                f"({len(extracted_text)} chars) for source {source.id}"
            )

        preview_text = (
            source.extracted_text[:500] + "..."
            if len(source.extracted_text) > 500
            else source.extracted_text
        )

        return JSONResponse(
            status_code=201,
            content={
                "id": str(source.id),
                "notebook_id": str(source.notebook_id),
                "type": source.type,
                "filename": source.filename,
                "file_url": source.file_url,
                "website_url": source.website_url,
                "youtube_url": source.youtube_url,
                "extracted_text": preview_text,
                "metadata": source.source_metadata,
                "embeddings_generated": embedding_success,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{notebook_id}")
async def get_sources(
    notebook_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all sources for a notebook."""
    try:
        logger.info(f"Getting sources for notebook {notebook_id}, user {user.user_id}")

        # Verify notebook exists and belongs to user
        result = await session.execute(
            select(Notebook).where(
                Notebook.id == notebook_id,
                Notebook.user_id == user.user_id
            )
        )
        notebook = result.scalar_one_or_none()
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Get sources ordered by newest first
        result = await session.execute(
            select(Source)
            .where(Source.notebook_id == notebook_id)
            .order_by(Source.created_at.desc())
        )
        sources = result.scalars().all()

        sources_data = [
            {
                "id": str(source.id),              # UUID → str for JSON serialization
                "notebook_id": str(source.notebook_id),
                "type": source.type,
                "filename": source.filename,
                "file_url": source.file_url,
                "website_url": source.website_url,
                "youtube_url": source.youtube_url,
                "extracted_text": (
                    source.extracted_text[:200] + "..."
                    if source.extracted_text and len(source.extracted_text) > 200
                    else source.extracted_text
                ),
                "metadata": source.source_metadata,
                "created_at": source.created_at.isoformat() if source.created_at else None,  # ✅ datetime → str
            }
            for source in sources
        ]

        logger.info(f"Retrieved {len(sources_data)} sources for notebook {notebook_id}")
        return {"sources": sources_data, "count": len(sources_data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_sources: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/detail/{source_id}")
async def get_source_detail(
    source_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed information about a specific source."""
    try:
        logger.info(f"Getting source detail for {source_id}, user {user.user_id}")

        # Get source with notebook eagerly loaded for ownership check
        result = await session.execute(
            select(Source)
            .options(selectinload(Source.notebook))
            .where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()

        # Return 404 for both missing and unauthorized — avoids source enumeration
        if not source or str(source.notebook.user_id) != str(user.user_id):
            raise HTTPException(status_code=404, detail="Source not found")

        # Use COUNT() — avoids loading all embedding rows into memory
        embeddings_count_result = await session.execute(
            select(func.count()).where(Embedding.source_id == source_id)
        )
        embeddings_count = embeddings_count_result.scalar() or 0

        return {
            "id": str(source.id),                    # ✅ UUID → str
            "notebook_id": str(source.notebook_id),
            "notebook_title": source.notebook.title,
            "type": source.type,
            "filename": source.filename,
            "file_url": source.file_url,
            "website_url": source.website_url,
            "youtube_url": source.youtube_url,
            "extracted_text": source.extracted_text,  # full text for detail view
            "metadata": source.source_metadata,
            "created_at": source.created_at.isoformat() if source.created_at else None,  # ✅ datetime → str
            "embeddings_count": embeddings_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_source_detail: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{source_id}")
async def delete_source(
    source_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a source and its embeddings."""
    try:
        logger.info(f"Deleting source {source_id}, user {user.user_id}")

        result = await session.execute(
            select(Source)
            .options(selectinload(Source.notebook))
            .where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()

        # 404 for both missing and unauthorized — avoids source enumeration
        if not source or str(source.notebook.user_id) != str(user.user_id):
            raise HTTPException(status_code=404, detail="Source not found")

        await session.delete(source)
        await session.commit()

        logger.info(f"Successfully deleted source {source_id}")

        # str(source_id) — UUID not JSON serializable in plain dict return
        return {"message": "Source deleted successfully", "source_id": str(source_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch("/{source_id}")
async def update_source(
    source_id: UUID,
    type: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a source URL (website or youtube only)."""
    try:
        logger.info(f"Updating source {source_id}, user {user.user_id}")

        result = await session.execute(
            select(Source)
            .options(selectinload(Source.notebook))
            .where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()

        if not source or str(source.notebook.user_id) != str(user.user_id):
            raise HTTPException(status_code=404, detail="Source not found")

        # Block updates on file sources — files can't be updated via PATCH
        if source.type == "file":
            raise HTTPException(
                status_code=400,
                detail="File sources cannot be updated. Delete and re-upload instead."
            )

        updated_fields = []

        if website_url is not None and source.type == "website":
            source.website_url = website_url
            updated_fields.append("website_url")

        if youtube_url is not None and source.type == "youtube":
            source.youtube_url = youtube_url
            updated_fields.append("youtube_url")

        if not updated_fields:
            # 400 not 200 — nothing was updated, caller likely sent wrong field
            raise HTTPException(
                status_code=400,
                detail=f"No updatable fields for source type '{source.type}'. "
                       f"Provide 'website_url' for website sources or 'youtube_url' for YouTube sources."
            )

        await session.commit()
        await session.refresh(source)

        logger.info(f"Updated source {source_id}, fields: {updated_fields}")

        return {
            "message": "Source updated successfully",
            "source_id": str(source_id),       # UUID → str
            "updated_fields": updated_fields,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
