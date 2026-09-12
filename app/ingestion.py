import os
import re
import glob
import fitz  # PyMuPDF
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.db import db

load_dotenv()

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
RAW_DOCS_DIR = os.getenv("RAW_DOCS_DIR", "./data/raw_docs")

# Initialize Embedding Model & ChromaDB Client
print(f"[Ingestion] Loading embedding model: {EMBEDDING_MODEL_NAME}...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
collection = chroma_client.get_or_create_collection(name="domain_documents")


def clean_text(text: str) -> str:
    """Clean raw extracted text by normalizing whitespace."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\r\n]+', '\n', text)
    return text.strip()


def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF, Markdown, or plain text file."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return clean_text(text)
    
    elif ext in [".md", ".txt"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return clean_text(f.read())
            
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Split text into manageable overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)


def process_single_file(file_path: str) -> dict:
    """Ingest a single document file, compute embeddings, store in ChromaDB & MongoDB."""
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    ext = os.path.splitext(file_path)[1].lower()
    
    chunks_with_meta = []
    
    if ext == ".pdf":
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = clean_text(page.get_text())
                if page_text:
                    p_chunks = chunk_text(page_text)
                    for ch in p_chunks:
                        chunks_with_meta.append({"text": ch, "page": page_num})
    elif ext in [".md", ".txt"]:
        raw_text = extract_text_from_file(file_path)
        if raw_text:
            p_chunks = chunk_text(raw_text)
            for ch in p_chunks:
                chunks_with_meta.append({"text": ch, "page": 1})
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    if not chunks_with_meta:
        return {"status": "skipped", "reason": "no content extracted", "filename": filename}
        
    chunks = [c["text"] for c in chunks_with_meta]
    
    # Generate embeddings
    embeddings = embedding_model.encode(chunks).tolist()
    
    # Generate IDs & Metadata for ChromaDB
    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": filename,
            "title": title,
            "chunk_index": i,
            "page": chunks_with_meta[i]["page"],
            "path": file_path
        }
        for i in range(len(chunks))
    ]
    
    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )
    
    # Save document metadata in MongoDB
    doc_id = db.save_document_metadata(
        title=title,
        source=filename,
        path=file_path,
        chunk_count=len(chunks)
    )
    
    return {
        "status": "success",
        "doc_id": doc_id,
        "filename": filename,
        "chunks_processed": len(chunks)
    }



def ingest_directory(dir_path: str = RAW_DOCS_DIR) -> list[dict]:
    """Ingest all supported documents in the specified directory."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        
    supported_extensions = ["*.pdf", "*.md", "*.txt"]
    files_to_process = []
    for ext in supported_extensions:
        files_to_process.extend(glob.glob(os.path.join(dir_path, ext)))
        
    results = []
    for fpath in files_to_process:
        try:
            res = process_single_file(fpath)
            results.append(res)
        except Exception as e:
            results.append({"status": "error", "filename": os.path.basename(fpath), "error": str(e)})
            
    return results
