"""Unit tests for the B1 routing graph — routing logic only. The daily/meet
react-agent nodes need a real OPENAI_API_KEY and real integrations, so
they're exercised manually / in a later integration pass, not here.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import END, parse_node, route_after_parse


def test_parse_node_routes_dailyagent():
    state = {"messages": [HumanMessage(content="dailyagent run now")]}

    result = parse_node(state)

    assert result["command"].agent == "dailyagent"
    assert route_after_parse({"command": result["command"]}) == "daily"


def test_parse_node_routes_meetagent():
    state = {"messages": [HumanMessage(content="meetagent create a meet with <@U1> <@U2>")]}

    result = parse_node(state)

    assert result["command"].agent == "meetagent"
    assert route_after_parse({"command": result["command"]}) == "meet"


def test_parse_node_replies_and_ends_on_unparseable_text():
    state = {"messages": [HumanMessage(content="hello there")]}

    result = parse_node(state)

    assert result["command"] is None
    assert isinstance(result["messages"][0], AIMessage)
    assert route_after_parse({"command": None}) == END
