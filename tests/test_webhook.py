import asyncio

import pytest

from httpx import AsyncClient, ASGITransport

from interpiped.api import main as api_main
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_issues_opened_creates_issuecreated_and_taskcreated() -> None:
    app = api_main.app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ensure app bus & agents running for deterministic handling
        await api_main.bus.start()
        await api_main.pm.start()
        await api_main.worker.start()

        # subscribe to TaskCreated events
        seen = asyncio.Event()

        async def on_task(e: schemas.TaskCreated) -> None:
            seen.set()

        await api_main.bus.subscribe("TaskCreated", on_task)

        payload = {
            "action": "opened",
            "issue": {"number": 7, "title": "Create auth", "body": "desc"},
            "repository": {"full_name": "owner/repo"},
        }

        r = await ac.post("/webhook/github", headers={"X-GitHub-Event": "issues"}, json=payload)
        assert r.status_code == 200

        await asyncio.wait_for(seen.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_pull_request_opened_ignored() -> None:
    app = api_main.app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "action": "opened",
            "pull_request": {"number": 1, "title": "PR", "head": {"sha": "abc"}},
            "repository": {"full_name": "owner/repo"},
        }

        r = await ac.post("/webhook/github", headers={"X-GitHub-Event": "pull_request"}, json=payload)
        assert r.status_code == 200
        assert r.json().get("status") == "ignored"


@pytest.mark.asyncio
async def test_issue_comment_created_ignored() -> None:
    app = api_main.app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "action": "created",
            "comment": {"body": "Nice"},
            "issue": {"number": 2},
            "repository": {"full_name": "owner/repo"},
        }

        r = await ac.post("/webhook/github", headers={"X-GitHub-Event": "issue_comment"}, json=payload)
        assert r.status_code == 200
        assert r.json().get("status") == "ignored"
