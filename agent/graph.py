"""Minimal LangGraph graph used to prove the AG-UI wire-up (F2).

Replaced by the real @dailyagent / @meetagent routing graph in task B1.
"""

from uuid import uuid4

from ag_ui_langgraph import CustomEventNames
from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph


async def emit_assistant_text(text: str) -> AIMessage:
    """Stream `text` to the client as an assistant message, and return it for state.

    Putting an AIMessage in state is NOT enough to reach a chat surface. State
    updates only produce STATE_SNAPSHOT / MESSAGES_SNAPSHOT on the AG-UI wire,
    and CopilotKit's Slack renderer renders only TEXT_MESSAGE_* / tool-call /
    custom events — so a state-only reply is delivered as an empty message and
    silently posts nothing (this is exactly what blocked A1). `ag_ui_langgraph`
    turns a `manually_emit_message` custom event into the
    TEXT_MESSAGE_START/CONTENT/END triple a surface actually renders.

    Nodes that call a chat model with streaming get those events for free; nodes
    that assemble a reply themselves must call this.
    """
    message = AIMessage(content=text, id=str(uuid4()))
    await adispatch_custom_event(
        CustomEventNames.ManuallyEmitMessage.value,
        {"message_id": message.id, "message": text},
    )
    return message


async def echo_node(state: MessagesState) -> dict:
    last_message = state["messages"][-1]
    message = await emit_assistant_text(f"echo: {last_message.content}")
    return {"messages": [message]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("echo", echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    # AG-UI reads/writes state per thread_id, which requires a checkpointer.
    # Swap for a persistent one (e.g. Postgres) before production use.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
