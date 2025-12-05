import os
import google.generativeai as genai
from sqlalchemy import select, func, literal_column,delete
from sqlalchemy.sql import text
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from models import Embedding, Source, Notebook
from db import AsyncSessionLocal
from schemas import SemanticSearchRequest
import numpy as np
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def chunk_text(text, max_tokens=500):
    """
    Split text into chunks of specified token size.
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
    Returns:
        List of text chunks
    """
    if not text or len(text.strip()) == 0:
        logger.warning("Empty or None text provided for chunking")
        return []
    
    words = text.split()
    chunks = [" ".join(words[i:i+max_tokens]) for i in range(0, len(words), max_tokens)]
    chunks = [chunk for chunk in chunks if len(chunk.strip()) > 0]
    logger.info(f"Created {len(chunks)} chunks from {len(words)} words")
    return chunks

async def embed_text(text: str) -> List[float]:
    """Generate embeddings using Gemini API."""
    try:
        logger.info(f"Generating embedding for text: {text[:100]}...")
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="semantic_similarity"
        )
        embedding_vector = result['embedding']
        logger.info(f"Successfully generated embedding with dimension: {len(embedding_vector)}")
        return embedding_vector
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")

async def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts in batch."""
    try:
        logger.info(f"Generating embeddings for {len(texts)} texts")
        vectors = []
        for i, text in enumerate(texts):
            if not text or len(text.strip()) == 0:
                logger.warning(f"Skipping empty text at index {i}")
                continue
            
            vector = await embed_text(text)
            vectors.append(vector)
            
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(0.1)
        
        logger.info(f"Generated {len(vectors)} embeddings successfully")
        return vectors
    except Exception as e:
        logger.error(f"Error in batch embedding generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch embedding failed: {str(e)}")

async def store_embeddings_for_source(source: Source, session: AsyncSession) -> List[Embedding]:
    """Process and store embeddings for a source."""
    logger.info(f"Starting embedding generation for source {source.id}")
    
    if not source.extracted_text or len(source.extracted_text.strip()) < 10:
        logger.warning(f"Insufficient text content: {len(source.extracted_text) if source.extracted_text else 0} characters")
        return []
    
    try:
        chunks = chunk_text(source.extracted_text)
        if not chunks:
            logger.warning("No valid chunks created from source text")
            return []
        
        logger.info(f"Processing {len(chunks)} chunks for source {source.id}")
        vectors = await embed_texts_batch(chunks)
        
        if len(vectors) != len(chunks):
            logger.error(f"Mismatch: {len(chunks)} chunks but {len(vectors)} vectors")
            return []
        
        embeddings = []
        for chunk, vector in zip(chunks, vectors):
            embedding = Embedding(
                source_id=source.id,
                chunk=chunk,
                vector=vector
            )
            session.add(embedding)
            embeddings.append(embedding)
        
        await session.commit()
        logger.info(f"Successfully stored {len(embeddings)} embeddings for source {source.id}")
        return embeddings
        
    except Exception as e:
        logger.error(f"Failed to store embeddings for source {source.id}: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {str(e)}")

async def semantic_search(data: SemanticSearchRequest, session: AsyncSession) -> Dict[str, Any]:
    """Perform semantic search across embeddings using schema-based request."""
    try:
        logger.info(f"Semantic search for: '{data.query}' (top {data.top_n})")
        
        query_vector = await embed_text(data.query)
        logger.info(f"Generated query embedding with dimension: {len(query_vector)}")
        
        # CORRECT format for pgvector - keep square brackets!
        vector_str = str(query_vector)  # This gives us "[1,2,3,...]" which is correct!
        
        # Create vector literal for comparison
        vector_literal = literal_column(f"'{vector_str}'::vector")
        
        # Base query using SQLAlchemy Core
        base_query = select(
            Embedding.id,
            Embedding.chunk,
            Embedding.source_id,
            (1 - func.cosine_distance(Embedding.vector, vector_literal)).label('similarity_score')
        )
        
        if data.source_ids:
            # Add source_id filter
            source_id_list = [str(sid) for sid in data.source_ids]
            query = base_query.where(
                Embedding.source_id.in_(source_id_list)
            )
        else:
            query = base_query
        
        # Add ordering and limit
        query = query.order_by(
            func.cosine_distance(Embedding.vector, vector_literal)
        ).limit(data.top_n)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        chunks = []
        for row in rows:
            chunks.append({
                "id": str(row.id),
                "chunk": row.chunk,
                "source_id": str(row.source_id),
                "score": round(row.similarity_score, 4)
            })
        
        logger.info(f"Found {len(chunks)} similar chunks")
        return {"chunks": chunks}
        
    except Exception as e:
        logger.error(f"Semantic search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


from sqlalchemy import select, func, and_, literal_column

async def get_relevant_chunks_for_notebook(
    session: AsyncSession,
    notebook_id: str,
    user_query: str,
    top_n: int = 5,
    user_id: str = None
) -> List[Dict[str, Any]]:
    """Get relevant chunks for a specific notebook using semantic search."""
    try:
        logger.info(f"Searching notebook {notebook_id} for: '{user_query}'")
        
        query_vector = await embed_text(user_query)

        # NEW: bind the embedding as a SQL parameter instead of "'[...]'::vector"
        # we will use this placeholder in func.cosine_distance below
        embedding_param = literal_column(":query_embedding")

        if user_id:
            # Query with user_id filter - join all three tables
            query = (
                select(
                    Embedding.id,
                    Embedding.chunk,
                    Embedding.source_id,
                    Source.filename.label("source_name"),
                    Source.type.label("source_type"),
                    (1 - func.cosine_distance(Embedding.vector, embedding_param)).label(
                        "similarity_score"
                    ),
                )
                .select_from(
                    Embedding.__table__
                    .join(Source.__table__)
                    .join(Notebook.__table__)
                )
                .where(
                    and_(
                        Source.notebook_id == notebook_id,
                        Notebook.user_id == user_id,
                    )
                )
            )
        else:
            # Query without user_id filter - join only Embedding and Source
            query = (
                select(
                    Embedding.id,
                    Embedding.chunk,
                    Embedding.source_id,
                    Source.filename.label("source_name"),
                    Source.type.label("source_type"),
                    (1 - func.cosine_distance(Embedding.vector, embedding_param)).label(
                        "similarity_score"
                    ),
                )
                .select_from(Embedding.__table__.join(Source.__table__))
                .where(Source.notebook_id == notebook_id)
            )

        # CHANGED: order_by uses the same embedding_param
        query = query.order_by(
            func.cosine_distance(Embedding.vector, embedding_param)
        ).limit(top_n)

        # NEW: pass the actual vector as a bound parameter
        result = await session.execute(
            query.params(query_embedding=query_vector)
        )
        rows = result.fetchall()

        chunks = []
        for row in rows:
            chunks.append(
                {
                    "id": str(row.id),
                    "chunk": row.chunk,
                    "source_id": str(row.source_id),
                    "source_name": row.source_name or "Unknown",
                    "source_type": row.source_type or "file",
                    "score": round(row.similarity_score, 4),
                }
            )

        logger.info(f"Retrieved {len(chunks)} relevant chunks for notebook {notebook_id}")
        return chunks

    except Exception as e:
        logger.error(f"Error retrieving chunks for notebook {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve relevant chunks: {str(e)}",
        )


async def get_embedding_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get statistics about stored embeddings."""
    try:
        stats_query = text("""
            SELECT 
                COUNT(*) as total_embeddings,
                COUNT(DISTINCT source_id) as unique_sources,
                AVG(LENGTH(chunk)) as avg_chunk_length,
                MAX(LENGTH(chunk)) as max_chunk_length,
                MIN(LENGTH(chunk)) as min_chunk_length
            FROM stud_hub_schema.embeddings
        """)
        result = await session.execute(stats_query)
        row = result.fetchone()
        
        stats = {
            "total_embeddings": row.total_embeddings or 0,
            "unique_sources": row.unique_sources or 0,
            "avg_chunk_length": round(row.avg_chunk_length or 0, 2),
            "max_chunk_length": row.max_chunk_length or 0,
            "min_chunk_length": row.min_chunk_length or 0
        }
        
        logger.info(f"Retrieved embedding stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting embedding stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get embedding stats: {str(e)}")

