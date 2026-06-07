"""GitHub integration helpers (webhook ingestion)."""

from .webhook import process_github_event

__all__ = ["process_github_event"]
