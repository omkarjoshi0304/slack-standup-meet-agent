"""Standup summarization: one LLM call per member, {done, in_progress, blockers}."""
from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from agent.prompts import STANDUP_SUMMARY_SYSTEM_PROMPT
from core.types import Issue


class StandupSummary(BaseModel):
    done: list[str]
    in_progress: list[str]
    blockers: list[str]


def _issues_text(issues: list[Issue]) -> str:
    return "\n".join(f"- [{issue.status}] {issue.key}: {issue.summary} ({issue.url})" for issue in issues)


def _default_llm(issues_text: str) -> StandupSummary:
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini").with_structured_output(StandupSummary)
    return model.invoke(
        [("system", STANDUP_SUMMARY_SYSTEM_PROMPT), ("human", issues_text)]
    )


def summarize_issues(
    issues: list[Issue],
    llm: Callable[[str], StandupSummary] = _default_llm,
) -> StandupSummary:
    """Summarize one member's current-sprint issues. Never calls `llm` for an
    empty issue list — there's nothing to summarize."""
    if not issues:
        return StandupSummary(done=[], in_progress=[], blockers=[])
    return llm(_issues_text(issues))
