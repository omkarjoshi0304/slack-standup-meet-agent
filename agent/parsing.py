"""Parse @mention text into a command. No slash commands — managed Slack apps
never receive them, so this is the only entry point for user intent.

There's a single Slack bot identity (one CopilotKit Channel — see
channels/src/channel.ts), not separate @dailyagent/@meetagent apps, so the
sub-agent is the first word of the mention text: "dailyagent" or "meetagent".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")
_DURATION_RE = re.compile(r"(\d+)\s*m(?:in(?:ute)?s?)?\b", re.IGNORECASE)

_DAILYAGENT_ACTIONS: dict[tuple[str, ...], str] = {
    ("run", "now"): "run_now",
    ("set", "schedule"): "set_schedule",
    ("pause",): "pause",
    ("resume",): "resume",
}


@dataclass
class ParsedCommand:
    agent: str  # "dailyagent" | "meetagent"
    action: str  # e.g. "run_now", "set_schedule", "pause", "resume", "create_meeting"
    mentioned_user_ids: list[str]
    duration_min: int | None
    raw_text: str


def _dailyagent_action(tokens: list[str]) -> str:
    lowered = tuple(t.lower() for t in tokens)
    for prefix, action in _DAILYAGENT_ACTIONS.items():
        if lowered[: len(prefix)] == prefix:
            return action
    raise ValueError(f"dailyagent: unrecognized action '{' '.join(tokens)}'")


def _meetagent_action(tokens: list[str]) -> str:
    if tokens and tokens[0].lower() == "create":
        return "create_meeting"
    raise ValueError(f"meetagent: unrecognized action '{' '.join(tokens)}'")


def parse_mention(text: str) -> ParsedCommand:
    """Parse an @dailyagent/@meetagent message into agent/action/args.

    Raises ValueError when the text doesn't start with a known sub-agent
    keyword or the remaining tokens don't match a known action.
    """
    mentioned_user_ids = _MENTION_RE.findall(text)
    stripped = _MENTION_RE.sub("", text).strip()
    tokens = stripped.split()
    if not tokens:
        raise ValueError("empty mention text: expected 'dailyagent' or 'meetagent' followed by an action")

    agent = tokens[0].lower()
    rest = tokens[1:]
    if agent == "dailyagent":
        action = _dailyagent_action(rest)
    elif agent == "meetagent":
        action = _meetagent_action(rest)
    else:
        raise ValueError(f"unknown agent '{tokens[0]}': expected 'dailyagent' or 'meetagent'")

    duration_match = _DURATION_RE.search(stripped)
    duration_min = int(duration_match.group(1)) if duration_match else None

    return ParsedCommand(
        agent=agent,
        action=action,
        mentioned_user_ids=mentioned_user_ids,
        duration_min=duration_min,
        raw_text=text,
    )
