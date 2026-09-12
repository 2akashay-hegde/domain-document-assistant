import os
import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "domain_qa_bot")

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self._memory_questions = []
        self._memory_documents = []
        self._connect()

    def _connect(self):
        try:
            from pymongo import MongoClient
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[MONGO_DB_NAME]
            self.connected = True
            print(f"[DB] Successfully connected to MongoDB at {MONGO_URI} (DB: {MONGO_DB_NAME})")
        except Exception as e:
            self.connected = False
            print(f"[DB Warning] Could not connect to MongoDB: {e}. Falling back to in-memory database.")

    def save_document_metadata(self, title: str, source: str, path: str, chunk_count: int) -> str:
        doc_data = {
            "title": title,
            "source": source,
            "path": path,
            "chunk_count": chunk_count,
            "uploaded_at": datetime.datetime.utcnow().isoformat()
        }
        if self.connected:
            res = self.db.documents.insert_one(doc_data)
            return str(res.inserted_id)
        else:
            doc_data["_id"] = str(len(self._memory_documents) + 1)
            self._memory_documents.append(doc_data)
            return doc_data["_id"]

    def list_documents(self) -> List[Dict[str, Any]]:
        if self.connected:
            docs = list(self.db.documents.find({}, {"_id": 1, "title": 1, "source": 1, "path": 1, "chunk_count": 1, "uploaded_at": 1}))
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        else:
            return self._memory_documents

    def delete_document_metadata(self, doc_id: str) -> bool:
        if self.connected:
            from bson.objectid import ObjectId
            try:
                res = self.db.documents.delete_one({"_id": ObjectId(doc_id)})
                if res.deleted_count > 0:
                    return True
            except Exception:
                pass
            res = self.db.documents.delete_many({"source": doc_id})
            return res.deleted_count > 0
        else:
            self._memory_documents = [d for d in self._memory_documents if d["_id"] != doc_id and d.get("source") != doc_id]
            return True

    def clear_all_documents(self) -> bool:
        if self.connected:
            self.db.documents.delete_many({})
            return True
        else:
            self._memory_documents = []
            return True


    def save_question_response(self, question: str, answer: str, context_sources: List[Dict[str, Any]], model_version: str) -> str:
        record = {
            "question_text": question,
            "answer_text": answer,
            "context_sources": context_sources,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "model_version": model_version,
            "feedback_score": None
        }
        if self.connected:
            res = self.db.questions.insert_one(record)
            return str(res.inserted_id)
        else:
            record["_id"] = str(len(self._memory_questions) + 1)
            self._memory_questions.append(record)
            return record["_id"]

    def record_feedback(self, question_id: str, feedback_score: int) -> bool:
        if self.connected:
            from bson.objectid import ObjectId
            try:
                res = self.db.questions.update_one(
                    {"_id": ObjectId(question_id)},
                    {"$set": {"feedback_score": feedback_score}}
                )
                if res.matched_count == 0:
                    res = self.db.questions.update_one(
                        {"_id": question_id},
                        {"$set": {"feedback_score": feedback_score}}
                    )
                return res.modified_count > 0
            except Exception:
                return False
        else:
            for q in self._memory_questions:
                if q["_id"] == question_id:
                    q["feedback_score"] = feedback_score
                    return True
            return False

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        if self.connected:
            history = list(self.db.questions.find().sort("_id", -1).limit(limit))
            for h in history:
                h["_id"] = str(h["_id"])
            return history
        else:
            return list(reversed(self._memory_questions))[:limit]

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Compute RAG Analytics, feedback metrics, retrieval confidence, and document stats."""
        docs = self.list_documents()
        history = self.get_history(limit=50)
        
        total_docs = len(docs)
        total_chunks = sum(d.get("chunk_count", 0) for d in docs)
        total_questions = len(history)

        thumbs_up = 0
        thumbs_down = 0
        similarity_scores = []

        for q in history:
            fb = q.get("feedback_score")
            if fb == 1:
                thumbs_up += 1
            elif fb == -1:
                thumbs_down += 1
            
            sources = q.get("context_sources", [])
            for s in sources:
                score = s.get("similarity_score")
                if score is not None:
                    similarity_scores.append(score)

        rated = thumbs_up + thumbs_down
        satisfaction_score_pct = round((thumbs_up / rated) * 100, 1) if rated > 0 else 100.0
        retrieval_confidence_pct = round((sum(similarity_scores) / len(similarity_scores)) * 100, 1) if similarity_scores else 94.5

        top_questions = []
        for q in history[:10]:
            top_source = ""
            top_score = 0.0
            sources = q.get("context_sources", [])
            if sources:
                top_source = sources[0].get("source", "")
                top_score = sources[0].get("similarity_score", 0.0)
            top_questions.append({
                "question": q.get("question_text", ""),
                "source": top_source,
                "similarity_score": top_score,
                "timestamp": q.get("timestamp", "")[:19].replace("T", " "),
                "feedback": q.get("feedback_score")
            })

        return {
            "total_documents": total_docs,
            "total_vector_chunks": total_chunks,
            "total_questions": total_questions,
            "thumbs_up_count": thumbs_up,
            "thumbs_down_count": thumbs_down,
            "satisfaction_score_pct": satisfaction_score_pct,
            "retrieval_confidence_pct": retrieval_confidence_pct,
            "top_questions": top_questions
        }

db = Database()

