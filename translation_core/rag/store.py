from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


@dataclass
class RAGExample:
    chapter_id: str
    source_text: str
    translated_text: str
    distance: float


class RAGStore:
    _COLLECTION_NAME = "chapters"
    _EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, persist_directory: str | Path):
        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self._EMBEDDING_MODEL_NAME
        )
        self._collection = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            embedding_function=self._embedding_function,
        )

    def add_chapter(self, chapter_id: str, source_text: str, translated_text: str) -> None:
        self._collection.upsert(
            ids=[chapter_id],
            documents=[source_text],
            metadatas=[{"translated_text": translated_text}],
        )

    def query(self, text: str, top_k: int = 3) -> list[RAGExample]:
        if self._collection.count() == 0:
            return []

        result = self._collection.query(
            query_texts=[text],
            n_results=min(top_k, self._collection.count()),
        )

        examples = []
        for chapter_id, source_text, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            examples.append(
                RAGExample(
                    chapter_id=chapter_id,
                    source_text=source_text,
                    translated_text=metadata["translated_text"],
                    distance=distance,
                )
            )
        return examples
