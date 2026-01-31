import os
from typing import List
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class RAGService:
    def __init__(
        self,
        persist_dir="backend/vectorstore/chroma",
        collection_name="insurance_faqs",
        embedding_model="sentence-transformers/all-mpnet-base-v2",
    ):
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(name=collection_name)

        self.embedder = SentenceTransformer(embedding_model)

        self.has_data = self.collection.count() > 0

    def check_collection_status(self) -> bool:
        """Return True if collection has documents."""
        try:
            count = self.collection.count()
            return count > 0
        except Exception:
            return False

    def retrieve(self, query: str, k: int = 4) -> List[str]:
        """Retrieve top-k relevant documents from Chroma."""
        if not self.has_data:
            return []

        try:
            embedding = self.embedder.encode(
                [query], normalize_embeddings=True
            ).tolist()

            results = self.collection.query(
                query_embeddings=embedding,
                n_results=k,
                include=["documents", "metadatas"],
            )

            docs = results.get("documents", [[]])
            if docs and docs[0]:
                return docs[0]

        except Exception:
            return []

        return []
