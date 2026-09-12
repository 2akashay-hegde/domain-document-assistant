import os
from typing import List, Dict, Any, Optional
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")

# Reuse embedding model & ChromaDB collection from app.ingestion to save RAM and initialization time
from app.ingestion import embedding_model, collection



def retrieve_context(query: str, top_k: int = 5, document_source: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve top_k most relevant chunks for a given search query.
    Optionally filters by specific document source filename.
    """
    if not query.strip():
        return []

    # Encode query string
    query_embedding = embedding_model.encode([query]).tolist()

    query_kwargs = {
        "query_embeddings": query_embedding,
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }

    # Apply document filter if requested
    if document_source and document_source != "all":
        query_kwargs["where"] = {"source": document_source}

    results = collection.query(**query_kwargs)

    chunks = []
    if results and results.get("documents") and len(results["documents"]) > 0:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc_text, meta, dist in zip(docs, metas, dists):
            chunks.append({
                "text": doc_text,
                "source": meta.get("source", "Unknown"),
                "title": meta.get("title", "Untitled"),
                "page": meta.get("page", 1),
                "path": meta.get("path", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "distance": round(float(dist), 4),
                "similarity_score": round(1.0 / (1.0 + float(dist)), 4)
            })

    return chunks
