"""Google Calendar free/busy + event creation with a Meet link.

Builds a per-call googleapiclient service from the user's delegated Google
access token (via C1's Token Vault exchange) — a bare access token, no
refresh handling here since Token Vault already handles refresh for us.
cache_discovery=False avoids a known googleapiclient warning when
oauth2client isn't installed; static_discovery=True avoids a network call to
fetch the discovery document on every build. Both verified against the
installed google-api-python-client (signatures inspected directly), not
assumed.

conferenceDataVersion=1 must be passed as a request parameter (per Google's
own docs) — otherwise conferenceData is silently ignored and no Meet link is
created; no error is returned in that case.

User.google_account_id is treated as that user's Google account email — the
only identifier Calendar's `attendees[].email` accepts.

Implements the frozen interface from TASKS.md Epic 0 (F5).
"""
from __future__ import annotations

import uuid

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from core.models import User
from core.types import BusyInterval, EventResult, Slot, Window
from integrations.auth0_vault import get_token


def _service_for(user: User):
    access_token = get_token(user, "google")
    credentials = Credentials(token=access_token)
    return build(
        "calendar", "v3", credentials=credentials, cache_discovery=False, static_discovery=True
    )


def get_freebusy(user: User, window: Window) -> list[BusyInterval]:
    if not user.google_account_id:
        raise RuntimeError(f"User {user.slack_user_id!r} has no google_account_id on file.")

    service = _service_for(user)
    response = (
        service.freebusy()
        .query(
            body={
                "timeMin": window.start.isoformat(),
                "timeMax": window.end.isoformat(),
                "items": [{"id": "primary"}],
            }
        )
        .execute()
    )

    busy = response["calendars"]["primary"]["busy"]
    return [BusyInterval(start=b["start"], end=b["end"]) for b in busy]


def create_event(organizer: User, attendees: list[User], slot: Slot) -> EventResult:
    if not organizer.google_account_id:
        raise RuntimeError(f"User {organizer.slack_user_id!r} has no google_account_id on file.")

    service = _service_for(organizer)
    body = {
        "summary": "Meeting",
        "start": {"dateTime": slot.start.isoformat()},
        "end": {"dateTime": slot.end.isoformat()},
        "attendees": [{"email": a.google_account_id} for a in attendees if a.google_account_id],
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    event = (
        service.events()
        .insert(calendarId="primary", body=body, conferenceDataVersion=1)
        .execute()
    )

    meet_url = ""
    for entry_point in event.get("conferenceData", {}).get("entryPoints", []):
        if entry_point.get("entryPointType") == "video":
            meet_url = entry_point.get("uri", "")
            break

    return EventResult(event_id=event["id"], meet_url=meet_url, html_link=event["htmlLink"])
