import os
import uuid
from collections import defaultdict
from typing import Any

import chromadb

from .transcript_parser import extract_chunks, parse_raw


class KnowledgeBase:
    def __init__(self):
        self._client = chromadb.Client()
        self._criteria_col = self._client.get_or_create_collection("criteria")
        self._findings_col = self._client.get_or_create_collection("findings")

    def _reset_collections(self) -> None:
        for name in ("criteria", "findings"):
            try:
                self._client.delete_collection(name)
            except Exception:
                pass
        self._criteria_col = self._client.get_or_create_collection("criteria")
        self._findings_col = self._client.get_or_create_collection("findings")

    def load_transcript(
        self,
        path: str,
        *,
        transcript_id: str | None = None,
        video_id: str | None = None,
        video_title: str | None = None,
        video_file: str | None = None,
        reset: bool = True,
    ) -> int:
        if not path or not os.path.exists(path):
            return 0

        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw_text = handle.read()
        except Exception:
            return 0

        segments = parse_raw(raw_text)
        chunks = extract_chunks(segments)
        if not chunks:
            if reset:
                self._reset_collections()
            return 0

        if reset:
            self._reset_collections()

        criteria_docs: list[str] = []
        criteria_ids: list[str] = []
        criteria_metas: list[dict[str, Any]] = []

        findings_docs: list[str] = []
        findings_ids: list[str] = []
        findings_metas: list[dict[str, Any]] = []

        for chunk in chunks:
            chunk_type = chunk.get("chunk_type")
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue

            metadata: dict[str, Any] = {
                "component_type": str(chunk.get("component_type", "unknown")),
                "timestamp_start": float(chunk.get("timestamp_start", 0.0)),
                "timestamp_end": float(chunk.get("timestamp_end", 0.0)),
                "transcript_id": str(transcript_id or os.path.basename(path)),
                "video_id": str(video_id or ""),
                "video_title": str(video_title or ""),
                "video_file": str(video_file or ""),
            }

            if chunk_type == "criteria":
                criteria_docs.append(text)
                criteria_ids.append(str(uuid.uuid4()))
                criteria_metas.append(metadata)
                continue

            severity = chunk.get("severity")
            nick_verdict = chunk.get("nick_verdict")
            metadata.update({
                "severity": str(severity) if severity is not None else "",
                "nick_verdict": str(nick_verdict) if nick_verdict is not None else "",
            })
            findings_docs.append(text)
            findings_ids.append(str(uuid.uuid4()))
            findings_metas.append(metadata)

        if criteria_docs:
            self._criteria_col.add(documents=criteria_docs, ids=criteria_ids, metadatas=criteria_metas)
        if findings_docs:
            self._findings_col.add(documents=findings_docs, ids=findings_ids, metadatas=findings_metas)

        return len(criteria_docs) + len(findings_docs)

    def load_transcripts(self, sources: list[dict[str, str]]) -> int:
        if not sources:
            return 0

        self._reset_collections()
        total_loaded = 0
        for source in sources:
            total_loaded += self.load_transcript(
                source.get("path", ""),
                transcript_id=source.get("transcript_id"),
                video_id=source.get("video_id"),
                video_title=source.get("video_title"),
                video_file=source.get("video_file"),
                reset=False,
            )
        return total_loaded

    def get_inspection_criteria(self, component_type: str) -> str:
        if not component_type:
            return ""
        try:
            if self._criteria_col.count() == 0:
                return ""
            results = self._criteria_col.query(
                query_texts=[component_type],
                n_results=1,
                where={"component_type": component_type},
            )
            documents = results.get("documents") or []
            if not documents or not documents[0]:
                return ""
            return str(documents[0][0])
        except Exception:
            return ""

    def get_similar_findings(
        self,
        component_type: str,
        condition_description: str,
        n: int = 3,
    ) -> list[dict[str, Any]]:
        if not component_type:
            return []
        try:
            total = self._findings_col.count()
            if total == 0:
                return []

            query = f"{component_type}: {condition_description or ''}".strip()
            results = self._findings_col.query(
                query_texts=[query],
                n_results=min(max(n, 1), total),
                where={"component_type": component_type},
            )

            documents = (results.get("documents") or [[]])[0]
            metadatas = (results.get("metadatas") or [[]])[0]
            items: list[dict[str, Any]] = []

            for index, text in enumerate(documents):
                meta = metadatas[index] if index < len(metadatas) else {}
                items.append({
                    "text": str(text),
                    "severity": meta.get("severity"),
                    "nick_verdict": meta.get("nick_verdict"),
                    "timestamp_start": meta.get("timestamp_start"),
                })
            return items
        except Exception:
            return []

    def get_all_criteria(self) -> dict[str, str]:
        try:
            if self._criteria_col.count() == 0:
                return {}

            records = self._criteria_col.get(include=["documents", "metadatas"])
            documents = records.get("documents") or []
            metadatas = records.get("metadatas") or []
            by_component: dict[str, list[str]] = defaultdict(list)

            for index, text in enumerate(documents):
                meta = metadatas[index] if index < len(metadatas) else {}
                component_type = str(meta.get("component_type", "unknown"))
                cleaned = str(text).strip()
                if cleaned:
                    by_component[component_type].append(cleaned)

            merged: dict[str, str] = {}
            for component_type, snippets in by_component.items():
                unique_snippets = list(dict.fromkeys(snippets))
                merged[component_type] = "\n\n".join(unique_snippets)
            return merged
        except Exception:
            return {}

    def get_component_coverage(self) -> list[str]:
        criteria = set(self.get_all_criteria().keys())
        try:
            if self._findings_col.count() > 0:
                findings = self._findings_col.get(include=["metadatas"]).get("metadatas") or []
                for meta in findings:
                    component_type = str((meta or {}).get("component_type", "")).strip()
                    if component_type:
                        criteria.add(component_type)
        except Exception:
            pass
        return sorted(criteria)

    def search_transcript(
        self,
        query: str,
        n: int = 5,
        video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        text_query = (query or "").strip()
        if not text_query:
            return []

        where = {"video_id": video_id} if video_id else None
        results: list[dict[str, Any]] = []

        def _collect(collection, chunk_type: str) -> None:
            try:
                total = collection.count()
                if total == 0:
                    return

                kwargs: dict[str, Any] = {
                    "query_texts": [text_query],
                    "n_results": min(max(n, 1), total),
                    "include": ["documents", "metadatas", "distances"],
                }
                if where is not None:
                    kwargs["where"] = where

                response = collection.query(**kwargs)
                documents = (response.get("documents") or [[]])[0]
                metadatas = (response.get("metadatas") or [[]])[0]
                distances = (response.get("distances") or [[]])[0]

                for index, doc in enumerate(documents):
                    meta = metadatas[index] if index < len(metadatas) else {}
                    distance = distances[index] if index < len(distances) else None
                    score = float(1.0 / (1.0 + float(distance))) if isinstance(distance, (float, int)) else None
                    results.append({
                        "chunk_type": chunk_type,
                        "component_type": meta.get("component_type"),
                        "text": str(doc),
                        "timestamp_start": meta.get("timestamp_start"),
                        "timestamp_end": meta.get("timestamp_end"),
                        "severity": meta.get("severity") or None,
                        "nick_verdict": meta.get("nick_verdict") or None,
                        "video_id": meta.get("video_id") or "",
                        "video_title": meta.get("video_title") or "",
                        "video_file": meta.get("video_file") or "",
                        "score": score,
                    })
            except Exception:
                return

        _collect(self._findings_col, "finding")
        _collect(self._criteria_col, "criteria")

        results.sort(key=lambda item: (item.get("score") or 0.0), reverse=True)
        return results[: max(n, 1)]


kb = KnowledgeBase()
