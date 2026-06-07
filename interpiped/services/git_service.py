from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from git import Repo, GitCommandError


class GitServiceError(RuntimeError):
    pass


@dataclass
class GitService:
    repo_path: str
    repo: Repo | None = None

    def __post_init__(self) -> None:
        try:
            if os.path.isdir(os.path.join(self.repo_path, ".git")):
                self.repo = Repo(self.repo_path)
            else:
                # try opening as a repo anyway
                self.repo = Repo(self.repo_path)
        except Exception as e:
            raise GitServiceError(f"failed to open repo at {self.repo_path}: {e}")

    @classmethod
    def clone_repository(cls, repo_url: str, destination: str) -> "GitService":
        try:
            Repo.clone_from(repo_url, destination)
            return cls(destination)
        except GitCommandError as e:
            raise GitServiceError(f"clone failed: {e}")

    def create_branch(self, branch_name: str) -> None:
        try:
            if branch_name in self.repo.heads:
                head = self.repo.heads[branch_name]
            else:
                head = self.repo.create_head(branch_name)
            head.checkout()
        except Exception as e:
            raise GitServiceError(f"create_branch failed: {e}")

    def checkout_branch(self, branch_name: str) -> None:
        try:
            if branch_name in self.repo.heads:
                self.repo.heads[branch_name].checkout()
            else:
                self.repo.git.checkout(branch_name)
        except Exception as e:
            raise GitServiceError(f"checkout_branch failed: {e}")

    def commit_all(self, message: str) -> None:
        try:
            self.repo.git.add(all=True)
            if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
                # nothing to commit
                return
            self.repo.index.commit(message)
        except Exception as e:
            raise GitServiceError(f"commit_all failed: {e}")

    def push_branch(self, remote: str = "origin") -> None:
        try:
            r = self.repo.remote(remote)
            r.push()
        except Exception as e:
            raise GitServiceError(f"push_branch failed: {e}")

    def get_current_commit_sha(self) -> str:
        try:
            return self.repo.head.commit.hexsha
        except Exception as e:
            raise GitServiceError(f"get_current_commit_sha failed: {e}")
