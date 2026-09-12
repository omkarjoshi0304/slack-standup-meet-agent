"""Tests for Google Calendar free/busy + event creation (C4/C5)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from core.models import User
from core.types import Slot, Window
from integrations import google_calendar


@pytest.fixture()
def user():
    return User(
        slack_user_id="U1", tz="UTC", google_account_id="alice@example.com", auth0_refresh_token="rt"
    )


def test_get_freebusy_raises_when_no_google_account():
    unlinked = User(slack_user_id="U2", tz="UTC")
    window = Window(start=datetime(2026, 9, 12, 9), end=datetime(2026, 9, 12, 17))

    with pytest.raises(RuntimeError, match="google_account_id"):
        google_calendar.get_freebusy(unlinked, window)


def test_get_freebusy_maps_busy_intervals(user):
    fake_service = MagicMock()
    fake_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {
            "primary": {
                "busy": [{"start": "2026-09-12T09:00:00Z", "end": "2026-09-12T09:30:00Z"}]
            }
        }
    }
    window = Window(start=datetime(2026, 9, 12, 9), end=datetime(2026, 9, 12, 17))

    with patch.object(google_calendar, "_service_for", return_value=fake_service):
        busy = google_calendar.get_freebusy(user, window)

    assert len(busy) == 1
    assert busy[0].start.hour == 9

    query_body = fake_service.freebusy.return_value.query.call_args.kwargs["body"]
    assert query_body["items"] == [{"id": "primary"}]
    assert query_body["timeMin"] == window.start.isoformat()
    assert query_body["timeMax"] == window.end.isoformat()


def test_create_event_requests_meet_link_and_maps_result(user):
    fake_service = MagicMock()
    fake_service.events.return_value.insert.return_value.execute.return_value = {
        "id": "evt123",
        "htmlLink": "https://calendar.google.com/event?eid=abc",
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"}
            ]
        },
    }
    attendee = User(slack_user_id="U2", tz="UTC", google_account_id="bob@example.com")
    slot = Slot(start=datetime(2026, 9, 12, 10), end=datetime(2026, 9, 12, 10, 30))

    with patch.object(google_calendar, "_service_for", return_value=fake_service):
        result = google_calendar.create_event(user, [attendee], slot)

    assert result.event_id == "evt123"
    assert result.meet_url == "https://meet.google.com/abc-defg-hij"
    assert result.html_link == "https://calendar.google.com/event?eid=abc"

    insert_kwargs = fake_service.events.return_value.insert.call_args.kwargs
    assert insert_kwargs["conferenceDataVersion"] == 1
    assert insert_kwargs["calendarId"] == "primary"
    assert insert_kwargs["body"]["attendees"] == [{"email": "bob@example.com"}]
    assert insert_kwargs["body"]["conferenceData"]["createRequest"]["conferenceSolutionKey"] == {
        "type": "hangoutsMeet"
    }
