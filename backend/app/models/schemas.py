from typing import Literal, Optional
from pydantic import BaseModel


class NormalizedMessage(BaseModel):
    user_id: str
    type: Literal["text", "audio", "image", "file"] = "text"
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_bytes: Optional[bytes] = None
    mime_type: Optional[str] = None


class OutgoingMessage(BaseModel):
    to: str
    text: str
    audio_url: Optional[str] = None
