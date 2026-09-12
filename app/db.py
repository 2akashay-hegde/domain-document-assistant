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
                return res.deleted_count > 0
            except Exception:
                res = self.db.documents.delete_one({"_id": doc_id})
                return res.deleted_count > 0
        else:
            self._memory_documents = [d for d in self._memory_documents if d["_id"] != doc_id]
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
            questions = list(self.db.questions.find().sort("timestamp", -1).limit(limit))
            for q in questions:
                q["_id"] = str(q["_id"])
            return questions
        else:
            return sorted(self._memory_questions, key=lambda x: x["timestamp"], reverse=True)[:limit]

db = Database()
