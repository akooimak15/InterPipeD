from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
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
    schema_version: Literal["1.0"] = "1.0"

    model_config = {"extra": "forbid"}


class TaskCreated(BaseEvent):
    event_type: Literal["TaskCreated"] = "TaskCreated"
    task_id: str
    issue_number: int
    repository: str
    branch_name: str
    title: str
    description: str
    priority: str = Field(default="normal")


class TaskCompleted(BaseEvent):
    event_type: Literal["TaskCompleted"] = "TaskCompleted"
    task_id: str
    commit_sha: str
    files_modified: list[str]


class TaskFailed(BaseEvent):
    event_type: Literal["TaskFailed"] = "TaskFailed"
    task_id: str
    reason: str
    error_type: str


class RetryRequested(BaseEvent):
    event_type: Literal["RetryRequested"] = "RetryRequested"
    task_id: str
    retry_count: int
    reason: str
    # optional task context so workers can re-run the task
    repository: Optional[str] = None
    branch_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class PermanentFailure(BaseEvent):
    event_type: Literal["PermanentFailure"] = "PermanentFailure"
    task_id: str
    reason: str


class TestPassed(BaseEvent):
    event_type: Literal["TestPassed"] = "TestPassed"
    task_id: str
    test_count: int
    duration_ms: int


class TestFailed(BaseEvent):
    event_type: Literal["TestFailed"] = "TestFailed"
    task_id: str
    failed_tests: list[str]
    duration_ms: int


class ArchitectureApproved(BaseEvent):
    event_type: Literal["ArchitectureApproved"] = "ArchitectureApproved"
    task_id: str
    reviewer: str


class ArchitectureRejected(BaseEvent):
    event_type: Literal["ArchitectureRejected"] = "ArchitectureRejected"
    task_id: str
    reviewer: str
    reason: str


class PullRequestCreated(BaseEvent):
    event_type: Literal["PullRequestCreated"] = "PullRequestCreated"
    task_id: str
    repository: str
    pr_number: int
    pr_url: str
    head: str
    base: str


class PullRequestFailed(BaseEvent):
    event_type: Literal["PullRequestFailed"] = "PullRequestFailed"
    task_id: str
    reason: str


class IssueCreated(BaseEvent):
    event_type: Literal["IssueCreated"] = "IssueCreated"
    issue_number: int
    repository: str
    title: str
    description: str


EVENT_MODELS: list[type[BaseModel]] = [
    BaseEvent,
    IssueCreated,
    TaskCreated,
    TaskCompleted,
    TaskFailed,
    RetryRequested,
    PermanentFailure,
    TestPassed,
    TestFailed,
    ArchitectureApproved,
    ArchitectureRejected,
    PullRequestCreated,
    PullRequestFailed,
]


def get_event_schemas() -> Dict[str, Dict[str, Any]]:
    """Return JSON Schemas for all event models in this module.

    The returned dict maps model class name -> JSON Schema dict.
    """
    return {m.__name__: m.model_json_schema() for m in EVENT_MODELS}


__all__ = [
    "schema_version",
    "BaseEvent",
    "IssueCreated",
    "TaskCreated",
    "TaskCompleted",
    "TaskFailed",
    "RetryRequested",
    "PermanentFailure",
    "TestPassed",
    "TestFailed",
    "ArchitectureApproved",
    "ArchitectureRejected",
    "PullRequestCreated",
    "PullRequestFailed",
    "get_event_schemas",
]
