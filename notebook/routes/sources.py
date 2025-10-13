from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from db import get_session
from models import Source, Notebook
from schemas import Source as SourceSchema
from services.extract_service import extract_text_from_file_content, extract_from_url, extract_from_youtube
from services.gcs_service import upload_file_to_gcs
from services.embedding_service import store_embeddings_for_source

router = APIRouter()

def get_user_id(x_user_id: str = Header(...)):  # Fixed this line
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id

@router.post("/")
async def add_source(
    notebook_id: UUID = Form(...),
    type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    website_url: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """Add a new source to a notebook"""
    try:
        print(f"DEBUG: Adding source - type: {type}, notebook_id: {notebook_id}, user_id: {user_id}")
        
        # Verify notebook exists and belongs to user
        notebook_query = select(Notebook).where(
            Notebook.id == notebook_id,
            Notebook.user_id == user_id
        )
        result = await session.execute(notebook_query)
        notebook = result.scalar_one_or_none()
        
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        # Initialize variables
        extracted_text = ""
        metadata = {}
        filename = None
        file_url = None
        
        # Process different source types
        if type == "file":
            if not file:
                raise HTTPException(status_code=400, detail="File is required for file type")
            
            print(f"DEBUG: Processing file upload: {file.filename}")
            
            # Read file content once
            file_content = await file.read()
            print(f"DEBUG: File content size: {len(file_content)} bytes")
            
            if len(file_content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
            # Upload to GCS
            try:
                # Reset file position for GCS upload
                import io
                file.file = io.BytesIO(file_content)
                file_url = upload_file_to_gcs(file)
                print(f"DEBUG: File uploaded to GCS: {file_url}")
            except Exception as e:
                print(f"DEBUG: GCS upload failed: {e}")
                raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
            
            # Extract text using the same content
            try:
                extracted_text, metadata = extract_text_from_file_content(file_content, file.filename)
                print(f"DEBUG: Text extraction result: {len(extracted_text)} characters")
            except Exception as e:
                print(f"DEBUG: Text extraction failed: {e}")
                extracted_text = f"Text extraction failed: {str(e)}"
                metadata = {"error": str(e)}
            
            filename = file.filename
            
        elif type == "website":
            if not website_url:
                raise HTTPException(status_code=400, detail="Website URL is required for website type")
            
            print(f"DEBUG: Processing website URL: {website_url}")
            
            try:
                extracted_text, metadata = await extract_from_url(website_url)
                print(f"DEBUG: Website extraction result: {len(extracted_text)} characters")
            except Exception as e:
                print(f"DEBUG: Website extraction failed: {e}")
                extracted_text = f"Website extraction failed: {str(e)}"
                metadata = {"error": str(e), "url": website_url}
            
        elif type == "youtube":
            if not youtube_url:
                raise HTTPException(status_code=400, detail="YouTube URL is required for youtube type")
            
            print(f"DEBUG: Processing YouTube URL: {youtube_url}")
            
            try:
                extracted_text, metadata = await extract_from_youtube(youtube_url)
                print(f"DEBUG: YouTube extraction result: {len(extracted_text)} characters")
            except Exception as e:
                print(f"DEBUG: YouTube extraction failed: {e}")
                extracted_text = f"YouTube extraction failed: {str(e)}"
                metadata = {"error": str(e), "url": youtube_url}
                
        else:
            raise HTTPException(status_code=400, detail="Invalid source type. Must be 'file', 'website', or 'youtube'")
        
        # Create source record
        source = Source(
            notebook_id=notebook_id,
            type=type,
            filename=filename,
            file_url=file_url,
            website_url=website_url,
            youtube_url=youtube_url,
            extracted_text=extracted_text,
            source_metadata=metadata
        )
        
        session.add(source)
        await session.commit()
        await session.refresh(source)
        
        print(f"DEBUG: Source created with ID: {source.id}")
        
        # Generate embeddings if we have meaningful text
        embedding_success = False
        if extracted_text and len(extracted_text.strip()) > 50:  # Only for substantial text
            try:
                print(f"DEBUG: Starting embedding generation for source {source.id}")
                embeddings = await store_embeddings_for_source(source, session)
                embedding_success = len(embeddings) > 0
                print(f"DEBUG: Generated {len(embeddings)} embeddings")
            except Exception as e:
                print(f"DEBUG: Embedding generation failed: {e}")
                # Don't fail the entire request if embedding generation fails
                pass
        else:
            print(f"DEBUG: Skipping embedding generation - insufficient text content ({len(extracted_text)} characters)")
        
        # Return response
        response_data = {
            "id": str(source.id),  # Convert UUID to string
            "notebook_id": str(source.notebook_id),  # Convert UUID to string
            "type": source.type,
            "filename": source.filename,
            "file_url": source.file_url,
            "website_url": source.website_url,
            "youtube_url": source.youtube_url,
            "extracted_text": source.extracted_text[:500] + "..." if len(source.extracted_text) > 500 else source.extracted_text,
            "metadata": source.source_metadata,
            "embeddings_generated": embedding_success
        }
        
        return JSONResponse(content=response_data, status_code=201)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in add_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{notebook_id}")
async def get_sources(
    notebook_id: UUID,
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """Get all sources for a notebook"""
    try:
        print(f"DEBUG: Getting sources for notebook {notebook_id}, user {user_id}")
        
        # Verify notebook exists and belongs to user
        notebook_query = select(Notebook).where(
            Notebook.id == notebook_id,
            Notebook.user_id == user_id
        )
        result = await session.execute(notebook_query)
        notebook = result.scalar_one_or_none()
        
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        # Get sources for the notebook
        sources_query = select(Source).where(Source.notebook_id == notebook_id).order_by(Source.created_at.desc())
        result = await session.execute(sources_query)
        sources = result.scalars().all()
        
        # Format response
        sources_data = []
        for source in sources:
            source_data = {
                "id": source.id,
                "notebook_id": source.notebook_id,
                "type": source.type,
                "filename": source.filename,
                "file_url": source.file_url,
                "website_url": source.website_url,
                "youtube_url": source.youtube_url,
                "extracted_text": source.extracted_text[:200] + "..." if source.extracted_text and len(source.extracted_text) > 200 else source.extracted_text,
                "metadata": source.source_metadata,
                "created_at": source.created_at
            }
            sources_data.append(source_data)
        
        return {"sources": sources_data, "count": len(sources_data)}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in get_sources: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/detail/{source_id}")
async def get_source_detail(
    source_id: UUID,
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed information about a specific source"""
    try:
        print(f"DEBUG: Getting source detail for {source_id}, user {user_id}")
        
        # Get source with notebook info
        query = select(Source).options(selectinload(Source.notebook)).where(Source.id == source_id)
        result = await session.execute(query)
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Verify user owns the notebook
        if source.notebook.user_id != user_id:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Count embeddings for this source
        from models import Embedding
        embeddings_query = select(Embedding).where(Embedding.source_id == source_id)
        embeddings_result = await session.execute(embeddings_query)
        embeddings_count = len(embeddings_result.scalars().all())
        
        source_data = {
            "id": source.id,
            "notebook_id": source.notebook_id,
            "notebook_title": source.notebook.title,
            "type": source.type,
            "filename": source.filename,
            "file_url": source.file_url,
            "website_url": source.website_url,
            "youtube_url": source.youtube_url,
            "extracted_text": source.extracted_text,
            "metadata": source.source_metadata,
            "created_at": source.created_at,
            "embeddings_count": embeddings_count
        }
        
        return source_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in get_source_detail: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{source_id}")
async def delete_source(
    source_id: UUID,
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """Delete a source and its embeddings"""
    try:
        print(f"DEBUG: Deleting source {source_id}, user {user_id}")
        
        # Get source with notebook info
        query = select(Source).options(selectinload(Source.notebook)).where(Source.id == source_id)
        result = await session.execute(query)
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Verify user owns the notebook
        if source.notebook.user_id != user_id:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Delete the source (embeddings will be deleted automatically due to CASCADE)
        await session.delete(source)
        await session.commit()
        
        print(f"DEBUG: Successfully deleted source {source_id}")
        
        return {"message": "Source deleted successfully", "source_id": source_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in delete_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.patch("/{source_id}")
async def update_source(
    source_id: UUID,
    type: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """Update a source (limited fields)"""
    try:
        print(f"DEBUG: Updating source {source_id}, user {user_id}")
        
        # Get source with notebook info
        query = select(Source).options(selectinload(Source.notebook)).where(Source.id == source_id)
        result = await session.execute(query)
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Verify user owns the notebook
        if source.notebook.user_id != user_id:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update allowed fields
        updated_fields = []
        if website_url is not None and source.type == "website":
            source.website_url = website_url
            updated_fields.append("website_url")
        
        if youtube_url is not None and source.type == "youtube":
            source.youtube_url = youtube_url
            updated_fields.append("youtube_url")
        
        if not updated_fields:
            return {"message": "No fields to update", "source_id": source_id}
        
        await session.commit()
        await session.refresh(source)
        
        print(f"DEBUG: Updated source {source_id}, fields: {updated_fields}")
        
        return {
            "message": "Source updated successfully",
            "source_id": source_id,
            "updated_fields": updated_fields
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in update_source: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
