import io
import logging
import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .i18n import TRANSLATIONS, get_text, get_inspection_prompt, get_calibration_prompt, get_report_prompt
from .knowledge_base import kb
from .report import assemble_report
from .schemas import ComponentInspection, InspectionReport
from .ticket_memory import ticket_memory
from .vision import run_inspection_pipeline, RoutingStrategy
from .voice import synthesize_speech, transcribe_audio
from .config import settings

app = FastAPI(title="CAT AI Inspector", version="1.0.0")
logger = logging.getLogger(__name__)

class KBLoadRequest(BaseModel):
    path: str


class KBQueryRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    n: int = 5
    language: str = "en"


class TicketSearchRequest(BaseModel):
    query: str
    component_type: Optional[str] = None
    n: int = 10


VIDEO_SOURCES = {
    "wheel_loader": {
        "video_title": "Cat Wheel Loader Daily Walkaround Inspection",
        "video_file": "Cat® Wheel Loader  Daily Walkaround Inspection - Cat® Products (240p, h264).mp4",
        "transcript_path": "wheel_loader_inspection_transcript.txt",
        "transcript_id": "wheel_loader_transcript",
    },
    "excavator": {
        "video_title": "Cat Excavator Daily Walkaround Inspection",
        "video_file": "Cat® Excavator Daily Walkaround Inspection - Cat® Products (240p, h264).mp4",
        "transcript_path": "excator_inspection_transcript.txt",
        "transcript_id": "excavator_transcript",
    },
}

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def get_config():
    """Return public configuration for frontend (e.g., ElevenLabs agent ID)."""
    return {
        "elevenlabs_agent_id": settings.elevenlabs_agent_id or None,
    }


@app.get("/api/language")
async def get_language_options():
    """Return available languages and translations."""
    return {
        "languages": list(TRANSLATIONS.keys()),
        "translations": TRANSLATIONS,
    }


@app.on_event("startup")
async def startup():
    sources: list[dict[str, str]] = []
    for video_id, config in VIDEO_SOURCES.items():
        transcript_path = config["transcript_path"]
        if not os.path.exists(transcript_path):
            logger.warning("Transcript knowledge file not found at startup: %s", transcript_path)
            continue

        sources.append({
            "path": transcript_path,
            "transcript_id": config["transcript_id"],
            "video_id": video_id,
            "video_title": config["video_title"],
            "video_file": config["video_file"],
        })

    if sources:
        kb.load_transcripts(sources)

    tickets_loaded = ticket_memory.load_from_file("supermemory.txt")
    logger.info("Loaded %s ticket-memory entries", tickets_loaded)


@app.post("/api/inspect", response_model=ComponentInspection)
async def inspect_image(
    image: UploadFile = File(...),
    audio: Optional[UploadFile] = File(None),
    routing: RoutingStrategy = Form(RoutingStrategy.VISION_LLM),
    language: str = Form("en"),
):
    """
    Analyze a single equipment image.
    Optionally accepts a voice narration audio file from the inspector.

    Two-stage pipeline:
      1. Llama 4 Scout classifies which component is in the image
      2. Subsection-specific prompt drives detailed anomaly detection
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    voice_text: Optional[str] = None
    if audio is not None:
        audio_bytes = await audio.read()
        if audio_bytes:
            try:
                # Pass language hint to Whisper for better accuracy
                voice_text = await transcribe_audio(audio_bytes, audio.filename or "audio.webm", language=language)
            except Exception as e:
                # Voice transcription failure is non-fatal
                voice_text = None

    if language not in TRANSLATIONS:
        language = "en"

    try:
        result = await run_inspection_pipeline(image_bytes, voice_text, routing, language=language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection pipeline failed: {str(e)}")

    return result


class ReportRequest(BaseModel):
    inspections: list[ComponentInspection]
    language: str = "en"


@app.post("/api/report", response_model=InspectionReport)
async def generate_report(request: ReportRequest):
    """
    Aggregate multiple component inspections into a full CAT Inspect-style report.
    Uses Llama 4 Scout to synthesize findings and prioritize actions.
    """
    if not request.inspections:
        raise HTTPException(status_code=400, detail="No inspections provided")

    language = request.language

    if language not in TRANSLATIONS:
        language = "en"

    try:
        report = await assemble_report(request.inspections, language=language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    return report


@app.post("/api/tts")
async def text_to_speech(text: str = Form(...)):
    """Convert text to speech using Orpheus/PlayAI via Groq."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        audio_bytes = await synthesize_speech(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/api/kb/load")
