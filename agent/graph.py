"""LangGraph graph: routes a parsed mention to the daily-standup or meeting
branch (B1). Replaces the F2 echo graph now that AG-UI wiring is verified.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from agent.parsing import ParsedCommand, parse_mention
from agent.prompts import MEETING_REASONING_SYSTEM_PROMPT, STANDUP_SUMMARY_SYSTEM_PROMPT
from agent.tools import get_free_busy, get_sprint_summary, propose_and_book_meeting

DAILY_TOOLS = [get_sprint_summary]
MEET_TOOLS = [get_free_busy, propose_and_book_meeting]


class AgentState(MessagesState):
    command: ParsedCommand | None


def parse_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    try:
        command = parse_mention(last_message.content)
    except ValueError as exc:
        return {
            "messages": [AIMessage(content=f"Sorry, I couldn't parse that: {exc}")],
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


def daily_node(state: AgentState) -> dict:
    result = _daily_agent().invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


def meet_node(state: AgentState) -> dict:
    result = _meet_agent().invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


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
