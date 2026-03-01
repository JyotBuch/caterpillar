import json
import uuid
from datetime import datetime, timezone

from groq import AsyncGroq

from .config import settings
from .i18n import get_report_prompt
from .prompts import REPORT_SYSTEM_PROMPT
from .schemas import ComponentInspection, InspectionReport, AnomalyItem, Severity
from .vector_store import store


_SEVERITY_RANK = {
    Severity.CRITICAL: 3,
    Severity.MODERATE: 2,
    Severity.MINOR: 1,
    Severity.NORMAL: 0,
}


def _worst(statuses: list[Severity]) -> Severity:
    return max(statuses, key=lambda s: _SEVERITY_RANK[s], default=Severity.NORMAL)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def assemble_report(inspections: list[ComponentInspection], language: str = "en") -> InspectionReport:
    """Aggregate component inspections into a CAT-style report using an LLM."""
    client = AsyncGroq(api_key=settings.groq_api_key)

    # Build context for the LLM
    inspection_summaries = []
    for insp in inspections:
        summary = {
            "component": insp.component_category,
            "description": insp.component_description,
            "overall_status": insp.overall_status,
            "voice_notes": insp.voice_notes,
            "anomalies": [
                {
                    "location": a.component_location,
                    "type": a.component_type,
                    "description": a.condition_description,
                    "severity": a.severity,
                    "action": a.recommended_action,
                }
                for a in insp.anomalies
            ],
        }

        # Augment with similar historical findings from vector store
        if insp.anomalies:
            similar = store.get_similar(insp.component_category, insp.component_description)
            if similar:
                summary["historical_context"] = similar

        inspection_summaries.append(summary)

    report_prompt = get_report_prompt(language)
    user_content = (
        "Generate a CAT Inspect report for the following component inspections:\n\n"
        + json.dumps(inspection_summaries, indent=2)
    )

    response = await client.chat.completions.create(
        model=settings.text_model,
        messages=[
            {"role": "system", "content": report_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        max_tokens=2000,
    )

    raw = _parse_json(response.choices[0].message.content)

    # Collect all critical findings across all inspections
    all_critical: list[AnomalyItem] = []
    for insp in inspections:
        for a in insp.anomalies:
            if a.severity == Severity.CRITICAL:
                all_critical.append(a)

    # Store inspections in vector DB for future RAG
    for insp in inspections:
        store.add(insp)

    overall = _worst([insp.overall_status for insp in inspections])

    return InspectionReport(
        report_id=str(uuid.uuid4())[:8].upper(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_status=overall,
        inspections=inspections,
        critical_findings=all_critical,
        summary=raw.get("summary", "Inspection complete."),
        recommended_actions=raw.get("recommended_actions", []),
    )
