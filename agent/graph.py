"""Minimal LangGraph graph used to prove the AG-UI wire-up (F2).

Replaced by the real @dailyagent / @meetagent routing graph in task B1.
"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph


def echo_node(state: MessagesState) -> dict:
    last_message = state["messages"][-1]
    return {"messages": [AIMessage(content=f"echo: {last_message.content}")]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("echo", echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    # AG-UI reads/writes state per thread_id, which requires a checkpointer.
    # Swap for a persistent one (e.g. Postgres) before production use.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
