"""Unit tests for agent/summarize.py (B4). No network/API key — llm is injected."""
from __future__ import annotations

from agent.summarize import StandupSummary, summarize_issues
from core.types import Issue


def test_empty_issue_list_short_circuits_without_calling_llm():
    calls = []

    def fake_llm(text: str) -> StandupSummary:
        calls.append(text)
        raise AssertionError("llm should not be called for an empty issue list")

    result = summarize_issues([], llm=fake_llm)

    assert result == StandupSummary(done=[], in_progress=[], blockers=[])
    assert calls == []


def test_summarize_issues_passes_formatted_text_to_llm():
    issues = [Issue(key="PROJ-1", summary="Fix bug", status="Done", url="https://x/PROJ-1")]
    captured = {}

    def fake_llm(text: str) -> StandupSummary:
        captured["text"] = text
        return StandupSummary(done=["PROJ-1"], in_progress=[], blockers=[])

    result = summarize_issues(issues, llm=fake_llm)

    assert result.done == ["PROJ-1"]
    assert "PROJ-1" in captured["text"]
    assert "Fix bug" in captured["text"]
