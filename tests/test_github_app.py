from __future__ import annotations

from types import SimpleNamespace

import pytest

from interpiped.github.github_app import GitHubService, GitHubServiceError


class DummyRepo:
    def __init__(self):
        self.calls = []

    def create_pull(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(html_url="https://github.com/org/repo/pull/1", number=1, **kwargs)


class DummyGithub:
    def __init__(self, token):
        self.token = token
        self.repo = DummyRepo()

    def get_repo(self, full_name):
        self.full_name = full_name
        return self.repo


class DummyIntegration:
    def __init__(self, app_id, private_key):
        self.app_id = app_id
        self.private_key = private_key
        self.tokens = []

    def get_access_token(self, installation_id):
        self.tokens.append(installation_id)
        return SimpleNamespace(token=f"token-{installation_id}")


def test_get_installation_token(monkeypatch):
    monkeypatch.setattr("interpiped.github.github_app.GithubIntegration", DummyIntegration)
    svc = GitHubService(app_id=1, private_key="key", installation_id=99)

    token = svc.get_installation_token()

    assert token == "token-99"


def test_create_pull_request(monkeypatch):
    dummy_integration = DummyIntegration(1, "key")

    monkeypatch.setattr("interpiped.github.github_app.GithubIntegration", lambda app_id, private_key: dummy_integration)
    monkeypatch.setattr("interpiped.github.github_app.Github", DummyGithub)

    svc = GitHubService(app_id=1, private_key="key", installation_id=99)

    pr = svc.create_pull_request(
        repository_full_name="org/repo",
        head="feature-branch",
        base="main",
        title="Add feature",
        body="Details",
    )

    assert pr.html_url == "https://github.com/org/repo/pull/1"
    assert pr.title == "Add feature"
    assert pr.body == "Details"
    assert pr.head == "feature-branch"
    assert pr.base == "main"


def test_get_installation_token_error(monkeypatch):
    class BadIntegration:
        def __init__(self, app_id, private_key):
            pass

        def get_access_token(self, installation_id):
            raise RuntimeError("boom")

    monkeypatch.setattr("interpiped.github.github_app.GithubIntegration", BadIntegration)
    svc = GitHubService(app_id=1, private_key="key", installation_id=99)

    with pytest.raises(GitHubServiceError):
        svc.get_installation_token()
