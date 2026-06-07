import os
import tempfile

import asyncio

import pytest

from git import Repo

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.agents.worker import WorkerAgent
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_worker_creates_commit_and_emits_taskcompleted(tmp_path) -> None:
    # setup bare repo to clone from
    src = tmp_path / "src"
    src.mkdir()
    r = Repo.init(src)
    (src / "initial.txt").write_text("init")
    r.git.add(A=True)
    r.index.commit("initial")

    # start bus and worker
    bus = InMemoryEventBus()
    await bus.start()
    worker = WorkerAgent("worker-git", bus)
    await worker.start()

    seen = asyncio.Event()
    result = {}

    async def on_completed(e: schemas.TaskCompleted) -> None:
        result["sha"] = e.commit_sha
        result["files"] = e.files_modified
        seen.set()

    await bus.subscribe("TaskCompleted", on_completed)

    # publish TaskCreated pointing to local repo path
    task = schemas.TaskCreated(
        task_id="auth-api",
        issue_number=1,
        repository=str(src),
        branch_name="task/auth-api",
        title="Auth",
        description="Create auth API",
        source="pm-test",
    )

    await bus.publish(task)
    await asyncio.wait_for(seen.wait(), timeout=3.0)

    assert "sha" in result and result["sha"]
    assert "files" in result and len(result["files"]) == 1

    await worker.stop()
    await bus.stop()
