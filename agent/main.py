"""AG-UI server exposing our LangGraph agent, plus the Auth0 account-linking
callback (C2) — both are small enough to share one process for the hackathon
rather than stand up a second server/port.

CopilotKit Channels reaches /agent over AG-UI at AGENT_URL (see channels/src/agent.ts).
Auth0 redirects the user's browser to /link/callback after they authorize a
connection (see integrations/auth0_link.py). Run with:
    uvicorn agent.main:app --reload --port 8000

Verified against the installed `ag-ui-langgraph` package (not the `copilotkit` PyPI
package, which targets a different/older CopilotKit protocol, not AG-UI): a real
AG-UI RunAgentInput POST to /agent returns a correct SSE stream ending in
MESSAGES_SNAPSHOT -> RUN_FINISHED.
"""
from contextlib import asynccontextmanager

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from agent.graph import graph
from core.db import get_session, init_db
from integrations.auth0_link import handle_callback

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="slack-standup-meet-agent", lifespan=lifespan)

langgraph_agent = LangGraphAgent(name="standup-meet-agent", graph=graph)

add_langgraph_fastapi_endpoint(app, langgraph_agent, "/agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/link/callback", response_class=PlainTextResponse)
def link_callback(code: str, state: str) -> str:
    with get_session() as session:
        try:
            return handle_callback(code=code, state=state, session=session)
        except (ValueError, RuntimeError) as err:
            raise HTTPException(status_code=400, detail=str(err))
