from groq import AsyncGroq
from .config import settings


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm", language: str = None) -> str:
    """Transcribe inspector voice narration using Whisper.
    
    Args:
        audio_bytes: Raw audio data
        filename: Original filename (for MIME type detection)
        language: ISO-639-1 language code (e.g., 'es' for Spanish, 'en' for English)
                 If None, Whisper auto-detects
    """
    client = AsyncGroq(api_key=settings.groq_api_key)

    # Groq STT expects a file-like tuple: (filename, bytes, mime_type)
    mime = "audio/webm"
    if filename.endswith(".wav"):
        mime = "audio/wav"
    elif filename.endswith(".mp3"):
        mime = "audio/mpeg"
    elif filename.endswith(".m4a"):
        mime = "audio/mp4"

    kwargs = {
        "model": settings.stt_model,
        "file": (filename, audio_bytes, mime),
    }
    
    # Add language hint if provided
    if language:
        kwargs["language"] = language

    response = await client.audio.transcriptions.create(**kwargs)
    return response.text.strip()


async def synthesize_speech(text: str) -> bytes:
    """Convert critical findings text to speech using Orpheus/PlayAI."""
    client = AsyncGroq(api_key=settings.groq_api_key)

    response = await client.audio.speech.create(
        model=settings.tts_model,
        voice=settings.tts_voice,
        input=text,
        response_format="mp3",
    )
    # response.content holds the raw audio bytes
    return response.content
