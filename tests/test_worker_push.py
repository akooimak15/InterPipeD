import asyncio

import pytest

from interpiped.agents.worker import WorkerAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas
from interpiped.services.git_service import GitService, GitServiceError


@pytest.mark.asyncio
async def test_worker_pushes_branch_before_task_completed(monkeypatch) -> None:
    bus = InMemoryEventBus()
    await bus.start()

    worker = WorkerAgent("worker-push", bus)
    await worker.start()

    push_calls: list[str] = []

    def fake_push(self, remote: str = "origin") -> None:
        push_calls.append(remote)

    monkeypatch.setattr(GitService, "push_branch", fake_push)

    completed = asyncio.Event()

    async def on_completed(e: schemas.TaskCompleted) -> None:
        if getattr(e, "event_type", None) == "TaskCompleted":
            completed.set()

    await bus.subscribe("TaskCompleted", on_completed)

    await bus.publish(
        schemas.TaskCreated(
            task_id="t-push",
            issue_number=1,
            repository="repo",
            branch_name="task/t-push",
            title="Push test",
            description="desc",
            source="pm",
        )
    )

    await asyncio.wait_for(completed.wait(), timeout=2.0)
    assert push_calls == ["origin"]

    await worker.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_worker_publishes_taskfailed_when_push_fails(monkeypatch) -> None:
    bus = InMemoryEventBus()
    await bus.start()

    worker = WorkerAgent("worker-push", bus)
    await worker.start()

    def failing_push(self, remote: str = "origin") -> None:
        raise GitServiceError("push_branch failed: no remote")

    monkeypatch.setattr(GitService, "push_branch", failing_push)

    failed = asyncio.Event()
    completed = asyncio.Event()

    async def on_failed(e: schemas.TaskFailed) -> None:
        if getattr(e, "event_type", None) == "TaskFailed":
            failed.set()

    async def on_completed(e: schemas.TaskCompleted) -> None:
        if getattr(e, "event_type", None) == "TaskCompleted":
            completed.set()

    await bus.subscribe("TaskFailed", on_failed)
    await bus.subscribe("TaskCompleted", on_completed)

    await bus.publish(
        schemas.TaskCreated(
            task_id="t-push-fail",
            issue_number=1,
            repository="repo",
            branch_name="task/t-push-fail",
            title="Push fail",
            description="desc",
            source="pm",
        )
    )

    await asyncio.wait_for(failed.wait(), timeout=2.0)
    assert not completed.is_set()

    await worker.stop()
    await bus.stop()
