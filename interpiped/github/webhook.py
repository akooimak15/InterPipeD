from __future__ import annotations

from typing import Any

from interpiped.events import schemas


async def process_github_event(event_header: str, payload: dict[str, Any], bus) -> bool:
    """Process a GitHub webhook payload and publish internal events.

    Returns True if an internal event was published, False if ignored.
    """
    # For v0.1 only handle issues.opened
    if event_header == "issues" and payload.get("action") == "opened":
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        repo_name = repo.get("full_name") or repo.get("name") or ""

        evt = schemas.IssueCreated(
            issue_number=issue.get("number"),
            repository=repo_name,
            title=issue.get("title", ""),
            description=issue.get("body", ""),
            source="github",
        )
        await bus.publish(evt)
        return True

    return False
