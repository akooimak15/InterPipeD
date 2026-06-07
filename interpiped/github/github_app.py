from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from github import Github, GithubIntegration


class GitHubServiceError(RuntimeError):
    """Raised when GitHub App authentication or PR creation fails."""


@dataclass
class GitHubService:
    """Thin wrapper around PyGithub for GitHub App authentication and PR creation."""

    app_id: int
    private_key: str
    installation_id: int
    _integration: Optional[GithubIntegration] = None
    _github: Optional[Github] = None

    def __post_init__(self) -> None:
        if self._integration is None:
            try:
                self._integration = GithubIntegration(self.app_id, self.private_key)
            except Exception as exc:  # pragma: no cover - defensive
                raise GitHubServiceError(f"failed to initialize GitHub App integration: {exc}") from exc

    def get_installation_token(self, installation_id: Optional[int] = None) -> str:
        """Return an installation access token for the GitHub App."""

        target_installation_id = installation_id or self.installation_id
        try:
            auth = self._integration.get_access_token(target_installation_id)
            token = getattr(auth, "token", None)
            if not token:
                raise GitHubServiceError("installation token is empty")
            return token
        except Exception as exc:
            if isinstance(exc, GitHubServiceError):
                raise
            raise GitHubServiceError(f"failed to get installation token: {exc}") from exc

    def _get_github_client(self) -> Github:
        if self._github is not None:
            return self._github

        token = self.get_installation_token()
        try:
            self._github = Github(token)
            return self._github
        except Exception as exc:  # pragma: no cover - defensive
            raise GitHubServiceError(f"failed to create GitHub client: {exc}") from exc

    def create_pull_request(
        self,
        repository_full_name: str,
        head: str,
        base: str,
        title: str,
        body: str = "",
    ):
        """Create a pull request in the specified repository."""

        try:
            gh = self._get_github_client()
            repo = gh.get_repo(repository_full_name)
            return repo.create_pull(title=title, body=body, head=head, base=base)
        except Exception as exc:
            raise GitHubServiceError(f"failed to create pull request: {exc}") from exc
