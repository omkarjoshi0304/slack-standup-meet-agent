"""Tests for Jira sprint issue retrieval (C3).

Uses POST /rest/api/3/search/jql — the current Jira Cloud search endpoint.
The old GET/POST /rest/api/3/search was fully removed by Atlassian in
October 2025 (now returns 410 Gone); verified against Atlassian's current
API reference before implementing, not assumed from memory.
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from core.models import User
from integrations import jira_client


@pytest.fixture(autouse=True)
def jira_env(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")


@pytest.fixture()
def user():
    return User(
        slack_user_id="U1", tz="UTC", jira_account_id="acc-123", auth0_refresh_token="rt"
    )


def test_get_sprint_issues_raises_when_no_jira_account():
    unlinked = User(slack_user_id="U2", tz="UTC")

    with pytest.raises(RuntimeError, match="jira_account_id"):
        jira_client.get_sprint_issues(unlinked)


def test_get_sprint_issues_calls_search_jql_and_maps_issues(user):
    fake_response = httpx.Response(
        200,
        json={
            "isLast": True,
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {"summary": "Fix bug", "status": {"name": "In Progress"}},
                },
                {
                    "key": "PROJ-2",
                    "fields": {"summary": "Ship feature", "status": {"name": "To Do"}},
                },
            ],
        },
        request=httpx.Request("POST", "https://example.atlassian.net/rest/api/3/search/jql"),
    )

    with patch.object(jira_client, "get_token", return_value="jira-access-token") as mock_get_token, \
         patch.object(jira_client.httpx, "post", return_value=fake_response) as mock_post:
        issues = jira_client.get_sprint_issues(user)

    mock_get_token.assert_called_once_with(user, "jira")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://example.atlassian.net/rest/api/3/search/jql"
    assert kwargs["headers"]["Authorization"] == "Bearer jira-access-token"
    assert "acc-123" in kwargs["json"]["jql"]
    assert "openSprints()" in kwargs["json"]["jql"]
    assert kwargs["json"]["fields"] == ["summary", "status"]

    assert len(issues) == 2
    assert issues[0].key == "PROJ-1"
    assert issues[0].summary == "Fix bug"
    assert issues[0].status == "In Progress"
    assert issues[0].url == "https://example.atlassian.net/browse/PROJ-1"


def test_get_sprint_issues_raises_on_http_error(user):
    error_response = httpx.Response(
        401,
        json={"errorMessages": ["Authentication credentials are incorrect or missing."]},
        request=httpx.Request("POST", "https://example.atlassian.net/rest/api/3/search/jql"),
    )

    with patch.object(jira_client, "get_token", return_value="bad-token"), \
         patch.object(jira_client.httpx, "post", return_value=error_response):
        with pytest.raises(httpx.HTTPStatusError):
            jira_client.get_sprint_issues(user)
