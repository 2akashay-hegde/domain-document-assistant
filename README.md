# Domain-Specific Q&A Bot 🤖

A production-ready, domain-specific Question & Answer Chatbot utilizing **Retrieval-Augmented Generation (RAG)**, **FastAPI**, **Sentence-Transformers**, **ChromaDB**, **MongoDB**, and **OpenAI GPT**.

---

## 🌟 Features

- **Document Ingestion**: Supports `.pdf`, `.md`, and `.txt` files with intelligent chunking (`langchain-text-splitters`) and PyMuPDF text extraction.
- **Local Dense Embeddings**: Generates 384-dimensional vector embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
- **Vector Search**: Persistent vector database storage and similarity search using **ChromaDB**.
- **Flexible Database**: Persistent question history, document metadata, and feedback scoring in **MongoDB** (with automatic in-memory fallback).
- **RAG LLM Synthesis**: Prompt-engineered OpenAI GPT synthesis (`gpt-3.5-turbo` / `gpt-4o`) with fallback snippet synthesis if API keys are missing.
- **Modern Web Interface**: Glassmorphism chat UI built into FastAPI supporting drag-and-drop file upload, source attributions, and feedback ratings.
- **Java Swing GUI Client**: Desktop client included in `clients/JavaSwingClient.java`.
- **Fine-Tuning Exporter**: CLI tool (`scripts/export_finetune_data.py`) to prepare ChatML dataset pairs from high-rated responses.
- **Analytics & Metrics**: Script (`scripts/evaluate_metrics.py`) to measure satisfaction rate, average feedback score, and context gap questions.
- **Docker Support**: Containerized with `Dockerfile` and `docker-compose.yml`.

---

## 🏗️ Architecture Diagram

```
                 +-----------------------+
                 |  PDF / MD / TXT Docs  |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 |  Document Ingestion   |
                 |  (PyMuPDF & Splitter) |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Sentence-Transformers |
                 |  (MiniLM-L6 Embeds)   |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 |       ChromaDB        | (Vector Store)
                 +-----------+-----------+
                             ^
                             | Similarity Search
                             v
+----------------+      +----+-------------------+      +----------------+
|  Web Chat UI   | ---> |   FastAPI Backend      | ---> |  OpenAI GPT    |
| / Java GUI     | <--- | (Retrieval & Prompt)   | <--- |  LLM Service   |
+----------------+      +----+-------------------+      +----------------+
                             |
                             v
                 +-----------------------+
                 |        MongoDB        | (Document & Question Metadata)
                 +-----------------------+
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup
Clone the repository and install Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your configuration:
```bash
cp .env.example .env
```
*(Optional: Add your `OPENAI_API_KEY` in `.env` to enable full GPT synthesis).*

### 3. Ingest Sample Documents
Place your domain documents in `data/raw_docs/` or run the sample document ingestion:
```bash
python ingest_docs.py
```

### 4. Start the Application
Launch the server:
```bash
python run.py
```
Open your browser at **`http://localhost:8000`**.

---

## 🐳 Docker Deployment

To launch the application along with MongoDB using Docker Compose:
```bash
docker-compose up --build
```

---

## 📊 Analytics & Evaluation

To evaluate system performance, user satisfaction rates, and detect knowledge gaps:
```bash
python scripts/evaluate_metrics.py
```

To export high-rated Q&A pairs for model fine-tuning:
```bash
python scripts/export_finetune_data.py --output data/finetune_data.jsonl
```

---

## 📑 Project Report Summary

### Problem Statement
Organizations have vast amounts of domain-specific documents (manuals, policies, medical records) that standard LLMs cannot answer without context or ground truth reference.

### Design Decisions
1. **RAG over Direct Fine-Tuning**: RAG allows instant updates by dropping new documents into `data/raw_docs/` without re-training models.
2. **Local Embedding Generation**: Offloading vector embeddings to `sentence-transformers` locally saves API costs and guarantees fast vector search.
3. **MongoDB Metadata Store**: Storing question logs and feedback ratings allows tracking answer quality and building fine-tuning datasets over time.

### Future Improvements
- Hybrid Search (BM25 keyword search + Dense Vector search).
- Multi-modal document ingestion (extracting charts and diagrams from PDFs).
