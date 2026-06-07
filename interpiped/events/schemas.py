from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Schema version for all event schemas in this module
schema_version = "1.0"


class BaseEvent(BaseModel):
    """Base event schema with versioning."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    target: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    schema_version: Literal["1.0"] = Field(default=schema_version)

    model_config = {"extra": "forbid"}


class TaskCreated(BaseEvent):
    event_type: Literal["TaskCreated"] = "TaskCreated"
    # payload may contain task_id, description, priority, etc.


class TaskCompleted(BaseEvent):
    event_type: Literal["TaskCompleted"] = "TaskCompleted"
    # payload may contain original_event_id, result, artifacts


class TestPassed(BaseEvent):
    event_type: Literal["TestPassed"] = "TestPassed"
    # payload may contain test_suite, duration, details


class TestFailed(BaseEvent):
    event_type: Literal["TestFailed"] = "TestFailed"
    # payload may contain test_suite, failures, logs


class ArchitectureApproved(BaseEvent):
    event_type: Literal["ArchitectureApproved"] = "ArchitectureApproved"
    # payload may contain pr_number, approver


class ArchitectureRejected(BaseEvent):
    event_type: Literal["ArchitectureRejected"] = "ArchitectureRejected"
    # payload may contain reasons, suggestions


def get_event_schemas() -> Dict[str, Dict[str, Any]]:
    """Return JSON Schemas for all event models in this module.

    The returned dict maps model class name -> JSON Schema dict.
    """
    models = [
        BaseEvent,
        TaskCreated,
        TaskCompleted,
        TestPassed,
        TestFailed,
        ArchitectureApproved,
        ArchitectureRejected,
    ]
    return {m.__name__: m.model_json_schema() for m in models}


__all__ = [
    "schema_version",
    "BaseEvent",
    "TaskCreated",
    "TaskCompleted",
    "TestPassed",
    "TestFailed",
    "ArchitectureApproved",
    "ArchitectureRejected",
    "get_event_schemas",
]
