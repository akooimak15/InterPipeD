import os

import pytest

from git import Repo

from interpiped.services.git_service import GitService, GitServiceError


def write_file(path, name, content="x"):
    p = path / name
    p.write_text(content)
    return p


def test_branch_and_commit(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    # init source repo
    r = Repo.init(src)
    write_file(src, "README.md", "hello")
    r.git.add(A=True)
    r.index.commit("initial")

    # clone
    dest = tmp_path / "dest"
    gs = GitService.clone_repository(str(src), str(dest))

    # create branch
    gs.create_branch("feature-x")
    assert gs.repo.active_branch.name == "feature-x"

    # create file and commit
    write_file(dest, "a.txt", "content")
    gs.commit_all("add a.txt")
    sha = gs.get_current_commit_sha()
    assert isinstance(sha, str) and len(sha) > 0
