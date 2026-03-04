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

def chunk_text(text: str, max_words: int = 500) -> List[str]:
    """
    Split text into chunks by word count.
    Note: 'words' here is a proxy for tokens (1 token ≈ 0.75 words).
    500 words ≈ ~650 tokens, safe for embedding model limits.
    """
    if not text or len(text.strip()) == 0:
        logger.warning("Empty or None text provided for chunking")
        return []

    words = text.split()
    chunks = [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
    ]
    chunks = [chunk for chunk in chunks if chunk.strip()]
    logger.info(f"Created {len(chunks)} chunks from {len(words)} words")
    return chunks


async def embed_text(text: str) -> List[float]:
    """Generate embeddings using Gemini API."""
    try:
        logger.info(f"Generating embedding for text: {text[:100]}...")

        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="semantic_similarity",
            output_dimensionality=768,
        )

        embedding_vector = None

        if isinstance(result, dict):
            if "embedding" in result:
                emb = result["embedding"]
                embedding_vector = emb.get("values", emb) if isinstance(emb, dict) else emb
            elif "embeddings" in result and result["embeddings"]:
                emb = result["embeddings"][0]
                embedding_vector = emb.get("values", emb)
        else:
            if hasattr(result, "embedding"):
                emb = result.embedding
                embedding_vector = getattr(emb, "values", emb)
            elif hasattr(result, "embeddings") and result.embeddings:
                emb = result.embeddings[0]
                embedding_vector = getattr(emb, "values", emb)

        if not embedding_vector:
            raise ValueError("Gemini embedding response missing embedding values")

        logger.info(f"Successfully generated embedding with dimension: {len(embedding_vector)}")
        return embedding_vector

    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise ValueError(f"Failed to generate embedding: {str(e)}")  # ✅ plain exception


async def embed_texts_batch(texts: List[str], max_retries: int = 3) -> List[List[float]]:
    """Generate embeddings for multiple texts in batch with retry on rate limit."""
    try:
        logger.info(f"Generating embeddings for {len(texts)} texts")
        vectors = []

        for i, t in enumerate(texts):
            if not t or not t.strip():
                logger.warning(f"Skipping empty text at index {i}")
                continue

            for attempt in range(max_retries):
                try:
                    vector = await embed_text(t)
                    vectors.append(vector)
                    break
                except ValueError as e:
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                        logger.warning(f"Embedding attempt {attempt+1} failed, retrying in {wait}s: {e}")
                        await asyncio.sleep(wait)
                    else:
                        raise

            # Gentle rate limit pacing — only needed in bulk operations
            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.5)  # 0.1s was too tight, 0.5s is safer

        logger.info(f"Generated {len(vectors)} embeddings successfully")
        return vectors

    except Exception as e:
        logger.error(f"Error in batch embedding generation: {str(e)}")
        raise ValueError(f"Batch embedding failed: {str(e)}")  # ✅ plain exception


async def store_embeddings_for_source(
    source: Source,
    session: AsyncSession
) -> List[Embedding]:
    """Process and store embeddings for a source."""
    logger.info(f"Starting embedding generation for source {source.id}")

    if not source.extracted_text or len(source.extracted_text.strip()) < 10:
        logger.warning(
            f"Insufficient text content for source {source.id}: "
            f"{len(source.extracted_text) if source.extracted_text else 0} chars"
        )
        return []

    try:
        chunks = chunk_text(source.extracted_text)  # uses max_words=500 default
        if not chunks:
            logger.warning(f"No valid chunks created from source {source.id}")
            return []

        logger.info(f"Processing {len(chunks)} chunks for source {source.id}")
        vectors = await embed_texts_batch(chunks)

        if len(vectors) != len(chunks):
            logger.error(
                f"Chunk/vector mismatch for source {source.id}: "
                f"{len(chunks)} chunks vs {len(vectors)} vectors — aborting store"
            )
            return []

        # Delete existing embeddings for this source before re-storing
        # Prevents duplicate embeddings if source is re-processed
        await session.execute(
            delete(Embedding).where(Embedding.source_id == source.id)
        )

        embeddings = [
            Embedding(source_id=source.id, chunk=chunk, vector=vector)
            for chunk, vector in zip(chunks, vectors)
        ]
        session.add_all(embeddings)  # ✅ batch add instead of per-item add()

        await session.commit()
        logger.info(
            f"Successfully stored {len(embeddings)} embeddings for source {source.id}"
        )
        return embeddings

    except Exception as e:
        logger.error(f"Failed to store embeddings for source {source.id}: {str(e)}")
        await session.rollback()
        raise ValueError(f"Failed to store embeddings: {str(e)}")  # ✅ plain exception

