"""Chroma vector index backed by LangChain Gemini embeddings."""

from typing import Any, Dict, List, Optional

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class ChromaMemoryIndex:
    def __init__(
        self,
        path: str,
        embeddings: Optional[GoogleGenerativeAIEmbeddings],
        collection_name: str = "reasoningbank_memories",
    ) -> None:
        self.embeddings = embeddings
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def upsert(self, memory_id: str, text: str, metadata: Dict[str, Any]) -> None:
        if self.embeddings is None:
            raise RuntimeError("embeddings are required for indexing")
        vector = self.embeddings.embed_documents([text])[0]
        self.collection.upsert(
            ids=[memory_id],
            documents=[text],
            metadatas=[metadata],
            embeddings=[vector],
        )

    def query(
        self,
        text: str,
        limit: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self.embeddings is None:
            raise RuntimeError("embeddings are required for retrieval")
        vector = self.embeddings.embed_query(text)
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=limit,
            where=where,
            include=["metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        rows: List[Dict[str, Any]] = []
        for memory_id, metadata, distance in zip(ids, metadatas, distances):
            rows.append(
                {
                    "memory_id": memory_id,
                    "metadata": metadata or {},
                    "distance": float(distance),
                    "similarity": max(0.0, 1.0 - float(distance)),
                }
            )
        return rows
