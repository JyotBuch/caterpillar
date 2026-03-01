from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


DATE_LINE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+—\s+(?P<equipment>[^—]+?)\s+—\s+(?P<description>.+)$"
)
STATUS_RE = re.compile(r"Status:\s*(Pending|Completed)", re.IGNORECASE)


@dataclass
class TicketEntry:
    ticket_id: str
    date: str
    equipment: str
    title: str
    content: str
    status: str
    severity: str
    component_type: str


class TicketMemory:
    def __init__(self) -> None:
        self._tickets: list[TicketEntry] = []

    @property
    def count(self) -> int:
        return len(self._tickets)

    def load_from_file(self, file_path: str) -> int:
        if not file_path or not os.path.exists(file_path):
            self._tickets = []
            return 0

        with open(file_path, "r", encoding="utf-8") as handle:
            raw_lines = [line.strip() for line in handle.readlines()]

        parsed: list[TicketEntry] = []

        for line in raw_lines:
            if (
                not line
                or line.startswith("INSPECTION MEMORY LOG")
                or line.startswith("ADDITIONAL MEMORY EVENTS")
                or line.startswith("END OF LOG")
            ):
                continue

            match = DATE_LINE_RE.match(line)
            if not match:
                continue

            date = match.group("date")
            equipment = match.group("equipment").strip()
            description = match.group("description").strip()

            status_match = STATUS_RE.search(description)
            status = status_match.group(1).lower() if status_match else "pending"

            clean_description = STATUS_RE.sub("", description)
            clean_description = clean_description.replace("—", " ").strip(" -")

            severity = self._derive_severity(clean_description)
            component_type = self._derive_component(clean_description)

            fingerprint = f"{date}|{equipment}|{clean_description}".encode("utf-8")
            ticket_id = hashlib.sha1(fingerprint).hexdigest()[:12]

            title = f"{equipment} — {clean_description[:70]}"
            parsed.append(
                TicketEntry(
                    ticket_id=ticket_id,
                    date=date,
                    equipment=equipment,
                    title=title,
                    content=clean_description,
                    status=status,
                    severity=severity,
                    component_type=component_type,
                )
            )

        self._tickets = parsed
        return len(self._tickets)

    def search(self, query: str, component_type: Optional[str] = None, limit: int = 10) -> list[dict]:
        needle = (query or "").strip().lower()
        if not needle:
            return []

        filtered = self._tickets
        if component_type:
            filtered = [ticket for ticket in filtered if ticket.component_type == component_type]

        scored: list[tuple[int, TicketEntry]] = []
        for ticket in filtered:
            haystack = f"{ticket.equipment} {ticket.title} {ticket.content}".lower()
            if needle in haystack:
                score = 100
            else:
                query_terms = [term for term in needle.split() if term]
                score = sum(10 for term in query_terms if term in haystack)

            if score > 0:
                scored.append((score, ticket))

        scored.sort(
            key=lambda item: (
                item[0],
                self._safe_date(item[1].date),
            ),
            reverse=True,
        )

        return [self._to_dict(ticket) for _, ticket in scored[: max(1, min(limit, 20))]]

    def get_by_id(self, ticket_id: str) -> Optional[dict]:
        for ticket in self._tickets:
            if ticket.ticket_id == ticket_id:
                return self._to_dict(ticket)
        return None

    def _to_dict(self, ticket: TicketEntry) -> dict:
        return {
            "id": ticket.ticket_id,
            "date": ticket.date,
            "equipment": ticket.equipment,
            "title": ticket.title,
            "content": ticket.content,
            "status": ticket.status,
            "severity": ticket.severity,
            "component_type": ticket.component_type,
        }

    def _derive_component(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ("hydraulic", "hose", "fluid")):
            return "hydraulic_system"
        if any(word in lower for word in ("tire", "brake", "axle")):
            return "undercarriage"
        if any(word in lower for word in ("oil", "engine", "coolant", "filter", "fuel", "battery")):
            return "engine_compartment"
        if any(word in lower for word in ("glass", "seat", "mirror", "light", "visibility")):
            return "cab_operator"
        if any(word in lower for word in ("bolt", "rust", "paint", "ladder", "joint", "lubrication")):
            return "structural_frame"
        return "general"

    def _derive_severity(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ("crack", "safety risk", "leak", "not functioning")):
            return "critical"
        if any(word in lower for word in ("worn", "weak", "low", "noise", "vibration", "repair")):
            return "moderate"
        return "minor"

    def _safe_date(self, date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            return datetime(1970, 1, 1)


ticket_memory = TicketMemory()
