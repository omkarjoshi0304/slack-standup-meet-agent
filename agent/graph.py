"""LangGraph graph: routes a parsed mention to the daily-standup or meeting
branch. Frozen interface — see TASKS.md Epic 0 (F5). Implemented in B1.
"""
from __future__ import annotations

from langgraph.graph import StateGraph


def build_graph() -> StateGraph:
    """Build the graph. Routing key is ParsedCommand.agent ('dailyagent' |
    'meetagent'); each branch binds the relevant agent/tools.py tools."""
    raise NotImplementedError("B1: build StateGraph with daily/meet branches")
