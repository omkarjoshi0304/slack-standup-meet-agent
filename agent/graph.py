"""LangGraph graph: routes a parsed mention to the daily-standup or meeting
branch (B1). Replaces the F2 echo graph now that AG-UI wiring is verified.
"""
from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

from ag_ui_langgraph import CustomEventNames
from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from agent.parsing import ParsedCommand, parse_mention
from agent.prompts import MEETING_REASONING_SYSTEM_PROMPT, STANDUP_SUMMARY_SYSTEM_PROMPT
from agent.tools import get_free_busy, get_sprint_summary, propose_and_book_meeting

DAILY_TOOLS = [get_sprint_summary]
MEET_TOOLS = [get_free_busy, propose_and_book_meeting]


async def emit_assistant_text(text: str, *, message_id: str | None = None) -> AIMessage:
    """Stream `text` to the client as an assistant message, and return it for state.

    Putting an AIMessage in state is NOT enough to reach a chat surface. State
    updates only produce STATE_SNAPSHOT / MESSAGES_SNAPSHOT on the AG-UI wire,
    and CopilotKit's Slack renderer renders only TEXT_MESSAGE_* / tool-call /
    custom events — so a state-only reply is delivered as an empty message and
    silently posts nothing. That is what blocked A1 for so long: the dashboard
    reported `Provider delivery completed` for a message with no renderable
    content. `ag_ui_langgraph` turns a `manually_emit_message` custom event into
    the TEXT_MESSAGE_START/CONTENT/END triple a surface actually renders.

    Pass `message_id` when the message already exists (e.g. a react agent's final
    reply) so the wire and the state agree on one id instead of showing it twice.
    """
    message = AIMessage(content=text, id=message_id or str(uuid4()))
    await adispatch_custom_event(
        CustomEventNames.ManuallyEmitMessage.value,
        {"message_id": message.id, "message": text},
    )
    return message


class AgentState(MessagesState):
    command: ParsedCommand | None


async def parse_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    try:
        command = parse_mention(last_message.content)
    except ValueError as exc:
        return {
            "messages": [await emit_assistant_text(f"Sorry, I couldn't parse that: {exc}")],
            "command": None,
        }
    return {"command": command}


def route_after_parse(state: AgentState) -> str:
    command = state.get("command")
    if command is None:
        return END
    return "meet" if command.agent == "meetagent" else "daily"


# Built lazily so importing this module (and anything that imports it, like
# agent/main.py) never requires OPENAI_API_KEY — only actually running a
# daily/meet turn does.
@lru_cache(maxsize=1)
def _daily_agent():
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(ChatOpenAI(model="gpt-4o-mini"), DAILY_TOOLS, prompt=STANDUP_SUMMARY_SYSTEM_PROMPT)


@lru_cache(maxsize=1)
def _meet_agent():
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(ChatOpenAI(model="gpt-4o-mini"), MEET_TOOLS, prompt=MEETING_REASONING_SYSTEM_PROMPT)


async def _run_branch(agent, state: AgentState) -> dict:
    """Run a react-agent branch and make sure its answer reaches the surface.

    `ainvoke` doesn't stream, so the model emits no TEXT_MESSAGE_* events of its
    own — the final reply has to be emitted explicitly or Slack shows nothing.
    """
    result = await agent.ainvoke({"messages": state["messages"]})
    messages = result["messages"]
    reply = messages[-1]
    if isinstance(reply, AIMessage) and isinstance(reply.content, str) and reply.content:
        await emit_assistant_text(reply.content, message_id=reply.id)
    return {"messages": messages}


async def daily_node(state: AgentState) -> dict:
    return await _run_branch(_daily_agent(), state)


async def meet_node(state: AgentState) -> dict:
    return await _run_branch(_meet_agent(), state)


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("parse", parse_node)
    builder.add_node("daily", daily_node)
    builder.add_node("meet", meet_node)

    builder.add_edge(START, "parse")
    builder.add_conditional_edges("parse", route_after_parse, {"daily": "daily", "meet": "meet", END: END})
    builder.add_edge("daily", END)
    builder.add_edge("meet", END)

    # AG-UI reads/writes state per thread_id, which requires a checkpointer.
    # Swap for a persistent one (e.g. Postgres) before production use.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
