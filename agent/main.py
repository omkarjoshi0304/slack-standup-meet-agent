"""AG-UI server exposing the LangGraph graph, so CopilotKit Channels can reach
it via AGENT_URL. F2/B1.

TODO(B): verify the exact CopilotKit Python SDK call for mounting a LangGraph
graph as an AG-UI endpoint against the current `copilotkit` package version —
not confirmed here, don't guess it into place without checking the installed
version's docs first.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# TODO(B): mount agent.graph.build_graph() as an AG-UI endpoint here so
# Channels' AGENT_URL can reach it.
