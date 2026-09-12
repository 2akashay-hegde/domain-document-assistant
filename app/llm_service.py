import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.db import db

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def build_system_prompt() -> str:
    return "You are an expert domain assistant. Use the provided context to answer the question. If the context is insufficient, say so clearly."


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


def generate_answer(question: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate answer using OpenAI API or fallback smart synthesis if key is unavailable."""
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(question, context_chunks)
    
    answer_text = ""
    model_version = OPENAI_MODEL

    if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
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


def fallback_synthesize(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Synthesize extracted text snippets directly when OpenAI API is not configured."""
    if not context_chunks:
        return (
            "I could not find any relevant information in the uploaded domain documents "
            "to answer your question. Please try rephrasing or upload relevant documents."
        )

    response = [
        "Based on the domain documents retrieved, here is the relevant information:\n"
    ]
    for i, c in enumerate(context_chunks, 1):
        title = c.get('title', 'Document')
        text = c.get('text', '').strip()
        response.append(f"📌 **From {title}**:")
        response.append(f"> {text}\n")

    response.append("*(Note: Add your `OPENAI_API_KEY` in `.env` to enable full GPT-3.5/GPT-4 summarization).*")
    return "\n".join(response)
