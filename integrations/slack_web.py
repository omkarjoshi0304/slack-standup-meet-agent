"""Direct Slack Web API calls for proactive posts.

Only used by the scheduled standup path (core/scheduler.py): a scheduled
digest has no triggering mention for Channels/AG-UI to ride on, so it posts
straight to Slack with the bot token instead.

Frozen interface — see TASKS.md Epic 0 (F5). Implemented in C6.
"""
from __future__ import annotations


def post_message(channel_id: str, blocks: list) -> str:
    """Post via chat.postMessage. Returns the message ts."""
    raise NotImplementedError("C6: slack_sdk chat.postMessage for scheduled digests")
