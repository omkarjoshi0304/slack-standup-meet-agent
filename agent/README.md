# agent — Python LangGraph agent (AG-UI server)

The brain. Exposed over the AG-UI protocol so `../channels` can reach it via `AGENT_URL`.
See root `AGENTS.md` for the full architecture.

## What's implemented (tasks F1/F2)

- `graph.py` — minimal echo graph (`MessagesState` in, `AIMessage` out), checkpointed with
  `MemorySaver` (AG-UI requires a checkpointer to read/write per-thread state).
- `main.py` — FastAPI app; `LangGraphAgent` wraps the compiled graph;
  `add_langgraph_fastapi_endpoint` mounts it at `POST /agent`.
- Tests: `../tests/test_graph.py` (unit test on the graph, no network).

Verified locally: unit test passes, the server boots, and a real AG-UI `RunAgentInput` POST
to `/agent` returns a correct SSE event stream ending in
`MESSAGES_SNAPSHOT` → `{"content": "echo: hello"}` → `RUN_FINISHED`. This proves the AG-UI
wiring end-to-end; the real `@dailyagent`/`@meetagent` routing graph replaces `graph.py` in
task B1.

## Run locally

```
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r ../requirements.txt
uvicorn agent.main:app --reload --port 8000   # run from repo root
```

Health check: `curl localhost:8000/health` and `curl localhost:8000/agent/health`.

## Run tests

```
pytest tests/test_graph.py
```
