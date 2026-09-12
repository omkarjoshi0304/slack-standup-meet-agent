"""Direct Slack Web API calls for proactive posts and DMs.

Used by the scheduled standup path (core/scheduler.py): a scheduled digest
has no triggering mention for Channels/AG-UI to ride on, so it posts straight
to Slack with the bot token instead (C6). Also used by the account-linking
flow (integrations/auth0_link.py) to DM a user their Auth0 connect link (C2).

Implements the frozen interface from TASKS.md Epic 0 (F5).
"""
from __future__ import annotations

import os

from slack_sdk import WebClient


def _client() -> WebClient:
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing required env var: SLACK_BOT_TOKEN")
    return WebClient(token=token)


def post_message(channel_id: str, blocks: list) -> str:
    """Post via chat.postMessage. Returns the message ts."""
    response = _client().chat_postMessage(channel=channel_id, blocks=blocks)
    return response["ts"]


def open_dm(user_id: str) -> str:
    """Open (or reuse) a DM channel with a user. Returns the channel id."""
    response = _client().conversations_open(users=user_id)
    return response["channel"]["id"]
