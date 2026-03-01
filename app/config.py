from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None

    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    text_model: str = "llama-3.3-70b-versatile"
    stt_model: str = "whisper-large-v3-turbo"
    tts_model: str = "playai-tts"
    tts_voice: str = "Fritz-PlayAI"

    class Config:
        env_file = ".env"


settings = Settings()
