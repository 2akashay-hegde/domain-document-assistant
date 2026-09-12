import os
from typing import List, Dict, Any
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")

# Load shared embedding model & ChromaDB client
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
collection = chroma_client.get_or_create_collection(name="domain_documents")


def retrieve_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top_k most relevant chunks for a given search query.
    Returns list of dicts with text, metadata, and distance.
    """
    if not query.strip():
        return []

    # Encode query string
    query_embedding = embedding_model.encode([query]).tolist()

    # Similarity search in ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

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
