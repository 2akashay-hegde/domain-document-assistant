import argparse
import sys
import os

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ingestion import ingest_directory, RAW_DOCS_DIR

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB & MongoDB.")
    parser.add_argument("--dir", type=str, default=RAW_DOCS_DIR, help="Path to raw documents directory")
    args = parser.parse_args()

    print(f"🚀 Starting document ingestion from directory: {args.dir}")
    results = ingest_directory(args.dir)
    
    print("\n--- Ingestion Results Summary ---")
    for r in results:
        status_icon = "✅" if r.get("status") == "success" else "⚠️"
        print(f"{status_icon} {r.get('filename')}: {r}")
    print("\n🎉 Ingestion complete!")
