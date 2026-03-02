# CAT AI Inspector

An AI-powered equipment inspection system for Caterpillar machinery. Field technicians upload photos and voice notes to receive instant, structured anomaly reports — powered by Groq's vision, speech, and language models.

---

## Features

- **Visual Inspection** — Classifies equipment components and detects anomalies (critical / moderate / minor / normal) from photos
- **Voice Notes** — Record verbal observations; Whisper transcribes them and integrates them into the inspection
- **Knowledge Base Search** — Semantic search over CAT training-video transcripts with timestamp-linked results
- **Report Generation** — Aggregate multiple inspections into a prioritized CAT Inspect-style report
- **Historical Tickets** — Search past maintenance tickets by keyword or component type
- **Text-to-Speech** — Listen to inspection summaries via PlayAI TTS
- **Voice Agent** — (Optional) ElevenLabs conversational interface for hands-free operation
- **Multilingual** — Full English and Spanish support across UI and backend prompts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Web UI (Tailwind CSS SPA)                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼───────────────────────────────────┐
│  FastAPI Backend (Python 3.11)                              │
│                                                             │
│  POST /api/inspect   → Vision Pipeline (2-stage)           │
│  POST /api/report    → Report Assembler (LLM synthesis)    │
│  POST /api/kb/query  → Knowledge Base (ChromaDB)           │
│  POST /api/tts       → Text-to-Speech (PlayAI)             │
│  POST /api/tickets/search → Ticket Memory                  │
└────────────┬───────────────────────┬────────────────────────┘
             │                       │
┌────────────▼──────────┐  ┌────────▼───────────────────────┐
│  Groq API             │  │  ChromaDB (in-memory)           │
│  · Llama 4 Scout      │  │  · criteria collection          │
│    (vision + inspect) │  │  · findings collection          │
│  · Llama 3.3 70B      │  └────────────────────────────────┘
│    (report gen)       │
│  · Whisper v3 Turbo   │
│    (speech-to-text)   │
│  · PlayAI TTS         │
└───────────────────────┘
```

### Project Structure

```
caterpillar/
├── app/                        # Backend application
│   ├── main.py                 # FastAPI routes & startup
│   ├── config.py               # Pydantic settings (env vars)
│   ├── schemas.py              # Data models (Severity, AnomalyItem, …)
│   ├── vision.py               # 2-stage vision inspection pipeline
│   ├── voice.py                # STT (Whisper) + TTS (PlayAI)
│   ├── knowledge_base.py       # ChromaDB wrapper
│   ├── transcript_parser.py    # Parse CAT training transcripts
│   ├── report.py               # Inspection report assembler
│   ├── prompts.py              # Component-specific LLM prompts
│   ├── i18n.py                 # EN/ES translations
│   ├── ticket_memory.py        # Historical ticket search
│   ├── vector_store.py         # RAG vector store for inspections
│   ├── voice_agent.py          # ElevenLabs voice agent config
│   └── clip_router.py          # Optional CLIP visual routing
├── static/
│   └── index.html              # Single-page web UI
├── data/
│   ├── transcripts/            # CAT training video transcripts
│   ├── tickets/                # Historical maintenance tickets
│   └── samples/
│       ├── pass/               # Reference images — acceptable conditions
│       └── fail/               # Reference images — equipment issues
├── videos/                     # Training videos (local playback)
├── docs/                       # Extended documentation
│   ├── DOCKER.md
│   ├── VOICE_AGENT_GUIDE.md
│   └── VOICE_AGENT_SETUP.md
├── .env.example                # Environment variable template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── render.yaml                 # Render.com deployment config
├── requirements.txt
├── runtime.txt                 # Python 3.11.9
└── run.sh                      # Local development helper
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/) (required)
- (Optional) ElevenLabs API key + Agent ID for the voice agent

### Local Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd caterpillar

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add at minimum: GROQ_API_KEY=<your-key>

# 5. Start the development server
./run.sh
# or directly: uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Configuration

Copy `.env.example` to `.env` and set the values below.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | — | Groq API key — powers all AI inference |
| `ELEVENLABS_API_KEY` | No | — | ElevenLabs key for voice agent |
| `ELEVENLABS_AGENT_ID` | No | — | ElevenLabs agent ID |
| `SUPERMEMORY_API` | No | — | SuperMemory API key for ticket storage |
| `VISION_MODEL` | No | `meta-llama/llama-4-scout-17b-16e-instruct` | Groq vision model |
| `TEXT_MODEL` | No | `llama-3.3-70b-versatile` | Groq text model for report generation |
| `STT_MODEL` | No | `whisper-large-v3-turbo` | Speech-to-text model |
| `TTS_MODEL` | No | `playai-tts` | Text-to-speech model |
| `TTS_VOICE` | No | `Fritz-PlayAI` | TTS voice ID |

