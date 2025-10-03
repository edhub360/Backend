import os
import faiss
import numpy as np
import pickle
from typing import List, Tuple, Dict, Optional
from pathlib import Path

class FaissStore:
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = None
        self.metadata: List[Dict] = []
        
        # Storage paths
        self.storage_dir = Path(os.environ.get("FAISS_STORAGE_DIR", "./data"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "faiss_index.bin"
        self.metadata_path = self.storage_dir / "metadata.pkl"
        
        self._initialize_index()
        self._load_existing_data()
    
    def _initialize_index(self):
        """Initialize FAISS index."""
        self.index = faiss.IndexFlatL2(self.dimension)
    
    def _load_existing_data(self):
        """Load existing index and metadata if they exist."""
        try:
            if self.index_path.exists() and self.metadata_path.exists():
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load metadata
                with open(self.metadata_path, "rb") as f:
                    self.metadata = pickle.load(f)
                
                print(f"Loaded existing index with {self.index.ntotal} vectors")
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
            self._initialize_index()
            self.metadata = []
    
    def _save_data(self):
        """Save index and metadata to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_path))
            
            # Save metadata
            with open(self.metadata_path, "wb") as f:
                pickle.dump(self.metadata, f)
        except Exception as e:
            raise RuntimeError(f"Error saving FAISS data: {e}")
    
    def add_documents(self, embeddings: np.ndarray, texts: List[str], source: str):
        """Add documents to the index."""
        if embeddings.shape[0] != len(texts):
            raise ValueError("Number of embeddings must match number of texts")
        
        # Add embeddings to FAISS index
        self.index.add(embeddings)
        
        # Add metadata
        for text in texts:
            self.metadata.append({
                "text": text,
                "source": source
            })
        
        # Save to disk
        self._save_data()
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, str, float]]:
        """Search for similar documents."""
        if self.index.ntotal == 0:
            return []
        
        # Ensure query_embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search the index
        distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                metadata = self.metadata[idx]
                results.append((
                    metadata["text"],
                    metadata["source"],
                    float(distance)
                ))
        
        return results
    
    def get_stats(self) -> Dict:
        """Get statistics about the index."""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "total_documents": len(set(m["source"] for m in self.metadata))
        }

# Global FAISS store instance
_faiss_store: Optional[FaissStore] = None

def get_faiss_store(dimension: int = 768) -> FaissStore:
    """Get or create the global FAISS store instance."""
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FaissStore(dimension=dimension)
    return _faiss_store
