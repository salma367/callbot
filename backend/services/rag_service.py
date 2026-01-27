import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader


class RAGService:
    def __init__(
        self,
        persist_dir="backend/vectorstore/chroma",  # EXACT path
        collection_name="insurance_faqs",
    ):
        # Ensure directory exists
        os.makedirs(persist_dir, exist_ok=True)

        # 1️⃣ Initialize Persistent Chroma client
        try:
            self.client = chromadb.PersistentClient(
                path=persist_dir, settings=Settings(anonymized_telemetry=False)
            )
        except Exception as e:
            print(f"❌ Failed to initialize Chroma client: {e}")
            raise

        # 2️⃣ Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(name=collection_name)
            print(f"✅ Connected to collection: {collection_name}")
        except Exception as e:
            print(f"❌ Failed to get/create collection: {e}")
            raise

        # 3️⃣ Embedder
        try:
            self.embedder = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            print("✅ SentenceTransformer loaded")
        except Exception as e:
            print(f"❌ Failed to load embedder: {e}")
            raise

        # Check if collection has data
        self.check_collection_status()

    def check_collection_status(self):
        """Check if collection has documents."""
        try:
            count = self.collection.count()
            print(f"📊 Collection has {count} documents")
            return count > 0
        except Exception as e:
            print(f"⚠️ Could not count documents: {e}")
            return False

    def retrieve(self, query: str, k: int = 4) -> List[str]:
        # First check if collection has data
        try:
            if self.collection.count() == 0:
                print("⚠️ RAG collection is empty!")
                return []
        except Exception:
            print("⚠️ Could not check collection count")
            return []

        # Embed query
        try:
            embedding = self.embedder.encode([query]).tolist()
        except Exception as e:
            print(f"❌ Failed to embed query: {e}")
            return []

        # Query collection
        try:
            results = self.collection.query(
                query_embeddings=embedding,
                n_results=k,
            )

            # Debug: print what we found
            print(f"🔍 Query: '{query}'")
            print(f"📄 Retrieved {len(results.get('documents', [[]])[0])} documents")

            docs = results.get("documents", [[]])
            if docs and docs[0]:
                return docs[0]
            return []

        except Exception as e:
            print(f"❌ Failed to query collection: {e}")
            return []

    # ... rest of your methods ...
