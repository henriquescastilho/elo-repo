from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)

    openai_api_key: str | None = Field(default=None)
    openai_api_base: str | None = Field(default="https://api.openai.com/v1")
    llm_model_name: str = Field(default="gpt-4o-mini")
    tts_model_name: str = Field(default="gpt-4o-mini-tts")
    tts_voice: str = Field(default="alloy")
    stt_model_name: str = Field(default="whisper-1")
    vision_model_name: str = Field(default="gpt-4o")
    embedding_model_name: str = Field(default="text-embedding-3-small")

    llm_provider: str = Field(default="openai")
    tts_provider: str = Field(default="openai")
    stt_provider: str = Field(default="openai")
    vision_provider: str = Field(default="openai")

    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None

    whatsapp_provider: str = Field(default="waha")

    waha_base_url: str | None = None
    waha_api_token: str | None = None

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_number: str | None = None

    redis_url: str | None = None

    api_camara_base_url: str | None = None
    api_senado_base_url: str | None = None
    legal_data_source_mode: str = Field(default="mock")

    log_level: str = Field(default="INFO")
    send_audio_default: bool = Field(default=False)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