> **Security**: Never commit `.env` to version control. The `.gitignore` excludes it by default.

---

## API Reference

### `POST /api/inspect`

Analyze a single equipment image.

**Form fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | Yes | JPG or PNG photo (max 10 MB) |
| `audio` | file | No | Voice note (WebM / WAV) |
| `routing` | string | No | `vision_llm` (default) or `clip` |
| `language` | string | No | `en` (default) or `es` |

**Example response**

```json
{
  "component_type": "hydraulic_system",
  "severity": "moderate",
  "anomalies": [
    {
      "location": "return hose near boom cylinder",
      "description": "Minor surface cracking on hose outer sleeve",
      "severity": "moderate",
      "action_required": "Schedule hose replacement within 48 hours",
      "impacts": ["potential fluid leak", "hydraulic pressure loss"]
    }
  ],
  "summary": "Hydraulic hose shows early wear. Monitor closely.",
  "confidence": 0.87
}
```

---

### `POST /api/report`

Aggregate multiple inspections into a prioritized report.

```json
{
  "inspections": [ /* array of ComponentInspection objects */ ],
  "language": "en"
}
```

---

### `POST /api/kb/query`

Search the knowledge base (CAT training transcripts).

```json
{
  "query": "hydraulic hose cracking",
  "video_id": "wheel_loader",
  "n": 5,
  "language": "en"
}
```

---

### `POST /api/tts`

Convert text to speech.
**Form field**: `text` (string)
**Response**: `audio/mpeg` binary

---

### `POST /api/tickets/search`

Search historical maintenance tickets.

```json
{
  "query": "hydraulic leak",
  "component_type": "hydraulic_system",
  "n": 10
}
```

---

### Other endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Public config (ElevenLabs agent ID) |
| `GET` | `/api/language` | Available languages and translations |
| `GET` | `/api/videos/{id}` | Stream training video |
| `GET` | `/api/videos/{id}/watch?t=60` | Watch video starting at timestamp (seconds) |
| `GET` | `/api/kb/criteria/{component}` | Get inspection criteria for a component type |
| `GET` | `/api/tickets/{ticket_id}` | Retrieve a specific ticket |

---

## Docker

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env — at minimum set GROQ_API_KEY

# Build and start
docker compose up --build
```

The app is available at [http://localhost:8000](http://localhost:8000).

See [docs/DOCKER.md](docs/DOCKER.md) for full Docker deployment details.

---

## Deploy to Render

1. Push this repository to GitHub
2. Create a new **Web Service** on [Render](https://render.com) and connect your repository — Render will detect `render.yaml` automatically
3. Set environment variables in the Render dashboard (never via `.env` in the repo):
   - `GROQ_API_KEY` (required)
   - `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` (optional)
4. Click **Deploy**

---

## Equipment Components

| Component | Description |
|---|---|
| `steps_handrails` | Access ladders and handrails |
| `cooling_system` | Radiator, hoses, coolant reservoir |
| `tires_rims` | Tires, rim condition, lug nuts |
| `hydraulic_system` | Cylinders, hoses, fluid levels |
| `structural_frame` | Welds, bolts, frame integrity |
| `undercarriage` | Tracks, rollers, sprockets |
| `engine_compartment` | Oil, belts, filters, battery |
| `cab_operator` | Glass, mirrors, controls, visibility |
| `unknown` | Fallback when component cannot be identified |

---

## Severity Levels

| Level | Meaning |
|---|---|
| **CRITICAL** | Equipment must not operate |
| **MODERATE** | Schedule maintenance within 24–48 hours |
| **MINOR** | Monitor at next service interval |
| **NORMAL** | Acceptable condition — no action required |

---

## Voice Agent (Optional)

An ElevenLabs conversational agent enables a hands-free interface for field use. See [docs/VOICE_AGENT_GUIDE.md](docs/VOICE_AGENT_GUIDE.md) for setup instructions.

---

## Performance

| Operation | Typical latency |
|---|---|
| Image analysis | 2–4 s |
| Voice transcription | 1–2 s |
| Report generation | 3–5 s |
| Knowledge base search | < 500 ms |

---

## Security

- Store API keys as environment variables only — never hard-code or commit them
- `.gitignore` excludes `.env` by default — verify before every commit
- If secrets were previously committed, rotate all affected API keys immediately
- For production, serve large files (videos) from a CDN rather than bundling them in the container

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes and verify they work locally
4. Open a pull request with a clear description of the change

---

## License

This project is a proof-of-concept built for demonstration purposes. CAT / Caterpillar branding and training materials are the property of Caterpillar Inc.
