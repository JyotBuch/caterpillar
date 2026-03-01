"""
ChromaDB-backed store for past inspection results.
Used for RAG: when assembling a report, retrieve similar past anomalies
to calibrate severity and surface recurring issues.
"""
import json
import uuid

import chromadb

from .schemas import ComponentInspection


class InspectionStore:
    def __init__(self):
        # In-memory for hackathon; swap to PersistentClient for persistence
        self._client = chromadb.Client()
        self._col = self._client.get_or_create_collection("inspections")

    def add(self, inspection: ComponentInspection) -> None:
        """Store a completed inspection result."""
        if not inspection.anomalies:
            return

        docs, ids, metas = [], [], []
        for anomaly in inspection.anomalies:
            doc = (
                f"{inspection.component_category}: "
                f"{anomaly.condition_description} "
                f"[{anomaly.severity}] → {anomaly.recommended_action}"
            )
            docs.append(doc)
            ids.append(str(uuid.uuid4()))
            metas.append({
                "component_category": inspection.component_category,
                "severity": anomaly.severity,
                "component_type": anomaly.component_type,
            })

        self._col.add(documents=docs, ids=ids, metadatas=metas)

    def get_similar(
        self,
        component_category: str,
        description: str,
        n: int = 3,
    ) -> list[str]:
        """Retrieve similar past anomalies for RAG context."""
        try:
            results = self._col.query(
                query_texts=[f"{component_category}: {description}"],
                n_results=min(n, self._col.count()),
                where={"component_category": component_category} if self._col.count() > 0 else None,
            )
            return results["documents"][0] if results["documents"] else []
        except Exception:
            return []

    def count(self) -> int:
        return self._col.count()


# Singleton instance
store = InspectionStore()
