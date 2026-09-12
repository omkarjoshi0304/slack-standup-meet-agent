"""Parse @mention text into a command. No slash commands — managed Slack apps
never receive them, so this is the only entry point for user intent.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedCommand:
    agent: str  # "dailyagent" | "meetagent"
    action: str  # e.g. "run_now", "set_schedule", "pause", "resume", "create_meeting"
    mentioned_user_ids: list[str]
    raw_text: str


def parse_mention(text: str) -> ParsedCommand:
    """Parse an @dailyagent/@meetagent message into agent/action/args. B2."""
    raise NotImplementedError("B2: parse subcommands + extract @mentions/dates/durations")
