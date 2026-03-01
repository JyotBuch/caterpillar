# CAT AI Inspector - Docker Deployment

## Quick Start

### 1. Build the Docker image:
```bash
docker build -t cat-inspector .
```

### 2. Run with environment variables:
```bash
docker run -d \
  --name cat-inspector \
  -p 8000:8000 \
  -e GROQ_API_KEY=your_groq_key \
  -e ELEVENLABS_API_KEY=your_elevenlabs_key \
  -e ELEVENLABS_AGENT_ID=your_agent_id \
  cat-inspector
```

### 3. Or use Docker Compose:
```bash
# Copy .env.example to .env and fill in your keys
cp .env.example .env

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Accessing the Application

Open your browser to: **http://localhost:8000**

## Environment Variables

Required:
- `GROQ_API_KEY` - Your Groq API key for vision/STT models
- `ELEVENLABS_API_KEY` - Your ElevenLabs API key
- `ELEVENLABS_AGENT_ID` - Your ElevenLabs agent ID from dashboard

Optional (defaults provided):
- `VISION_MODEL` - Vision model ID (default: meta-llama/llama-4-scout-17b-16e-instruct)
- `TEXT_MODEL` - Text model ID (default: llama-3.3-70b-versatile)
- `STT_MODEL` - Speech-to-text model (default: whisper-large-v3-turbo)
- `TTS_MODEL` - Text-to-speech model (default: playai-tts)
- `TTS_VOICE` - TTS voice ID (default: Fritz-PlayAI)

## Health Check

```bash
curl http://localhost:8000/api/health
```

## Volumes

The container exposes a `/app/data` directory for persistent storage. Mount it if needed:

```bash
docker run -v ./data:/app/data cat-inspector
```

## Production Deployment

For production, consider:
1. Use a reverse proxy (nginx/Traefik) with HTTPS
2. Set proper resource limits
3. Use secrets management for API keys
4. Enable logging to external systems
5. Set up monitoring and alerts
