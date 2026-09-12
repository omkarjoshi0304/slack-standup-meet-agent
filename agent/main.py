"""AG-UI server exposing our LangGraph agent.

CopilotKit Channels reaches this over AG-UI at AGENT_URL (see channels/src/agent.ts).
Run with: uvicorn agent.main:app --reload --port 8000
"""

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from dotenv import load_dotenv
from fastapi import FastAPI

from agent.graph import graph

load_dotenv()

app = FastAPI(title="slack-standup-meet-agent")

langgraph_agent = LangGraphAgent(name="standup-meet-agent", graph=graph)

add_langgraph_fastapi_endpoint(app, langgraph_agent, "/agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
