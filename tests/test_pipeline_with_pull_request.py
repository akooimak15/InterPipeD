import asyncio
from types import SimpleNamespace

import pytest

from interpiped.agents.architect import ArchitectAgent
from interpiped.agents.pm import PMAgent
from interpiped.agents.pull_request import PullRequestAgent
from interpiped.agents.tester import TesterAgent
from interpiped.agents.worker import WorkerAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas


class FakeGitHub:
    def create_pull_request(self, **kwargs):
        return SimpleNamespace(
            number=7,
            html_url=f"https://github.com/{kwargs['repository_full_name']}/pull/7",
        )


@pytest.mark.asyncio
async def test_pipeline_includes_pull_request() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-1", bus)
    worker = WorkerAgent("worker-1", bus)
    tester = TesterAgent("tester-1", bus)
    architect = ArchitectAgent("architect-1", bus)
    pr_agent = PullRequestAgent("pr-1", bus, FakeGitHub())  # type: ignore[arg-type]

    await pm.start()
    await worker.start()
    await tester.start()
    await architect.start()
    await pr_agent.start()

    seen = asyncio.Event()
    captured: list[schemas.PullRequestCreated] = []

    async def on_pr_created(e: schemas.PullRequestCreated) -> None:
        if getattr(e, "event_type", None) == "PullRequestCreated":
            captured.append(e)
            seen.set()

    await bus.subscribe("PullRequestCreated", on_pr_created)

    issue = schemas.IssueCreated(
        issue_number=303,
        repository="org/repo",
        title="Create auth",
        description="desc",
        source="user",
    )
    await bus.publish(issue)

    await asyncio.wait_for(seen.wait(), timeout=5.0)

    assert len(captured) >= 1
    assert captured[0].pr_number == 7
    assert captured[0].pr_url.endswith("/pull/7")

    await pm.stop()
    await worker.stop()
    await tester.stop()
    await architect.stop()
    await pr_agent.stop()
    await bus.stop()
