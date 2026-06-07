import asyncio

import pytest

from httpx import AsyncClient, ASGITransport

from interpiped.api import main as api_main
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_issues_opened_to_issuecreated_and_pmaget() -> None:
    app = api_main.app
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ensure bus and PM agent are running
        await api_main.bus.start()
        await api_main.pm.start()

        seen = asyncio.Event()

        async def on_task(e: schemas.TaskCreated) -> None:
            seen.set()

        await api_main.bus.subscribe("TaskCreated", on_task)

        payload = {
            "action": "opened",
            "issue": {"number": 314, "title": "Add search", "body": "Please add search"},
            "repository": {"full_name": "owner/repo"},
        }

        r = await ac.post("/webhook/github", headers={"X-GitHub-Event": "issues"}, json=payload)
        assert r.status_code == 200

        await asyncio.wait_for(seen.wait(), timeout=1.0)

        await api_main.pm.stop()
        await api_main.bus.stop()
