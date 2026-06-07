import asyncio

import pytest

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.agents.worker import WorkerAgent
from interpiped.events import schemas
from interpiped.services.git_service import GitService, GitServiceError


@pytest.mark.asyncio
async def test_worker_publishes_taskfailed_on_git_error(monkeypatch) -> None:
    bus = InMemoryEventBus()
    await bus.start()

    worker = WorkerAgent("worker-test", bus)
    await worker.start()

    # force clone to raise
    def fake_clone(repo_url, destination):
        raise GitServiceError("clone failed")

    monkeypatch.setattr(GitService, "clone_repository", staticmethod(fake_clone))

    seen_failed = asyncio.Event()
    seen_completed = asyncio.Event()

    async def on_failed(e: schemas.TaskFailed) -> None:
        seen_failed.set()

    async def on_completed(e: schemas.TaskCompleted) -> None:
        seen_completed.set()

    await bus.subscribe("TaskFailed", on_failed)
    await bus.subscribe("TaskCompleted", on_completed)

    task = schemas.TaskCreated(
        task_id="t-bad",
        issue_number=1,
        repository="/non/existent/repo",
        branch_name="task/t-bad",
        title="Bad",
        description="desc",
        source="pm",
    )

    await bus.publish(task)

    await asyncio.wait_for(seen_failed.wait(), timeout=2.0)

    # ensure TaskCompleted not emitted
    assert not seen_completed.is_set()

    await worker.stop()
    await bus.stop()
