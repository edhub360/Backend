import os
import numpy as np
from typing import List
import google.generativeai as genai

# Configure the API key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=api_key)

def embed_texts(texts: List[str], model: str = "models/text-embedding-004") -> np.ndarray:
    """Generate embeddings for a list of texts."""
    if not texts:
        return np.array([])
    
    try:
        # Generate embeddings using Gemini API
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        
        return np.array(embeddings, dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f"Error generating embeddings: {str(e)}")

def embed_query(query: str, model: str = "models/text-embedding-004") -> np.ndarray:
    """Generate embedding for a single query."""
    try:
        result = genai.embed_content(
            model=model,
            content=query,
            task_type="retrieval_query"
        )
        return np.array(result['embedding'], dtype=np.float32).reshape(1, -1)
    except Exception as e:
        raise RuntimeError(f"Error generating query embedding: {str(e)}")
