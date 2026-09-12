# Domain-Specific Q&A Bot 🤖

A production-ready, multimodal domain-specific Question & Answer Chatbot utilizing **Retrieval-Augmented Generation (RAG)**, **FastAPI**, **Sentence-Transformers**, **RapidOCR**, **ChromaDB**, **MongoDB**, and **OpenAI GPT**.

---

## 🌟 Key Features

- 📄 **Multimodal Ingestion**: Supports `.pdf`, `.md`, `.txt` files as well as `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`, `.svg` image files with automatic OCR text extraction (`rapidocr-onnxruntime` / `pytesseract`) and image specification metadata (dimensions, format, color mode, file size).
- 🧠 **Local Dense Embeddings**: Generates 384-dimensional vector embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
- 🔍 **Vector Search & Targeted Answers**: Persistent vector database storage and similarity search using **ChromaDB** with targeted key-value fact extraction (e.g. fees, names, dates, specs).
- 📊 **Visual RAG Analytics Dashboard**: Real-time modal UI featuring total documents indexed, vector chunk count, user satisfaction score (👍 % vs 👎 %), cosine similarity confidence metrics, and top FAQs.
- 🌐 **Multilingual Q&A Support**: Ask questions and synthesize answers in 12+ supported languages (English 🇬🇧, Hindi 🇮🇳, Kannada 🇮🇳, Tamil 🇮🇳, Telugu 🇮🇳, Spanish 🇪🇸, French 🇫🇷, German 🇩🇪, Japanese 🇯🇵, Chinese 🇨🇳, Arabic 🇸🇦, and Auto-Detect 🌐).
- 🎙️ **Voice Speech-to-Text & TTS**: Voice input (`🎤`) and vocal answer reading (`🔊 Read Answer`) with automatic locale adaptation for all languages.
- 📄 **Export Session (PDF / MD / JSON)**: Export active Q&A history or invoice breakdowns as formatted `.pdf`, `.md`, or `.json` reports.
- 🎨 **Dynamic Theme Color Switcher**: Toggle between `⚪ Pure White`, `🌫️ Soft Light Gray`, `🪻 Soft Lavender`, and `🌙 Midnight Dark` themes.
- 🧹 **Auto-Delete Setting**: Optional toggle to automatically purge uploaded documents upon tab or browser window closure.
- ☕ **Java Swing GUI Client**: Desktop GUI client included in `clients/JavaSwingClient.java`.
- 🗄️ **Flexible Database**: Question history, document metadata, and feedback scoring in **MongoDB** (with automatic in-memory fallback).

---

## 🏗️ Architecture Diagram

```
                 +--------------------------------------+
                 |  PDF / MD / TXT & PNG/JPG/WEBP Images |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 |     Document & Image Ingestion       |
                 |  (PyMuPDF, PIL Metadata & RapidOCR)  |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 |       Sentence-Transformers          |
                 |        (MiniLM-L6 Embeds)            |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 |               ChromaDB               | (Vector Store)
                 +------------------+-------------------+
                                    ^
                                    | Similarity Search
                                    v
+------------------+       +--------+-------------------+       +------------------+
|   Web Chat UI    | <---> |     FastAPI Backend        | <---> |   OpenAI GPT     |
| (Voice, Analytics|       | (RAG, Multilingual, Export)|       |   LLM Service    |
| & Theme Switcher)|       +--------+-------------------+       +------------------+
+------------------+                |
                                    v
                         +----------------------+
                         |       MongoDB        | (Document & Question Metadata)
                         +----------------------+
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
*(Optional: Add your `OPENAI_API_KEY` in `.env` to enable full GPT-4o synthesis).*

### 3. Ingest Sample Documents & Images
Place your domain documents or images in `data/raw_docs/` or run the sample document ingestion:
```bash
python ingest_docs.py
```

### 4. Start the Application
Launch the FastAPI server:
```bash
python run.py
```
Open your browser at **`http://localhost:8000`**.

---

## 📊 Endpoints & API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Glassmorphism Web Chat Interface |
| `/ask` | `POST` | Retrieve context & generate answer (`question`, `target_language`, `document_source`) |
| `/upload` | `POST` | Upload and immediately ingest `.pdf`, `.md`, `.txt`, or `.png`/`.jpg` images |
| `/documents` | `GET`, `DELETE` | List, delete single document, or clear all ingested knowledge |
| `/analytics` | `GET` | Returns RAG quality metrics, satisfaction rates, & confidence statistics |
| `/export` | `GET` | Export Q&A report as `.md`, `.json`, or `.pdf` (`?format=pdf\|markdown\|json`) |
| `/feedback` | `POST` | Record user feedback rating (👍 / 👎) |

---

## 🐳 Docker Deployment

To launch the application along with MongoDB using Docker Compose:
```bash
docker-compose up --build
```

---

## 📑 Project Report Summary

### Problem Statement
Organizations have vast amounts of domain-specific documents and image receipts/invoices that standard LLMs cannot answer without context or ground truth reference.

### Design Decisions
1. **RAG over Direct Fine-Tuning**: RAG allows instant updates by dropping new documents or images into `data/raw_docs/` without re-training models.
2. **Local Dense Embeddings & RapidOCR**: Processing OCR text and vector embeddings locally guarantees fast vector search and zero per-token embedding cost.
3. **MongoDB & In-Memory Fallback**: Storing question logs and feedback ratings allows tracking answer quality and building fine-tuning datasets over time.
