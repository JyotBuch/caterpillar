import base64
import json
from enum import Enum
from groq import AsyncGroq

from .config import settings
from .i18n import get_inspection_prompt, get_calibration_prompt
from .knowledge_base import kb
from .prompts import CLASSIFY_PROMPT, SUBSECTION_PROMPTS, COMPONENT_TYPES
from .schemas import ComponentInspection, AnomalyItem, Severity


class RoutingStrategy(str, Enum):
    # Default: Llama 4 Scout classifies + inspects (one model, full reasoning)
    VISION_LLM = "vision_llm"
    # CLIP: fast visual grounding for routing, LLM still does inspection reasoning
    # Requires reference images in references/<component_type>/ and:
    #   pip install transformers torch
    CLIP = "clip"


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _image_msg(b64: str, mime: str = "image/jpeg") -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def _text_msg(text: str) -> dict:
    return {"type": "text", "text": text}


def _parse_json(raw: str) -> dict:
    """Robustly extract JSON from model output."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _format_similar_findings(findings: list[dict]) -> str:
    lines = []
    for idx, item in enumerate(findings, start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        severity = item.get("severity") or "unknown"
        verdict = item.get("nick_verdict") or "none"
        ts = item.get("timestamp_start")
        ts_text = f"{float(ts):.1f}s" if isinstance(ts, (int, float)) else "unknown"
        lines.append(f"{idx}. [{severity}] [{verdict}] @ {ts_text} — {text}")
    return "\n".join(lines)


async def classify_component(image_bytes: bytes) -> tuple[str, float, str]:
    """Stage 1: identify what component is in the image."""
    client = AsyncGroq(api_key=settings.groq_api_key)
    b64 = _b64(image_bytes)

    response = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[{
            "role": "user",
            "content": [_image_msg(b64), _text_msg(CLASSIFY_PROMPT)],
        }],
        response_format={"type": "json_object"},
        max_tokens=300,
    )

    try:
        data = _parse_json(response.choices[0].message.content)
        component_type = data.get("component_type", "unknown")
        if component_type not in COMPONENT_TYPES:
            component_type = "unknown"
        confidence = float(data.get("confidence", 0.7))
        description = data.get("component_description", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        component_type, confidence, description = "unknown", 0.5, "Could not classify"

    return component_type, confidence, description


async def inspect_component(
    image_bytes: bytes,
    component_type: str,
    voice_context: str | None = None,
    language: str = "en",
) -> dict:
    """Stage 2: inspect with the subsection-specific prompt."""
    client = AsyncGroq(api_key=settings.groq_api_key)
    b64 = _b64(image_bytes)

    subsection_prompt = get_inspection_prompt(component_type, language)
    criteria = kb.get_inspection_criteria(component_type)
    if criteria:
        system_prompt = (
            "CAT EXPERT INSPECTION CRITERIA (from official CAT training):\n"
            f"{criteria}\n\n---\n{subsection_prompt}"
        )
    else:
        system_prompt = subsection_prompt

    # If inspector provided voice notes, make them central to the inspection
    if voice_context:
        user_text = (
            f"PRIORITY: The inspector noted: \"{voice_context}\"\n\n"
            f"You MUST inspect the image to verify/investigate this concern. "
            f"Look carefully for any signs of what the inspector mentioned. "
            f"Include this as an anomaly if found, and rate severity appropriately. "
            f"Do not dismiss it - treat it as a directive to inspect that specific area."
        )
    else:
        user_text = "Perform a detailed inspection of this component."

    response = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [_image_msg(b64), _text_msg(user_text)],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )

    first_result = _parse_json(response.choices[0].message.content)

    anomalies = first_result.get("anomalies") or []
    condition_description = ""
    if anomalies and isinstance(anomalies[0], dict):
        condition_description = str(anomalies[0].get("condition_description", "")).strip()
    if not condition_description:
        condition_description = str(first_result.get("component_description", "")).strip()

    similar_findings = kb.get_similar_findings(component_type, condition_description)
    if not similar_findings:
        return first_result

    findings_text = _format_similar_findings(similar_findings)
    if not findings_text:
        return first_result

    calibrated_user_text = (
        f"{user_text}\n\n"
        "Similar findings from CAT expert inspection:\n"
        f"{findings_text}\n"
        "Use these as severity calibration."
    )

    calibrated_response = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [_image_msg(b64), _text_msg(calibrated_user_text)],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )

    try:
        return _parse_json(calibrated_response.choices[0].message.content)
    except Exception:
        return first_result


def _coerce_severity(val: str) -> Severity:
    mapping = {
        "critical": Severity.CRITICAL,
        "major": Severity.CRITICAL,
        "moderate": Severity.MODERATE,
        "minor": Severity.MINOR,
        "normal": Severity.NORMAL,
        "green": Severity.NORMAL,
        "yellow": Severity.MODERATE,
        "red": Severity.CRITICAL,
    }
    return mapping.get(str(val).lower(), Severity.MINOR)


_SECOND_OPINION_PROMPT = """You are a skeptical senior CAT equipment inspector reviewing a junior inspector's finding.
The junior inspector said this component is NORMAL. Your job is to look harder.

