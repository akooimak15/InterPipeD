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