# Legacy function for backward compatibility
async def semantic_search_legacy(
    query: str, 
    top_n: int = 5, 
    source_ids: Optional[List[UUID]] = None, 
    session: AsyncSession = None
) -> List[Dict[str, Any]]:
    """
    Legacy semantic search function for backward compatibility.
    
    Args:
        query: Search query
        top_n: Number of results to return
        source_ids: Optional list of source IDs to filter by
        session: Database session
    
    Returns:
        List of search results
    """
    try:
        logger.info(f"Legacy semantic search for: '{query}' (top {top_n})")
        
        # Create a SemanticSearchRequest object
        search_request = SemanticSearchRequest(
            query=query,
            top_n=top_n,
            source_ids=source_ids
        )
        
        # Use the main search function
        result = await semantic_search(search_request, session)
        return result["chunks"]
        
    except Exception as e:
        logger.error(f"Legacy semantic search error: {str(e)}")
        raise

async def semantic_search_simple(query: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Simple semantic search without source filtering using a new session.
    
    Args:
        query: Search query
        top_n: Number of results to return
    
    Returns:
        List of search results
    """
    async with AsyncSessionLocal() as session:
        return await semantic_search_legacy(query, top_n, None, session)

# Health check function for embedding service
async def health_check() -> Dict[str, Any]:
    """
    Check if the embedding service is healthy.
    
    Returns:
        Dictionary with health status
    """
    try:
        # Test Gemini API connectivity
        test_embedding = await embed_text("health check test")
        
        # Test database connectivity
        async with AsyncSessionLocal() as session:
            stats = await get_embedding_stats(session)
        
        return {
            "status": "healthy",
            "gemini_api": "connected",
            "embedding_dimension": len(test_embedding),
            "database_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
