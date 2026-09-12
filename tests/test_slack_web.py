"""Tests for direct Slack Web API calls (C6, pulled in early by C2's DM step)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from integrations import slack_web


@pytest.fixture(autouse=True)
def slack_env(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")


def test_post_message_returns_message_ts():
    fake_response = {"ok": True, "ts": "1234.5678"}
    with patch.object(
        slack_web.WebClient, "chat_postMessage", return_value=fake_response
    ) as mock_post:
        ts = slack_web.post_message("C1", [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}])

    assert ts == "1234.5678"
    _, kwargs = mock_post.call_args
    assert kwargs["channel"] == "C1"


def test_open_dm_returns_channel_id():
    fake_response = {"ok": True, "channel": {"id": "D0123"}}
    with patch.object(
        slack_web.WebClient, "conversations_open", return_value=fake_response
    ) as mock_open:
        channel_id = slack_web.open_dm("U1")

    assert channel_id == "D0123"
    _, kwargs = mock_open.call_args
    assert kwargs["users"] == "U1"
