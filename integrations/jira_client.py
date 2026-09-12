"""Sprint issues per user via Jira Cloud REST (JQL).

Uses POST /rest/api/3/search/jql — the current Jira Cloud search endpoint.
The old GET/POST /rest/api/3/search was fully removed by Atlassian in
October 2025 and now returns 410 Gone; this was verified against Atlassian's
current API reference before implementing, not assumed from memory.

Fetches a single page (maxResults, no nextPageToken loop): Atlassian's own
community has reported the token-pagination loop not terminating correctly
on this endpoint, and one sprint's issue count for one engineer comfortably
fits a single page for our use case.

If the team's Auth0 "jira" connection is Atlassian's official OAuth 2.0 (3LO)
app rather than a custom connection wrapping a site-scoped token, calls must
instead go through https://api.atlassian.com/ex/jira/{cloudId}/... (requiring
a cloudId lookup) rather than directly at JIRA_BASE_URL — worth confirming
against however the team configures that connection.

Implements the frozen interface from TASKS.md Epic 0 (F5).
"""
from __future__ import annotations

import os

import httpx

from core.models import User
from core.types import Issue
from integrations.auth0_vault import get_token

_JQL = 'assignee = "{account_id}" AND sprint in openSprints() AND status != Done'
_MAX_RESULTS = 100


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def get_sprint_issues(user: User) -> list[Issue]:
    if not user.jira_account_id:
        raise RuntimeError(f"User {user.slack_user_id!r} has no jira_account_id on file.")

    token = get_token(user, "jira")
    base_url = _require_env("JIRA_BASE_URL").rstrip("/")

    response = httpx.post(
        f"{base_url}/rest/api/3/search/jql",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={
            "jql": _JQL.format(account_id=user.jira_account_id),
            "maxResults": _MAX_RESULTS,
            "fields": ["summary", "status"],
        },
    )
    response.raise_for_status()
    data = response.json()

    return [
        Issue(
            key=issue["key"],
            summary=issue["fields"]["summary"],
            status=issue["fields"]["status"]["name"],
            url=f"{base_url}/browse/{issue['key']}",
        )
        for issue in data.get("issues", [])
    ]
