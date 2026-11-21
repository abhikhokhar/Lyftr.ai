from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: Optional[str] = None

    @field_validator("session_id", "message", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        return value.strip()


class ChatMetadata(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str] = None
    fallback_attempts: int = 0
    cache_hit: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class MessageResponse(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageResponse]
