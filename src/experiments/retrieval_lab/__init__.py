"""Retrieval lab scaffold used to benchmark retrieval quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalDocument:
    """Simple retrieval document represented by id and content."""

    document_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalLab:
    """Minimal retrieval lab for evaluating hypotheses h1-h3."""

    def __init__(self, documents: list[RetrievalDocument] | None = None) -> None:
        self.documents = list(documents or [])

    def add_document(self, document: RetrievalDocument) -> None:
        self.documents.append(document)

    def retrieve(self, query: str, limit: int = 3) -> list[RetrievalDocument]:
        query = (query or "").strip().lower()
        if not query:
            return []
        scored = []
        for document in self.documents:
            content = (document.content or "").lower()
            score = sum(1 for token in query.split() if token in content)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [document for _, document in scored[:limit]]

    def validate(self, query: str, limit: int = 3) -> dict[str, Any]:
        matches = self.retrieve(query, limit=limit)
        return {
            "query": query,
            "matches": [
                {"id": document.document_id, "content": document.content, "metadata": document.metadata}
                for document in matches
            ],
            "match_count": len(matches),
            "status": "ready",
        }


__all__ = ["RetrievalDocument", "RetrievalLab"]
