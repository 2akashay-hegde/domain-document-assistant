import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.db import db

def analyze_system_logs():
    """Analyze Q&A logs, calculate quality metrics, and identify knowledge gaps."""
    print("📊 --- Domain Q&A System Analytics & Metrics Report ---")
    
    history = db.get_history(limit=1000)
    total_questions = len(history)
    
    if total_questions == 0:
        print("No questions logged in database yet. Ask a few questions in the web UI first!")
        return

    rated_items = [q for q in history if q.get("feedback_score") is not None]
    positive_ratings = [q for q in rated_items if q.get("feedback_score") == 1]
    negative_ratings = [q for q in rated_items if q.get("feedback_score") == -1]

    avg_score = (sum(q.get("feedback_score", 0) for q in rated_items) / len(rated_items)) if rated_items else 0.0
    good_pct = (len(positive_ratings) / len(rated_items) * 100) if rated_items else 0.0

    print(f"Total Questions Asked: {total_questions}")
    print(f"Total Rated Responses: {len(rated_items)}")
    print(f"👍 Positive Ratings: {len(positive_ratings)}")
    print(f"👎 Negative Ratings: {len(negative_ratings)}")
    print(f"⭐ Average Feedback Score: {avg_score:.2f}")
    print(f"🎯 Percent 'Good' Answers: {good_pct:.1f}%")
    print("-" * 50)

    # Context Gap Detection
    print("\n🔍 --- Potential Knowledge Gap Questions ---")
    gap_questions = [
        q for q in history
        if "could not find any relevant information" in q.get("answer_text", "").lower()
        or q.get("feedback_score") == -1
    ]

    if gap_questions:
        for i, q in enumerate(gap_questions[:10], 1):
            print(f"  {i}. Question: {q.get('question_text')}")
            print(f"     Answer Snippet: {q.get('answer_text')[:100]}...")
            print(f"     Feedback: {q.get('feedback_score')}\n")
    else:
        print("  No knowledge gaps or negative responses flagged!")

if __name__ == "__main__":
    analyze_system_logs()
