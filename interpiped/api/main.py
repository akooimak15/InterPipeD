from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas
from interpiped.agents.worker import WorkerAgent
from interpiped.agents.pm import PMAgent
from interpiped.agents.tester import TesterAgent
from interpiped.agents.architect import ArchitectAgent
from interpiped.agents.pull_request import PullRequestAgent
from interpiped.github.github_app import GitHubService
from interpiped.github.webhook import process_github_event

log = logging.getLogger(__name__)

app = FastAPI(title="InterPipeD API")

# Instantiate an in-memory bus and sample agents for the demo scaffold
bus = InMemoryEventBus()
worker = WorkerAgent("worker-1", bus)
pm = PMAgent("pm-1", bus)
tester = TesterAgent("tester-1", bus)
architect = ArchitectAgent("architect-1", bus)
pull_request_agent: Optional[PullRequestAgent] = None

_github_app_id = os.environ.get("GITHUB_APP_ID")
_github_private_key = os.environ.get("GITHUB_PRIVATE_KEY")
_github_installation_id = os.environ.get("GITHUB_INSTALLATION_ID")
if _github_app_id and _github_private_key and _github_installation_id:
    github_service = GitHubService(
        app_id=int(_github_app_id),
        private_key=_github_private_key,
        installation_id=int(_github_installation_id),
    )
    pull_request_agent = PullRequestAgent("pr-1", bus, github_service)
else:
    log.info("PullRequestAgent disabled: GITHUB_APP_ID, GITHUB_PRIVATE_KEY, and GITHUB_INSTALLATION_ID required")


@app.on_event("startup")
async def startup() -> None:
    await bus.start()
    try:
        await worker.start()
    except Exception:
        log.exception("worker start failed")
    try:
        await pm.start()
    except Exception:
        log.exception("pm start failed")
    try:
        await tester.start()
    except Exception:
        log.exception("tester start failed")
    try:
        await architect.start()
    except Exception:
        log.exception("architect start failed")
    if pull_request_agent is not None:
        try:
            await pull_request_agent.start()
        except Exception:
            log.exception("pull request agent start failed")


@app.on_event("shutdown")
async def shutdown() -> None:
    try:
        await worker.stop()
    except Exception:
        log.exception("worker stop failed")
    try:
        await pm.stop()
    except Exception:
        log.exception("pm stop failed")
    try:
        await tester.stop()
    except Exception:
        log.exception("tester stop failed")
    try:
        await architect.stop()
    except Exception:
        log.exception("architect stop failed")
    if pull_request_agent is not None:
        try:
            await pull_request_agent.stop()
        except Exception:
            log.exception("pull request agent stop failed")
    await bus.stop()


@app.post("/events")
async def post_event(event: schemas.BaseEvent) -> dict:
    """Publish an event into the system."""
    await bus.publish(event)
    return {"status": "accepted", "event_id": str(event.event_id)}


@app.post("/webhook/github")
async def github_webhook(request: Request) -> JSONResponse:
    """Receive GitHub webhooks and convert supported events into internal events.

    Supported mappings:
    - issues (action: opened) -> IssueCreated
    - pull_request (action: opened) -> BaseEvent(event_type='PullRequestOpened')
    - issue_comment (action: created) -> BaseEvent(event_type='IssueCommentCreated')
    """
    event_header = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    try:
        accepted = await process_github_event(event_header, payload, bus)
        if accepted:
            return JSONResponse({"status": "accepted"})
        return JSONResponse({"status": "ignored"})
    except Exception:
        log.exception("failed to process github webhook")
        return JSONResponse({"status": "error"}, status_code=500)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
