import os
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.ingestion import ingest_directory, process_single_file, RAW_DOCS_DIR
from app.retrieval import retrieve_context
from app.llm_service import generate_answer
from app.db import db

load_dotenv()

app = FastAPI(
    title="Domain-Specific Q&A Bot API",
    description="RAG System powered by FastAPI, ChromaDB, Sentence-Transformers, MongoDB, and OpenAI",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory (CSS / JS)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")



# Pydantic Schemas
class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3


class FeedbackRequest(BaseModel):
    question_id: str
    feedback_score: int


@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serve the Web Chat Interface."""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Domain Q&A Bot API is running! UI template not found.</h1>"


@app.post("/ask")
def ask_question(req: AskRequest):
    """Retrieve relevant document chunks and generate answer."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    # Step 1: Retrieve Context
    context_chunks = retrieve_context(req.question, top_k=req.top_k or 3)
    
    # Step 2: Generate Answer via LLM Service
    result = generate_answer(req.question, context_chunks)
    
    return result


@app.post("/ingest")
def trigger_ingestion():
    """Ingest all files in data/raw_docs/."""
    results = ingest_directory(RAW_DOCS_DIR)
    return {"message": "Ingestion process completed.", "results": results}


@app.post("/upload")
def upload_and_ingest_file(file: UploadFile = File(...)):
    """Upload a file to data/raw_docs/ and ingest immediately."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".md", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Only .pdf, .md, and .txt files are allowed.")
    
    os.makedirs(RAW_DOCS_DIR, exist_ok=True)
    save_path = os.path.join(RAW_DOCS_DIR, file.filename)
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    res = process_single_file(save_path)
    if res.get("status") == "error":
        raise HTTPException(status_code=500, detail=res.get("error"))
        
    return res


@app.get("/documents")
def get_documents():
    """List all ingested document metadata."""
    docs = db.list_documents()
    return {"documents": docs}


@app.get("/history")
def get_history(limit: int = 20):
    """Retrieve past questions & answers."""
    history = db.get_history(limit=limit)
    return {"history": history}


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Update feedback score for a question."""
    success = db.record_feedback(req.question_id, req.feedback_score)
    if not success:
        raise HTTPException(status_code=404, detail="Question ID not found or feedback update failed.")
    return {"status": "ok"}

