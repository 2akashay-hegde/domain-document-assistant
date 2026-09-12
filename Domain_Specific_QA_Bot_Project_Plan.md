# Domain-Specific Q&A Bot Project Plan

## Overview
A comprehensive project plan for creating a Domain-Specific Question & Answering (Q&A) Chatbot utilizing Retrieval-Augmented Generation (RAG), vector databases, and LLMs.

---

## Database Schemas

### Documents Table
```sql
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(500),
    path VARCHAR(500),
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Questions Table
```sql
CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    answer_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50),
    feedback_score INT DEFAULT 0 -- e.g., +1 like, -1 dislike, 0 none
);
```

---

## API Contracts

### 1. Ask Question
- **Endpoint**: `POST /ask`
- **Request JSON**:
```json
{
  "question": "What is RAG and how does it work?"
}
```
- **Response JSON**:
```json
{
  "question_id": 42,
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "sources": [
    { "doc_id": 3, "chunk_id": 7, "text": "..." },
    { "doc_id": 5, "chunk_id": 2, "text": "..." }
  ]
}
```

### 2. Send Feedback
- **Endpoint**: `POST /feedback`
- **Request JSON**:
```json
{
  "question_id": 42,
  "score": 1
}
```
- **Response JSON**:
```json
{
  "status": "ok"
}
```

---

## Expected Challenges & Mitigations

1. **Hallucinations (wrong answers)**
   - *Mitigation*: Strong RAG; instruct model to state "I don't know" if context is insufficient; log bad answers for corpus enhancement.
2. **Slow Response Time**
   - *Mitigation*: Use lightweight embeddings (`MiniLM-L6-v2`); cache frequent responses; fast LLM API.
3. **Data Licensing**
   - *Mitigation*: Use domain documents with proper authorization or open licenses.
4. **Fine-Tuning Complexity**
   - *Mitigation*: RAG-first approach; parameter-efficient methods (LoRA/QLoRA) if fine-tuning is required.

---

## Deliverables & Accomplishments

1. ✅ Working FastAPI backend with RAG Q&A pipeline.
2. ✅ ChromaDB vector database populated with domain documents.
3. ✅ MongoDB database logging questions, answers, and feedback.
4. ✅ Dual interface: Glassmorphism Web UI + Java Swing Desktop Client.
5. ✅ Fine-tuning exporter script & QLoRA notebook.
6. ✅ GitHub-ready repository with code, tests, and documentation.
