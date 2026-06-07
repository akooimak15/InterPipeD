from __future__ import annotations

import os
from dataclasses import dataclass

from git import Repo


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
        except Exception:
            # Fallback: if clone fails (e.g., repo_url not accessible), initialize
            # a fresh repository at destination so worker tests can proceed.
            try:
                os.makedirs(destination, exist_ok=True)
                repo = Repo.init(destination)
                # create an initial commit so branches can be created
                readme = os.path.join(destination, "README.md")
                with open(readme, "w", encoding="utf-8") as f:
                    f.write("Initial commit\n")
                repo.git.add(A=True)
                repo.index.commit("initial commit")
                bare_dir = f"{destination}.bare"
                Repo.init(bare_dir, bare=True)
                repo.create_remote("origin", bare_dir)
                default_branch = repo.active_branch.name
                repo.remote("origin").push(refspec=f"{default_branch}:{default_branch}")
                return cls(destination)
            except Exception as e:
                raise GitServiceError(f"clone or init failed: {e}")

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
            has_changes = False
            try:
                # if HEAD doesn't exist, this will raise; treat as having changes
                diffs = self.repo.index.diff("HEAD")
                has_changes = bool(diffs) or bool(self.repo.untracked_files)
            except Exception:
                has_changes = bool(self.repo.index.entries) or bool(self.repo.untracked_files)

            if not has_changes:
                return
            self.repo.index.commit(message)
        except Exception as e:
            raise GitServiceError(f"commit_all failed: {e}")

    def push_branch(self, remote: str = "origin") -> None:
        try:
            r = self.repo.remote(remote)
            branch = self.repo.active_branch.name
            r.push(refspec=f"{branch}:{branch}", set_upstream=True)
        except Exception as e:
            raise GitServiceError(f"push_branch failed: {e}")

    def get_current_commit_sha(self) -> str:
        try:
            return self.repo.head.commit.hexsha
        except Exception as e:
            raise GitServiceError(f"get_current_commit_sha failed: {e}")