async def semantic_search(
    data: SemanticSearchRequest,
    session: AsyncSession
) -> Dict[str, Any]:
    """Perform semantic search across embeddings using pgvector cosine similarity."""
    try:
        logger.info(f"Semantic search for: '{data.query}' (top_n={data.top_n})")

        query_vector = await embed_text(data.query)
        logger.info(f"Generated query embedding with dimension: {len(query_vector)}")

        # Use SQLAlchemy text() cast — safer than string interpolation into literal_column
        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        vector_literal = func.cast(vector_str, type_=text("vector"))

        similarity_score = (
            1 - func.cosine_distance(Embedding.vector, vector_literal)
        ).label("similarity_score")

        base_query = select(
            Embedding.id,
            Embedding.chunk,
            Embedding.source_id,
            similarity_score
        )

        if data.source_ids:
            # Cast to str only if source_id column is UUID stored as string
            source_id_list = [str(sid) for sid in data.source_ids]
            base_query = base_query.where(Embedding.source_id.in_(source_id_list))

        base_query = (
            base_query
            .order_by(func.cosine_distance(Embedding.vector, vector_literal))
            .limit(data.top_n)
        )

        result = await session.execute(base_query)
        rows = result.fetchall()

        chunks = [
            {
                "id": str(row.id),
                "chunk": row.chunk,
                "source_id": str(row.source_id),
                "score": round(float(row.similarity_score), 4),
                # Guard: clamp to [0.0, 1.0] since floating point can produce 1.0000001
                "score": max(0.0, min(1.0, round(float(row.similarity_score), 4)))
            }
            for row in rows
        ]

        # Optionally filter out low-relevance results
        MIN_SCORE = 0.5
        filtered = [c for c in chunks if c["score"] >= MIN_SCORE]

        logger.info(
            f"Found {len(rows)} chunks, {len(filtered)} above "
            f"MIN_SCORE={MIN_SCORE} threshold"
        )

        return {"chunks": filtered, "total_found": len(rows)}

    except Exception as e:
        logger.error(f"Semantic search error: {str(e)}")
        raise ValueError(f"Search failed: {str(e)}")  # plain exception


from sqlalchemy import select, and_, func, literal_column
from fastapi import HTTPException

