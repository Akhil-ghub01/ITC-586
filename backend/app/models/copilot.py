from typing import List, Optional, Literal
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SuggestReplyRequest(BaseModel):
    customer_message: str
    conversation_history: Optional[List[ChatMessage]] = []
    topic_hint: Optional[str] = None  # e.g. "orders", "returns", "account"


class SuggestReplyResponse(BaseModel):
    suggested_reply: str


class SummarizeCaseRequest(BaseModel):
    conversation: List[ChatMessage]


class SummarizeCaseResponse(BaseModel):
    summary: str
    key_points: List[str]