Look specifically for:
- Subtle wear patterns, uneven surfaces, asymmetric damage
- Early-stage corrosion, surface staining, or residue from leaks
- Anything that deviates from factory-new condition
- Small cracks, hairline fractures, or stress marks

If you find ANYTHING that deviates from perfect condition, report it.
Use the same JSON format as the original inspection.
Only return "normal" if you are fully confident after a thorough look."""


async def _second_opinion(
    image_bytes: bytes,
    component_type: str,
    voice_context: str | None,
    first_result: dict,
) -> dict:
    """Re-inspect with a skeptical prompt when first pass returns NORMAL at low confidence."""
    client = AsyncGroq(api_key=settings.groq_api_key)
    b64 = _b64(image_bytes)

    base_prompt = SUBSECTION_PROMPTS.get(component_type, SUBSECTION_PROMPTS["unknown"])
    combined_prompt = f"{_SECOND_OPINION_PROMPT}\n\n---\nOriginal inspection guidelines:\n{base_prompt}"

    user_text = "Re-examine this component carefully. The initial inspection found nothing — look harder."
    if voice_context:
        user_text += f'\n\nInspector voice notes: "{voice_context}"'

    response = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {"role": "system", "content": combined_prompt},
            {"role": "user", "content": [_image_msg(b64), _text_msg(user_text)]},
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )

    try:
        second = _parse_json(response.choices[0].message.content)
        # Only upgrade if second opinion found something
        if second.get("overall_status", "normal") != "normal" or second.get("anomalies"):
            return second
    except Exception:
        pass

    return first_result


async def _classify_with_clip(image_bytes: bytes) -> tuple[str, float, str]:
    """CLIP routing: fast visual grounding, no LLM call for classification."""
    from .clip_router import classify_with_clip
    import asyncio
    # CLIP is sync (torch), run in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, classify_with_clip, image_bytes)


async def run_inspection_pipeline(
    image_bytes: bytes,
    voice_text: str | None = None,
    routing: RoutingStrategy = RoutingStrategy.VISION_LLM,
    language: str = "en",
) -> ComponentInspection:
    """
    Full two-stage pipeline: classify → inspect → return structured result.

    routing=VISION_LLM (default):
        Stage 1: Llama 4 Scout reads the image and classifies the component.
        Best when you don't have labeled reference images.
        Slower (~1-2s) but handles ambiguous or novel components well.

    routing=CLIP:
        Stage 1: CLIP cosine similarity against reference images does grounding.
        Stage 2: LLM still does all reasoning/anomaly detection.
        Faster classification, but requires reference images per component type
        in references/<component_type>/. Falls back to 'unknown' if none found.
    """

    # Stage 1: what component is this?
    if routing == RoutingStrategy.CLIP:
        try:
            component_type, confidence, description = await _classify_with_clip(image_bytes)
            # If CLIP returned unknown due to no reference index, fall back to Vision LLM
            if component_type == "unknown" and "No CLIP reference index" in description:
                component_type, confidence, description = await classify_component(image_bytes)
        except Exception:
            # Fall back to Vision LLM if CLIP fails for any reason
            component_type, confidence, description = await classify_component(image_bytes)
    else:
        component_type, confidence, description = await classify_component(image_bytes)

    # Stage 2: inspect with the right subsection prompt
    raw = await inspect_component(image_bytes, component_type, voice_text, language=language)

    # Stage 2b: second-opinion pass if model returned NORMAL with low confidence.
    # Re-inspects with a skeptical prompt to catch missed subtle findings.
    if raw.get("overall_status") == "normal" and float(raw.get("confidence", 1.0)) < 0.8:
        raw = await _second_opinion(image_bytes, component_type, voice_text, raw)

    # Parse anomalies
    anomalies = []
    for a in raw.get("anomalies", []):
        try:
            anomalies.append(AnomalyItem(
                component_location=a.get("component_location", "unknown"),
                component_type=a.get("component_type", component_type),
                condition_description=a.get("condition_description", ""),
                severity=_coerce_severity(a.get("severity", "minor")),
                safety_impact=a.get("safety_impact", ""),
                operational_impact=a.get("operational_impact", ""),
                recommended_action=a.get("recommended_action", ""),
            ))
        except Exception:
            continue

    overall = _coerce_severity(raw.get("overall_status", "normal"))

    return ComponentInspection(
        component_category=component_type,
        component_description=raw.get("component_description", description),
        overall_status=overall,
        anomalies=anomalies,
        voice_notes=voice_text,
        confidence=confidence,
    )
