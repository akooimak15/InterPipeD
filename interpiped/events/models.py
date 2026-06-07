from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    target: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
