#!/usr/bin/env python3
"""Manual, one-off script to verify Google Calendar integration against a
real calendar. NOT part of the pytest suite: it makes real network calls,
needs a real short-lived access token, and (with --create-event) creates a
REAL event with a real Google Meet link on your primary calendar.

Bypasses Auth0/Token Vault entirely: monkey-patches
integrations.auth0_vault.get_token to return a short-lived OAuth access
token you obtain manually via Google's OAuth Playground, then calls the
REAL integrations/google_calendar.py functions unmodified — so a pass is a
real signal about production behavior, not a separate guess.

Setup:
  1. https://developers.google.com/oauthplayground/
  2. Gear icon (top right) -> check "Use your own OAuth credentials" ->
     paste a Client ID/Secret from a Google Cloud project with the Calendar
     API enabled (console.cloud.google.com -> APIs & Services -> Library ->
     "Google Calendar API" -> Enable; then Credentials -> Create OAuth
     client ID -> Desktop app).
  3. In Step 1 (left panel), find and select the scope:
       https://www.googleapis.com/auth/calendar
     (full access — needed for --create-event; calendar.readonly is enough
     for the freebusy-only check). Click "Authorize APIs" and sign in with
     the Google account you want to test against.
  4. In Step 2, click "Exchange authorization code for tokens".
  5. Copy the "Access token" value (it expires in about an hour).
  6. export GOOGLE_TEST_ACCESS_TOKEN=<paste it — only in your terminal>
  7. python3 scripts/manual_verify_google_calendar.py
     Add --create-event to also test event creation.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# Running this file directly only puts scripts/ on sys.path, not the repo
# root, so the project packages wouldn't otherwise be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import User
from core.types import Slot, Window
from integrations import google_calendar


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing {name}. See the docstring at the top of this script.", file=sys.stderr)
        sys.exit(1)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create-event",
        action="store_true",
        help="Also test create_event — creates a REAL event with a REAL Meet "
        "link on your primary calendar.",
    )
    args = parser.parse_args()

    access_token = require("GOOGLE_TEST_ACCESS_TOKEN")
    # Only used to satisfy google_calendar.py's "has this user linked Google"
    # guard clause — never sent to the API in this script (attendees=[]).
    user = User(slack_user_id="manual-test", tz="UTC", google_account_id="manual-test@example.com")

    with patch.object(google_calendar, "get_token", return_value=access_token):
        print("--- Step 1: freebusy on your primary calendar, next 24h ---")
        now = datetime.now(timezone.utc)
        window = Window(start=now, end=now + timedelta(hours=24))
        busy = google_calendar.get_freebusy(user, window)
        print(f"Busy intervals in the next 24h: {len(busy)}")
        for interval in busy:
            print(f"  {interval.start} -> {interval.end}")

        if not args.create_event:
            print("\n(Skipping event creation — pass --create-event to also test that.)")
            return

        print("\n--- Step 2: create a real event with a Meet link ---")
        start = now + timedelta(minutes=10)
        slot = Slot(start=start, end=start + timedelta(minutes=30))
        result = google_calendar.create_event(user, [], slot)
        print(f"event_id:  {result.event_id}")
        print(f"meet_url:  {result.meet_url}")
        print(f"html_link: {result.html_link}")
        print("\n(Go delete this test event from your calendar when you're done.)")


if __name__ == "__main__":
    main()
