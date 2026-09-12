#!/usr/bin/env python3
"""Manual, one-off script to verify Jira Cloud REST API assumptions against a
real site. NOT part of the app's runtime or the pytest suite — it makes a
real network call and needs real personal credentials, so it lives outside
tests/ and is never auto-collected.

Bypasses Auth0/Token Vault entirely: uses HTTP Basic Auth with a personal
Jira API token, purely to confirm that integrations/jira_client.py's JQL,
endpoint (POST /rest/api/3/search/jql), and field mapping are correct
against a real site *before* wiring up the full Auth0 OAuth pipeline (C1/C2).
Imports the exact JQL template and field list jira_client.py uses, so a pass
here is a real signal about production behavior, not a separate guess.

Setup:
  1. Get a Jira API token: https://id.atlassian.com/manage-profile/security/api-tokens
  2. In Jira, assign at least one issue in the ACTIVE sprint to yourself —
     the JQL filters on `assignee = <you>`, so unassigned issues never match
     (this is easy to miss — an unassigned issue silently returns 0 results,
     not an error).
  3. export JIRA_BASE_URL=https://<your-site>.atlassian.net
     export JIRA_TEST_EMAIL=<your Atlassian account email>
     export JIRA_TEST_API_TOKEN=<the token from step 1>
  4. python scripts/manual_verify_jira.py
"""
from __future__ import annotations

import os
import sys

import httpx

from integrations.jira_client import _JQL, _MAX_RESULTS


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing {name}. See the docstring at the top of this script.", file=sys.stderr)
        sys.exit(1)
    return value


def main() -> None:
    base_url = require("JIRA_BASE_URL").rstrip("/")
    email = require("JIRA_TEST_EMAIL")
    token = require("JIRA_TEST_API_TOKEN")
    auth = (email, token)

    print("--- Step 1: who am I? (GET /rest/api/3/myself) ---")
    me = httpx.get(f"{base_url}/rest/api/3/myself", auth=auth)
    me.raise_for_status()
    me_data = me.json()
    account_id = me_data["accountId"]
    print(f"accountId:   {account_id}")
    print(f"displayName: {me_data.get('displayName')}\n")

    print("--- Step 2: run the exact JQL jira_client.py uses ---")
    jql = _JQL.format(account_id=account_id)
    print(f"JQL: {jql}\n")

    response = httpx.post(
        f"{base_url}/rest/api/3/search/jql",
        auth=auth,
        headers={"Accept": "application/json"},
        json={"jql": jql, "maxResults": _MAX_RESULTS, "fields": ["summary", "status"]},
    )
    response.raise_for_status()
    issues = response.json().get("issues", [])

    print(f"Matched {len(issues)} issue(s):\n")
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        status = issue["fields"]["status"]["name"]
        print(f"  {key} [{status}]: {summary}")
        print(f"    {base_url}/browse/{key}")

    if not issues:
        print(
            "  (none) — check the issue is: assigned to you, in the ACTIVE sprint, "
            "and not in a status JQL treats as 'Done'."
        )


if __name__ == "__main__":
    main()
