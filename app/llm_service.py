import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.db import db

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()


LANG_NAME_MAP = {
    "auto": "the same language as the user's question",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "ja": "Japanese",
    "zh": "Chinese",
    "ar": "Arabic"
}


def build_system_prompt(target_language: str = "auto") -> str:
    lang_name = LANG_NAME_MAP.get(target_language, "the same language as the user's question")
    return (
        f"You are an expert domain assistant. Answer the question fluently and naturally in {lang_name}, "
        "using the provided context including document text, image metadata (dimensions, format, color mode, file size), and OCR text extracted from images. "
        "When the user asks about an uploaded image or asks to fetch image info, present all relevant image details clearly."
    )


def build_user_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    if not context_chunks:
        context_str = "No relevant context found in uploaded documents."
    else:
        context_blocks = []
        for i, chunk in enumerate(context_chunks, start=1):
            source_info = f"[Source {i}: {chunk.get('title', 'Doc')} ({chunk.get('source', '')})]"
            context_blocks.append(f"{source_info}\n{chunk.get('text', '')}")
        context_str = "\n\n".join(context_blocks)

    return f"Context:\n{context_str}\n\nQuestion:\n{question}\n\nAnswer:"


def generate_answer(question: str, context_chunks: List[Dict[str, Any]], target_language: str = "auto") -> Dict[str, Any]:
    """Generate answer using OpenAI API or fallback smart synthesis if key is unavailable."""
    system_prompt = build_system_prompt(target_language)
    user_prompt = build_user_prompt(question, context_chunks)
    
    answer_text = ""
    model_version = OPENAI_MODEL

    if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client_kwargs = {"api_key": OPENAI_API_KEY}
            if OPENAI_BASE_URL:
                client_kwargs["base_url"] = OPENAI_BASE_URL
            client = OpenAI(**client_kwargs)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=600
            )
            answer_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM Error] OpenAI API call failed: {e}. Utilizing fallback generation.")
            answer_text = fallback_synthesize(question, context_chunks)
            model_version = "RAG-LocalFallback"
    else:
        answer_text = fallback_synthesize(question, context_chunks)
        model_version = "RAG-LocalFallback (No OpenAI Key Configured)"


    # Format context sources for logging and response
    sources = [
        {
            "title": c.get("title"),
            "source": c.get("source"),
            "page": c.get("page", 1),
            "similarity_score": c.get("similarity_score"),
            "excerpt": c.get("text")[:200] + "..." if len(c.get("text", "")) > 200 else c.get("text")
        }
        for c in context_chunks
    ]


    # Save to MongoDB / memory
    q_id = db.save_question_response(
        question=question,
        answer=answer_text,
        context_sources=sources,
        model_version=model_version
    )

    return {
        "question_id": q_id,
        "question": question,
        "answer": answer_text,
        "sources": sources,
        "model_version": model_version
    }


def extract_targeted_answer(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Extract only the specific lines matching the user's targeted question (e.g. total, name, date, dimensions)."""
    q_lower = question.lower().strip()
    
    # Keyword mapping
    targets = []
    if any(kw in q_lower for kw in ["total", "amount", "cost", "sum", "price"]):
        targets.extend(["total", "amount in words", "amount"])
    if any(kw in q_lower for kw in ["name", "student"]):
        targets.extend(["name", "student"])
    if any(kw in q_lower for kw in ["date"]):
        targets.extend(["date", "dddate"])
    if any(kw in q_lower for kw in ["receipt", "voucher", "number"]):
        targets.extend(["receipt", "voucher", "no:"])
    if any(kw in q_lower for kw in ["class", "course"]):
        targets.extend(["class", "course", "mba"])
    if any(kw in q_lower for kw in ["dimension", "size", "resolution", "dpi", "height", "width"]):
        targets.extend(["dimensions", "file size", "resolution", "aspect ratio", "dpi"])
    if "format" in q_lower:
        targets.extend(["format"])
    if "fee" in q_lower and not targets:
        targets.extend(["fee", "tuition", "development", "statutory", "total"])

    if not targets:
        return ""

    matched_sections = []
    for c in context_chunks:
        source = c.get('source', '')
        text = c.get('text', '')
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        matches = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(t in line_lower for t in targets):
                matches.append(line)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line and (next_line[0].isdigit() or next_line.startswith("INR")):
                        matches.append(next_line)

        if matches:
            unique_matches = []
            for m in matches:
                if m not in unique_matches:
                    unique_matches.append(m)
            matched_sections.append((source, unique_matches))

    if not matched_sections:
        return ""

    response = []
    for source, matches in matched_sections:
        response.append(f"**Targeted Result ({source})**:")
        for m in matches:
            response.append(f"- {m}")
        response.append("")

    return "\n".join(response).strip()


def fallback_synthesize(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Synthesize extracted text snippets and image info directly when OpenAI API is not configured."""
    if not context_chunks:
        return (
            "I could not find any relevant information in the uploaded domain documents "
            "to answer your question. Please try rephrasing or upload relevant documents."
        )

    # First attempt targeted answer extraction for specific queries
    targeted_answer = extract_targeted_answer(question, context_chunks)
    if targeted_answer:
        return f"{targeted_answer}\n\n*(Note: Add your `OPENAI_API_KEY` in `.env` for full GPT-4o summarization).*"

    # Default full synthesis for broad/summary queries
    response = [
        "Based on the retrieved domain documents and images, here is the relevant information:\n"
    ]
    for i, c in enumerate(context_chunks, 1):
        title = c.get('title', 'Document')
        source = c.get('source', '')
        text = c.get('text', '').strip()
        is_image = any(source.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".svg"])
        
        if is_image:
            response.append(f"**Image Info ({source})**:")
        else:
            response.append(f"**From {title}**:")
        response.append(f"{text}\n")

    response.append("*(Note: Add your `OPENAI_API_KEY` in `.env` to enable full GPT-4o image & document summarization).*")
    return "\n".join(response)