async def load_kb(request: KBLoadRequest):
    file_name = os.path.basename(request.path)
    source_payload: list[dict[str, str]] = []

    for video_id, config in VIDEO_SOURCES.items():
        if config["transcript_path"] == file_name or request.path == config["transcript_path"]:
            source_payload.append({
                "path": request.path,
                "transcript_id": config["transcript_id"],
                "video_id": video_id,
                "video_title": config["video_title"],
                "video_file": config["video_file"],
            })
            break

    if source_payload:
        chunks_loaded = kb.load_transcripts(source_payload)
    else:
        chunks_loaded = kb.load_transcript(request.path)

    return {
        "chunks_loaded": chunks_loaded,
        "component_coverage": kb.get_component_coverage(),
    }


@app.get("/api/kb/criteria/{component_type}")
async def get_kb_criteria(component_type: str):
    return {
        "component_type": component_type,
        "criteria": kb.get_inspection_criteria(component_type),
    }


@app.post("/api/kb/query")
async def query_kb(request: KBQueryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    n = max(1, min(int(request.n or 5), 10))
    matches = kb.search_transcript(query=query, n=n, video_id=request.video_id)
    hydrated = []

    for item in matches:
        video_id = str(item.get("video_id") or "")
        start_seconds = float(item.get("timestamp_start") or 0.0)
        resume_url = f"/api/videos/{video_id}/watch?t={int(start_seconds)}" if video_id else ""
        hydrated.append({
            **item,
            "resume_url": resume_url,
        })

    return {
        "query": query,
        "matches": hydrated,
    }


@app.post("/api/tickets/search")
async def search_tickets(request: TicketSearchRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    n = max(1, min(int(request.n or 10), 20))
    tickets = ticket_memory.search(
        query=query,
        component_type=request.component_type,
        limit=n,
    )

    return {
        "query": query,
        "component_type": request.component_type,
        "matches": tickets,
    }


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    ticket = ticket_memory.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    config = VIDEO_SOURCES.get(video_id)
    if not config:
        raise HTTPException(status_code=404, detail="Video not found")

    video_file = config["video_file"]
    if not os.path.exists(video_file):
        raise HTTPException(status_code=404, detail="Video file missing")

    return FileResponse(video_file, media_type="video/mp4")


@app.get("/api/videos/{video_id}/watch", response_class=HTMLResponse)
async def watch_video(video_id: str, t: int = 0):
    config = VIDEO_SOURCES.get(video_id)
    if not config:
        raise HTTPException(status_code=404, detail="Video not found")

    video_file = config["video_file"]
    if not os.path.exists(video_file):
        raise HTTPException(status_code=404, detail="Video file missing")

    start_at = max(0, int(t))
    title = config["video_title"]
    video_src = f"/api/videos/{video_id}"

    html = f"""
<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>{title}</title>
    <style>
      body {{ margin: 0; background: #000; color: #eee; font-family: Inter, system-ui, sans-serif; }}
      .wrap {{ max-width: 960px; margin: 0 auto; padding: 16px; }}
      h1 {{ font-size: 16px; font-weight: 600; margin: 0 0 12px; }}
      .meta {{ color: #aaa; font-size: 12px; margin-bottom: 10px; }}
      video {{ width: 100%; height: auto; border-radius: 8px; background: #111; }}
      a {{ color: #ffcd11; text-decoration: none; }}
    </style>
  </head>
  <body>
    <div class=\"wrap\">
      <h1>{title}</h1>
      <div class=\"meta\">Starting at {start_at}s · <a href=\"/\">Back to app</a></div>
      <video id=\"player\" controls autoplay preload=\"metadata\" src=\"{video_src}\"></video>
    </div>
    <script>
      const startAt = {start_at};
      const player = document.getElementById('player');
      player.addEventListener('loadedmetadata', () => {{
        player.currentTime = startAt;
      }});
      player.addEventListener('canplay', () => {{
        if (player.currentTime < startAt) player.currentTime = startAt;
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)