async def get_relevant_chunks_for_notebook(
    session: AsyncSession,
    notebook_id: str,
    user_query: str,
    top_n: int = 5,
    user_id: Optional[str] = None,
    min_score: float = 0.5,  # ✅ consistent with semantic_search threshold
) -> List[Dict[str, Any]]:
    """Get relevant chunks for a specific notebook using semantic search."""
    try:
        logger.info(f"Searching notebook {notebook_id} for: '{user_query}'")

        query_vector = await embed_text(user_query)
        logger.info(f"Generated query embedding dimension: {len(query_vector)}")

        # Compact format — no spaces — safe for all pgvector versions
        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        vector_literal = literal_column(f"'{vector_str}'::vector")

        similarity_expr = (
            1 - func.cosine_distance(Embedding.vector, vector_literal)
        ).label("similarity_score")

        # Shared selected columns to avoid duplication between branches
        selected_columns = [
            Embedding.id,
            Embedding.chunk,
            Embedding.source_id,
            Source.filename.label("source_name"),
            Source.type.label("source_type"),
            similarity_expr,
        ]

        if user_id:
            query = (
                select(*selected_columns)
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
            query = (
                select(*selected_columns)
                .select_from(Embedding.__table__.join(Source.__table__))
                .where(Source.notebook_id == notebook_id)
            )

        query = (
            query
            .order_by(func.cosine_distance(Embedding.vector, vector_literal))
            .limit(top_n)
        )

        result = await session.execute(query)
        rows = result.fetchall()

        chunks: List[Dict[str, Any]] = [
            {
                "id": str(row.id),
                "chunk": row.chunk,
                "source_id": str(row.source_id),
                "source_name": row.source_name or "Unknown",
                "source_type": row.source_type or "file",
                # Clamp to [0.0, 1.0] — floating point cosine can exceed bounds
                "score": max(0.0, min(1.0, round(float(row.similarity_score), 4))),
            }
            for row in rows
        ]

        # Filter low-relevance chunks — prevents noise being passed to Gemini
        filtered = [c for c in chunks if c["score"] >= min_score]

        logger.info(
            f"Notebook {notebook_id}: {len(rows)} chunks retrieved, "
            f"{len(filtered)} above min_score={min_score}"
        )

        return filtered

    except Exception as e:
        logger.error(f"Error retrieving chunks for notebook {notebook_id}: {str(e)}")
        raise ValueError(f"Failed to retrieve relevant chunks: {str(e)}")  # ✅ plain exception


async def get_embedding_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get statistics about stored embeddings."""
    try:
        stats_query = text("""
            SELECT
                COUNT(*)                    AS total_embeddings,
                COUNT(DISTINCT source_id)   AS unique_sources,
                AVG(LENGTH(chunk))          AS avg_chunk_length,
                MAX(LENGTH(chunk))          AS max_chunk_length,
                MIN(LENGTH(chunk))          AS min_chunk_length
            FROM stud_hub_schema.embeddings
        """)
        result = await session.execute(stats_query)
        row = result.fetchone()

        if row is None:
            logger.warning("No rows returned from embedding stats query")
            return {
                "total_embeddings": 0,
                "unique_sources": 0,
                "avg_chunk_length": 0.0,
                "max_chunk_length": 0,
                "min_chunk_length": 0,
            }

        stats = {
            "total_embeddings": row.total_embeddings or 0,
            "unique_sources": row.unique_sources or 0,
            "avg_chunk_length": round(float(row.avg_chunk_length or 0), 2),
            "max_chunk_length": row.max_chunk_length or 0,
            "min_chunk_length": row.min_chunk_length or 0,
        }

        logger.info(f"Embedding stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting embedding stats: {str(e)}")
        raise ValueError(f"Failed to get embedding stats: {str(e)}")  # ✅ plain exception


# ---------------------------------------------------------------------------
# Legacy wrapper — do not add new callers, use semantic_search() directly
# ---------------------------------------------------------------------------
async def semantic_search_legacy(
    query: str,
    top_n: int = 5,
    source_ids: Optional[List[UUID]] = None,
    session: AsyncSession = None,
) -> List[Dict[str, Any]]:
    """Legacy semantic search wrapper for backward compatibility."""
    if session is None:
        raise ValueError("session is required for semantic_search_legacy")  # ✅ fail fast

    logger.info(f"Legacy semantic search for: '{query}' (top_n={top_n})")

    search_request = SemanticSearchRequest(
        query=query,
        top_n=top_n,
        source_ids=source_ids,
    )
    result = await semantic_search(search_request, session)
    return result["chunks"]
    # Exceptions propagate naturally — no need to catch and re-raise


async def semantic_search_simple(query: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """Simple semantic search without source filtering, manages its own session."""
    async with AsyncSessionLocal() as session:
        return await semantic_search_legacy(query, top_n, None, session)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
async def health_check() -> Dict[str, Any]:
    """Check embedding service health — Gemini API + database connectivity."""
    gemini_ok = False
    db_ok = False
    embedding_dim = 0
    stats: Dict[str, Any] = {}
    errors = []

    # Check Gemini API independently
    try:
        test_embedding = await embed_text("health check")
        embedding_dim = len(test_embedding)
        gemini_ok = True
    except Exception as e:
        errors.append(f"Gemini API: {str(e)}")
        logger.error(f"Health check — Gemini API failed: {str(e)}")

    # Check DB independently — one failing should not mask the other
    try:
        async with AsyncSessionLocal() as session:
            stats = await get_embedding_stats(session)
        db_ok = True
    except Exception as e:
        errors.append(f"Database: {str(e)}")
        logger.error(f"Health check — DB failed: {str(e)}")

    overall = "healthy" if (gemini_ok and db_ok) else (
        "degraded" if (gemini_ok or db_ok) else "unhealthy"
    )

    return {
        "status": overall,                      # "healthy" | "degraded" | "unhealthy"
        "gemini_api": "connected" if gemini_ok else "unreachable",
        "database": "connected" if db_ok else "unreachable",
        "embedding_dimension": embedding_dim,
        "database_stats": stats,
        **({"errors": errors} if errors else {}),  # only include if there are errors
    }
