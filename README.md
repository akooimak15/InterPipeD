# InterPipeD — scaffold

Initial scaffold for InterPipeD (v0.1) — agents, event model, in-memory EventBus,
worker example, FastAPI entrypoint and basic tests.

Quick start

1. Create virtualenv with Python 3.12

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run tests

```bash
pytest
```

3. Start the API (development)

```bash
uvicorn interpiped.api.main:app --reload
```

## Workflow

```
GitHub Issue
    ↓
Webhook → IssueCreated
    ↓
PMAgent → TaskCreated
    ↓
WorkerAgent
    ├─ clone repository
    ├─ create branch
    ├─ modify files
    ├─ commit changes
    ├─ push branch
    ├─ TaskCompleted
    └─ TaskFailed (on git/push error)
    ↓
TesterAgent → TestPassed / TestFailed
    ↓
ArchitectAgent → ArchitectureApproved / ArchitectureRejected
    ↓
PullRequestAgent → PullRequestCreated / PullRequestFailed
```

## GitHub App

InterPipeD uses `GitHubService` for GitHub App authentication and pull request creation.

Role in the workflow:

1. WorkerAgent clones, commits, and pushes the task branch to GitHub.
2. GitHubService exchanges the GitHub App installation for a token.
3. PullRequestAgent calls `GitHubService.create_pull_request()` after architecture approval.

Only PR creation is supported in v0.1. Auto-merge and review automation are out of scope.

### GitHub App permissions

The app needs these repository permissions on the target repo:

- **Contents**: Read & write (clone, commit, push branches)
- **Pull requests**: Read & write (create pull requests)
- **Metadata**: Read-only (repository access)

Install the app on the repository you use for validation.

### Manual E2E validation

`scripts/e2e_github_validation.py` runs the full agent pipeline against a real
GitHub repository. It is for manual validation only — not for CI.

The script will:

1. Create a temporary issue context with a unique title
2. Publish `IssueCreated` into the in-process pipeline
3. Run PM → Worker → Tester → Architect → PullRequest agents
4. Verify via the GitHub API that the branch, commit, and pull request exist

**Note:** PMAgent decomposes each issue into three tasks (`-models`, `-service`,
`-api`), so one run creates three branches and three pull requests. The script
waits for and validates whichever pull request completes first.

#### Setup

```bash
export GITHUB_APP_ID=123456
export GITHUB_INSTALLATION_ID=12345678
export GITHUB_REPOSITORY=your-org/your-repo
export GITHUB_BASE_BRANCH=main   # optional, default: main

# Private key: inline or from file
export GITHUB_PRIVATE_KEY="$(cat /path/to/your-app.private-key.pem)"
# export GITHUB_PRIVATE_KEY_PATH=/path/to/your-app.private-key.pem
```

Use a dedicated test repository. The worker pushes real branches and opens real
pull requests.

#### Run

```bash
source .venv/bin/activate
python scripts/e2e_github_validation.py
```

Optional flags:

```bash
python scripts/e2e_github_validation.py \
  --repository your-org/your-repo \
  --base-branch main \
  --timeout 180
```

On success:

```
InterPipeD E2E validation: SUCCESS
branch: task/interpiped-e2e-20250607120000-models
commit: abc123def456...
pull request url: https://github.com/your-org/your-repo/pull/42
```
