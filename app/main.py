import os
import shutil
import io
import json
import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.ingestion import ingest_directory, process_single_file, RAW_DOCS_DIR, collection as chroma_collection
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
    top_k: Optional[int] = 5
    document_source: Optional[str] = "all"
    target_language: Optional[str] = "auto"


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
    
    # Step 1: Retrieve Context (with optional document scope filtering)
    context_chunks = retrieve_context(
        query=req.question,
        top_k=req.top_k or 5,
        document_source=req.document_source
    )
    
    # Step 2: Generate Answer via LLM Service (with target language support)
    result = generate_answer(
        question=req.question,
        context_chunks=context_chunks,
        target_language=req.target_language or "auto"
    )
    
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
    allowed_exts = [".pdf", ".md", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".svg"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed formats: {', '.join(allowed_exts)}")
    
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


@app.delete("/documents/{doc_source}")
def delete_document(doc_source: str):
    """Delete a document from ChromaDB, MongoDB metadata, and raw_docs filesystem."""
    try:
        # Delete from ChromaDB vector collection
        existing = chroma_collection.get(where={"source": doc_source})
        if existing and existing.get("ids"):
            chroma_collection.delete(ids=existing["ids"])
        
        # Delete from MongoDB
        db.delete_document_metadata(doc_source)
        
        # Delete file from raw_docs
        file_path = os.path.join(RAW_DOCS_DIR, doc_source)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"status": "ok", "message": f"Document {doc_source} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents")
@app.post("/documents/clear")
def clear_all_documents():
    """Clear all documents from ChromaDB, MongoDB metadata, and raw_docs directory."""
    try:
        # Delete all from ChromaDB
        existing_docs = chroma_collection.get()
        if existing_docs and existing_docs.get("ids"):
            chroma_collection.delete(ids=existing_docs["ids"])
            
        # Delete all from MongoDB/in-memory DB
        db.clear_all_documents()

        # Delete all files in raw_docs
        if os.path.exists(RAW_DOCS_DIR):
            for fname in os.listdir(RAW_DOCS_DIR):
                fpath = os.path.join(RAW_DOCS_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass

        return {"status": "ok", "message": "All uploaded documents deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



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


@app.get("/analytics")
def get_analytics():
    """Retrieve Visual RAG Analytics and System Quality metrics."""
    return db.get_analytics_summary()


@app.get("/export")
def export_session(format: str = "markdown"):
    """Export Q&A Session to Markdown, JSON, or PDF report."""
    history = db.get_history(limit=100)
    
    if format.lower() == "json":
        json_data = json.dumps({"session_export_time": datetime.datetime.utcnow().isoformat(), "qa_records": history}, indent=2)
        return Response(content=json_data, media_type="application/json", headers={"Content-Disposition": "attachment; filename=qa_session_report.json"})
    
    elif format.lower() == "pdf":
        try:
            from xhtml2pdf import pisa
        except ImportError:
            raise HTTPException(status_code=500, detail="xhtml2pdf is not installed.")
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Helvetica, Arial, sans-serif; padding: 20px; color: #0f172a; }}
                h1 {{ color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
                .meta {{ font-size: 12px; color: #64748b; margin-bottom: 20px; }}
                .qa-item {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px; margin-bottom: 16px; border-radius: 8px; }}
                .question {{ font-weight: bold; color: #4f46e5; font-size: 14px; margin-bottom: 6px; }}
                .answer {{ font-size: 13px; line-height: 1.5; color: #1e293b; margin-bottom: 10px; }}
                .sources {{ font-size: 11px; color: #64748b; border-top: 1px solid #cbd5e1; padding-top: 6px; }}
            </style>
        </head>
        <body>
            <h1>Domain Q&A Session Report</h1>
            <div class="meta">Exported: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Total Records: {len(history)}</div>
        """
        for idx, q in enumerate(reversed(history), 1):
            sources_str = ", ".join([f"{s.get('source')} ({(s.get('similarity_score', 0)*100):.1f}% match)" for s in q.get("context_sources", [])]) or "General Domain Knowledge"
            html_content += f"""
            <div class="qa-item">
                <div class="question">Q{idx}: {q.get('question_text', '')}</div>
                <div class="answer">{q.get('answer_text', '').replace('\n', '<br>')}</div>
                <div class="sources"><strong>Sources:</strong> {sources_str}</div>
            </div>
            """
        html_content += "</body></html>"
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_content.encode("utf-8")), pdf_buffer)
        if pisa_status.err:
            raise HTTPException(status_code=500, detail="Failed to render PDF export.")
        
        return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=qa_session_report.pdf"})
    
    else:  # default markdown
        md_lines = [
            "# 📄 Domain Q&A Session Report",
            f"**Generated At**: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Total Questions**: {len(history)}",
            "",
            "---",
            ""
        ]
        for idx, q in enumerate(reversed(history), 1):
            md_lines.append(f"### Q{idx}: {q.get('question_text', '')}")
            md_lines.append(f"**Timestamp**: {q.get('timestamp', '')}")
            md_lines.append("")
            md_lines.append(f"{q.get('answer_text', '')}")
            md_lines.append("")
            sources = q.get("context_sources", [])
            if sources:
                md_lines.append("**Sources & Knowledge Matches**:")
                for s in sources:
                    md_lines.append(f"- `{s.get('source')}` ({(s.get('similarity_score', 0)*100):.1f}% match)")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

        md_content = "\n".join(md_lines)
        return Response(content=md_content, media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=qa_session_report.md"})


