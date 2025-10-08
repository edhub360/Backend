import os
import google.generativeai as genai
from sqlalchemy import select
from models import Embedding, Source
from db import AsyncSessionLocal
import numpy as np
from typing import List, Optional
from uuid import UUID

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def chunk_text(text, max_tokens=500):
    """Split text into chunks of specified token size"""
    if not text or len(text.strip()) == 0:
        return []
    
    words = text.split()
    chunks = [" ".join(words[i:i+max_tokens]) for i in range(0, len(words), max_tokens)]
    print(f"DEBUG: Created {len(chunks)} chunks from {len(words)} words")
    return [chunk for chunk in chunks if len(chunk.strip()) > 0]

async def embed_text(text):
    """Generate embeddings using Gemini API"""
    try:
        print(f"DEBUG: Generating embedding for text: {text[:100]}...")
        
        # CORRECT: Use 'content' parameter (not 'text')
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="semantic_similarity"
        )
        
        print(f"DEBUG: Successfully generated embedding with dimension: {len(result['embedding'])}")
        return result['embedding']
    except Exception as e:
        print(f"DEBUG: Embedding error: {e}")
        raise

async def embed_texts_batch(texts):
    """Generate embeddings for multiple texts"""
    try:
        print(f"DEBUG: Generating embeddings for {len(texts)} texts")
        vectors = []
        
        for text in texts:
            if len(text.strip()) == 0:
                continue
            vector = await embed_text(text)
            vectors.append(vector)
            
        print(f"DEBUG: Generated {len(vectors)} embeddings")
        return vectors
    except Exception as e:
        print(f"DEBUG: Batch embedding error: {e}")
        raise

async def store_embeddings_for_source(source: Source, session):
    """Process and store embeddings for a source"""
    print(f"DEBUG: Starting embedding generation for source {source.id}")
    
    if not source.extracted_text or len(source.extracted_text.strip()) < 10:
        print(f"DEBUG: Insufficient text content: {len(source.extracted_text) if source.extracted_text else 0} characters")
        return []
        
    chunks = chunk_text(source.extracted_text)
    if not chunks:
        print("DEBUG: No valid chunks created")
        return []
        
    print(f"DEBUG: Processing {len(chunks)} chunks")
    
    try:
        # Generate embeddings for all chunks
        vectors = await embed_texts_batch(chunks)
        
        if len(vectors) != len(chunks):
            print(f"DEBUG: Mismatch: {len(chunks)} chunks but {len(vectors)} vectors")
            return []
        
        embeddings = []
        for chunk, vector in zip(chunks, vectors):
            emb = Embedding(source_id=source.id, chunk=chunk, vector=vector)
            session.add(emb)
            embeddings.append(emb)
        
        await session.commit()
        print(f"DEBUG: Successfully stored {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        print(f"DEBUG: Failed to store embeddings: {e}")
        raise

async def semantic_search(query: str, top_n: int = 5, source_ids: Optional[List[UUID]] = None, session = None):
    """Perform semantic search across embeddings"""
    try:
        print(f"DEBUG: Semantic search for: '{query}' (top {top_n})")
        
        # Generate embedding for the query
        query_vector = await embed_text(query)
        print(f"DEBUG: Generated query embedding with dimension: {len(query_vector)}")
        
        # Build the search query
        search_query = select(
            Embedding.id,
            Embedding.chunk,
            Embedding.source_id,
            # Calculate cosine similarity using pgvector
            Embedding.vector.cosine_distance(query_vector).label('distance')
        )
        
        # Filter by source_ids if provided
        if source_ids:
            search_query = search_query.where(Embedding.source_id.in_(source_ids))
        
        # Order by similarity (lower distance = higher similarity) and limit
        search_query = search_query.order_by('distance').limit(top_n)
        
        # Execute the query
        result = await session.execute(search_query)
        rows = result.fetchall()
        
        # Format results
        results = []
        for row in rows:
            # Convert distance to similarity score (1 - distance)
            similarity_score = 1 - row.distance
            results.append({
                "id": str(row.id),
                "chunk": row.chunk,
                "source_id": str(row.source_id),
                "score": round(similarity_score, 4)
            })
        
        print(f"DEBUG: Found {len(results)} similar chunks")
        return results
        
    except Exception as e:
        print(f"DEBUG: Semantic search error: {e}")
        raise

async def semantic_search_simple(query: str, top_n: int = 5):
    """Simple semantic search without source filtering"""
    async with AsyncSessionLocal() as session:
        return await semantic_search(query, top_n, None, session)
