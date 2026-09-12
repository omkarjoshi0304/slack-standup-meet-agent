#!/usr/bin/env python3
"""Manual, one-off script: run the REAL Epic B pipeline (parse -> route ->
LangGraph tool-calling loop -> LLM summary) against REAL Jira data, without a
configured Auth0 tenant.

Auth0 Token Vault (C1) isn't set up yet, so integrations/jira_client.py's real
Bearer-token call can't authenticate. This script monkeypatches only the
Jira-fetch step to use Basic Auth (personal API token) instead — the same
auth style already verified working by manual_verify_jira.py. Parsing (B2),
routing (B1), tool orchestration (B3), and the LLM's summarization (B4 prompt)
all run unmodified and for real.

NOT part of the app's runtime or the pytest suite. Needs real personal
credentials and makes real network calls (Jira + OpenAI).

Setup (same vars as manual_verify_jira.py, plus OPENAI_API_KEY):
  export JIRA_BASE_URL=https://<your-site>.atlassian.net
  export JIRA_TEST_EMAIL=<your Atlassian account email>
  export JIRA_TEST_API_TOKEN=<a Jira API token>
  export OPENAI_API_KEY=<your key>
  python3 scripts/manual_run_daily_partial.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from langchain_core.messages import HumanMessage

from core.db import get_session, init_db
from core.models import User
from core.types import Issue
from integrations.jira_client import _JQL, _MAX_RESULTS


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing {name}. See the docstring at the top of this script.", file=sys.stderr)
        sys.exit(1)
    return value


def _fetch_issues_via_basic_auth(base_url: str, auth: tuple[str, str], account_id: str) -> list[Issue]:
    """Stand-in for integrations.jira_client.get_sprint_issues, real HTTP call,
    just using Basic Auth instead of an Auth0-issued Bearer token."""
    jql = _JQL.format(account_id=account_id)
    response = httpx.post(
        f"{base_url}/rest/api/3/search/jql",
        auth=auth,
        headers={"Accept": "application/json"},
        json={"jql": jql, "maxResults": _MAX_RESULTS, "fields": ["summary", "status"]},
    )
    response.raise_for_status()
    return [
        Issue(
            key=issue["key"],
            summary=issue["fields"]["summary"],
            status=issue["fields"]["status"]["name"],
            url=f"{base_url}/browse/{issue['key']}",
        )
        for issue in response.json().get("issues", [])
    ]


def main() -> None:
    base_url = require("JIRA_BASE_URL").rstrip("/")
    email = require("JIRA_TEST_EMAIL")
    token = require("JIRA_TEST_API_TOKEN")
    require("OPENAI_API_KEY")
    auth = (email, token)

    print("--- Step 1: who am I? (real Jira call) ---")
    me = httpx.get(f"{base_url}/rest/api/3/myself", auth=auth)
    me.raise_for_status()
    account_id = me.json()["accountId"]
    print(f"accountId: {account_id}\n")

    print("--- Step 2: seed a local User row (bypasses Auth0 linking) ---")
    slack_user_id = "MANUALTEST"
    init_db()
    with get_session() as session:
        from sqlmodel import select

        user = session.exec(select(User).where(User.slack_user_id == slack_user_id)).first()
        if user is None:
            user = User(slack_user_id=slack_user_id, tz="UTC")
        user.jira_account_id = account_id
        session.add(user)
        session.commit()
    print(f"Seeded User(slack_user_id={slack_user_id!r}, jira_account_id={account_id!r})\n")

    print("--- Step 3: monkeypatch only the Jira-fetch step (not Auth0, not the tool, not the graph) ---")
    import integrations.jira_client as jira_client_module

    jira_client_module.get_sprint_issues = lambda user: _fetch_issues_via_basic_auth(
        base_url, auth, user.jira_account_id
    )

    print("--- Step 4: run the REAL graph: parse -> route -> LLM tool-calling loop ---")
    from agent.graph import graph

    config = {"configurable": {"thread_id": "manual-test-thread"}}
    # Plain slack_user_id, not the <@ID> mention syntax: the react-agent reads
    # raw message text to decide the tool's user_id argument, and an
    # unambiguous plain id avoids it guessing at bracket/prefix formatting
    # (a real gap noted in TASKS.md B8 — nothing feeds "who's asking" in yet).
    result = graph.invoke(
        {"messages": [HumanMessage(content=f"dailyagent run now for user {slack_user_id}")]},
        config,
    )

    print("\n--- Final reply ---")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
