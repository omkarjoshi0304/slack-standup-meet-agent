"""Unit tests for agent/parsing.py (B2)."""
from __future__ import annotations

import pytest

from agent.parsing import parse_mention


def test_dailyagent_run_now():
    command = parse_mention("dailyagent run now")
    assert command.agent == "dailyagent"
    assert command.action == "run_now"
    assert command.mentioned_user_ids == []


def test_dailyagent_set_schedule():
    command = parse_mention("dailyagent set schedule weekdays 9:00 #team-standup")
    assert command.agent == "dailyagent"
    assert command.action == "set_schedule"


def test_dailyagent_pause_and_resume():
    assert parse_mention("dailyagent pause").action == "pause"
    assert parse_mention("dailyagent resume").action == "resume"


def test_meetagent_create_meeting_extracts_mentions_and_duration():
    command = parse_mention("meetagent create a meet with <@U111> <@U222> this week 30m")
    assert command.agent == "meetagent"
    assert command.action == "create_meeting"
    assert command.mentioned_user_ids == ["U111", "U222"]
    assert command.duration_min == 30


def test_unknown_agent_raises():
    with pytest.raises(ValueError):
        parse_mention("someotherbot do something")


def test_unrecognized_action_raises():
    with pytest.raises(ValueError):
        parse_mention("dailyagent do a backflip")


def test_empty_text_raises():
    with pytest.raises(ValueError):
        parse_mention("   ")
