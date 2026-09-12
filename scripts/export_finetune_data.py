import os
import json
import argparse
from dotenv import load_dotenv

load_dotenv()

def export_dataset(output_file: str = "data/finetune_data.jsonl"):
    """
    Export Q&A records with positive feedback (score == 1) from MongoDB
    into a JSONL dataset for QLoRA / OpenAI fine-tuning.
    """
    from app.db import db

    history = db.get_history(limit=1000)
    positive_samples = [item for item in history if item.get("feedback_score") == 1]

    if not positive_samples:
        print("⚠️ No positively rated questions (feedback_score = 1) found in database.")
        print("Will export all available history items as preliminary dataset...")
        positive_samples = history

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for item in positive_samples:
            question = item.get("question_text", "")
            answer = item.get("answer_text", "")
            if question and answer:
                # ChatML / Instruction format
                record = {
                    "messages": [
                        {"role": "system", "content": "You are an expert domain assistant."},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer}
                    ]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    print(f"✅ Successfully exported {count} fine-tuning pairs to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Q&A dataset for fine-tuning.")
    parser.add_argument("--output", type=str, default="data/finetune_data.jsonl", help="Output JSONL filepath")
    args = parser.parse_args()
    export_dataset(args.output)
