import re
from typing import Any


_COMPONENT_KEYWORDS: list[tuple[list[str], str]] = [
    (["cutting edge", "bucket", "corner", "teeth", "adapter"], "structural_frame"),
    (["linkage", "pin", "grease", "boom", "seized"], "structural_frame"),
    (["tire", "tyre", "wheel bolt", "final drive", "inflation", "rebar"], "tires_rims"),
    (["hose", "steering cylinder", "hitch", "wiring harness"], "hydraulic_system"),
    (["transmission", "fuel tank", "engine oil", "exhaust", "intake", "coolant", "cooler"], "engine_compartment"),
    (["hydraulic tank", "hydraulic oil"], "hydraulic_system"),
    (["step", "handrail", "handguard", "ladder"], "steps_handrails"),
    (["cab", "gauge", "light", "control", "seat belt", "filter"], "cab_operator"),
]

_FINDING_SIGNALS = [
    "found",
    "seized",
    "broken",
    "leaking",
    "leak",
    "low",
    "bad",
    "damaged",
    "don't run",
    "shut down",
    "replace",
    "skip",
    "cracked",
]

_VERDICT_PHRASES: list[tuple[str, str]] = [
    ("don't run this machine", "do not operate"),
    ("not bad enough to shut down", "monitor"),
    ("should be replaced very soon", "replace soon"),
    ("make a note of it", "schedule maintenance"),
    ("add some oil", "top up required"),
]

_VERDICT_TO_SEVERITY = {
    "do not operate": "critical",
    "top up required": "critical",
    "replace soon": "moderate",
    "schedule maintenance": "moderate",
    "monitor": "minor",
}

_TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)$")
_ANNOTATION_RE = re.compile(r"\[[^\]]+\]")


def _parse_timestamp(value: str) -> float | None:
    raw = value.strip()
    match = _TIMESTAMP_RE.match(raw)
    if not match:
        return None

    hours_raw, minutes_raw, seconds_raw = match.groups()
    if hours_raw is None:
        minutes = int(minutes_raw)
        seconds = int(seconds_raw)
        return float(minutes * 60 + seconds)

    hours = int(hours_raw)
    minutes = int(minutes_raw)
    seconds = int(seconds_raw)
    return float(hours * 3600 + minutes * 60 + seconds)


def _clean_caption_line(line: str) -> str:
    cleaned = _ANNOTATION_RE.sub(" ", line)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_raw(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    segments: list[dict[str, Any]] = []

    current_start: float | None = None
    current_text_lines: list[str] = []

    def flush(end_seconds: float | None) -> None:
        nonlocal current_start, current_text_lines
        if current_start is None:
            return

        merged_text = " ".join(item for item in current_text_lines if item).strip()
        if merged_text:
            segment_end = end_seconds if end_seconds is not None else current_start + 5.0
            if segment_end < current_start:
                segment_end = current_start
            segments.append({
                "start_seconds": float(current_start),
                "end_seconds": float(segment_end),
                "text": merged_text,
            })

        current_start = None
        current_text_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        ts = _parse_timestamp(line)
        if ts is not None:
            flush(ts)
            current_start = ts
            current_text_lines = []
            continue

        if current_start is None:
            continue

        cleaned = _clean_caption_line(line)
        if cleaned:
            current_text_lines.append(cleaned)

    flush(None)
    return segments


def _component_for_text(value: str) -> str:
    text = value.lower()
    for keywords, component_type in _COMPONENT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return component_type
    return "unknown"


def classify_chunk_type(chunk_text: str) -> str:
    text = chunk_text.lower()
    if any(signal in text for signal in _FINDING_SIGNALS):
        return "finding"
    return "criteria"


def extract_nick_verdict(chunk_text: str) -> str | None:
    text = chunk_text.lower()
    for phrase, verdict in _VERDICT_PHRASES:
        if phrase in text:
            return verdict
    return None


def _infer_severity(nick_verdict: str | None) -> str | None:
    if nick_verdict is None:
        return None
    return _VERDICT_TO_SEVERITY.get(nick_verdict)


def extract_chunks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not segments:
        return []

    grouped: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None

    for segment in segments:
        segment_text = str(segment.get("text", "")).strip()
        if not segment_text:
            continue

        component_type = _component_for_text(segment_text)
        start_seconds = float(segment.get("start_seconds", 0.0))
        end_seconds = float(segment.get("end_seconds", start_seconds))

        if (
            current_group is not None
            and current_group["component_type"] == component_type
        ):
            current_group["text_parts"].append(segment_text)
            current_group["timestamp_end"] = end_seconds
            continue

        if current_group is not None:
            grouped.append(current_group)

        current_group = {
            "component_type": component_type,
            "timestamp_start": start_seconds,
            "timestamp_end": end_seconds,
            "text_parts": [segment_text],
        }

    if current_group is not None:
        grouped.append(current_group)

    chunks: list[dict[str, Any]] = []
    for group in grouped:
        chunk_text = " ".join(group["text_parts"]).strip()
        if not chunk_text:
            continue

        chunk_type = classify_chunk_type(chunk_text)
        nick_verdict = extract_nick_verdict(chunk_text) if chunk_type == "finding" else None
        severity = _infer_severity(nick_verdict) if chunk_type == "finding" else None

        chunks.append({
            "chunk_type": chunk_type,
            "component_type": group["component_type"],
            "text": chunk_text,
            "timestamp_start": float(group["timestamp_start"]),
            "timestamp_end": float(group["timestamp_end"]),
            "nick_verdict": nick_verdict,
            "severity": severity,
        })

    return chunks
