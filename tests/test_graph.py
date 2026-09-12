"""Unit tests for the B1 routing graph — routing logic only. The daily/meet
react-agent nodes need a real OPENAI_API_KEY and real integrations, so
they're exercised manually / in a later integration pass, not here.
"""
from __future__ import annotations

import asyncio

from ag_ui_langgraph import CustomEventNames
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import END, graph, parse_node, route_after_parse

# `parse_node` is async because a reply it produces has to be streamed to the
# surface, so the tests drive it with asyncio.run rather than taking a
# pytest-asyncio dependency for a handful of cases.


def test_parse_node_routes_dailyagent():
    state = {"messages": [HumanMessage(content="dailyagent run now")]}

    result = asyncio.run(parse_node(state))

    assert result["command"].agent == "dailyagent"
    assert route_after_parse({"command": result["command"]}) == "daily"


def test_parse_node_routes_meetagent():
    state = {"messages": [HumanMessage(content="meetagent create a meet with <@U1> <@U2>")]}

    result = asyncio.run(parse_node(state))

    assert result["command"].agent == "meetagent"
    assert route_after_parse({"command": result["command"]}) == "meet"


def test_graph_replies_and_ends_on_unparseable_text():
    # Driven through the graph rather than calling parse_node directly: its
    # reply is dispatched as a LangChain custom event, which needs a run context.
    state = {"messages": [HumanMessage(content="hello there")]}
    config = {"configurable": {"thread_id": "test-thread-unparseable"}}

    result = asyncio.run(graph.ainvoke(state, config))

    assert result["command"] is None
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content.startswith("Sorry, I couldn't parse that:")
    assert route_after_parse({"command": None}) == END


def test_parse_failure_reply_is_emitted_as_a_streamable_message():
    """A state-only reply is invisible to chat surfaces.

    CopilotKit's Slack renderer renders TEXT_MESSAGE_* events and ignores
    MESSAGES_SNAPSHOT, so a node that only writes an AIMessage into state gets
    delivered as an empty message and posts nothing. `ag_ui_langgraph` turns this
    custom event into the TEXT_MESSAGE_START/CONTENT/END triple.
    """

    async def collect_manual_emits():
        # Unparseable text routes straight to END, so the whole graph runs
        # without reaching the daily/meet nodes (and without OPENAI_API_KEY).
        state = {"messages": [HumanMessage(content="hello there")]}
        config = {"configurable": {"thread_id": "test-thread-stream"}}
        return [
            event
            async for event in graph.astream_events(state, config)
            if event["event"] == "on_custom_event"
            and event["name"] == CustomEventNames.ManuallyEmitMessage.value
        ]

    emitted = asyncio.run(collect_manual_emits())

    assert len(emitted) == 1
    assert emitted[0]["data"]["message"].startswith("Sorry, I couldn't parse that:")
    assert emitted[0]["data"]["message_id"]
