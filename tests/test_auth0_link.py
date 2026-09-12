"""Tests for the one-time Auth0 account-linking flow (C2)."""
from __future__ import annotations
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import jwt
import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.models import User
from integrations import auth0_link


@pytest.fixture(autouse=True)
def auth0_env(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "test-tenant.auth0.com")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AUTH0_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AUTH0_GOOGLE_CONNECTION", "google-oauth2")
    monkeypatch.setenv("AUTH0_JIRA_CONNECTION", "jira-custom-connection")
    monkeypatch.setenv("AUTH0_REDIRECT_URI", "https://example.com/link/callback")
    monkeypatch.setenv("LINK_STATE_SECRET", "test-signing-secret")


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_make_state_and_parse_state_round_trip():
    state = auth0_link.make_state("U1", "google")

    slack_user_id, provider = auth0_link.parse_state(state)

    assert slack_user_id == "U1"
    assert provider == "google"


def test_parse_state_rejects_tampered_state():
    state = auth0_link.make_state("U1", "google")
    tampered = state[:-1] + ("a" if state[-1] != "a" else "b")

    with pytest.raises(ValueError):
        auth0_link.parse_state(tampered)


def test_build_authorize_url_has_expected_params():
    url = auth0_link.build_authorize_url("U1", "google")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "test-tenant.auth0.com"
    assert parsed.path == "/authorize"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == ["https://example.com/link/callback"]
    assert params["connection"] == ["google-oauth2"]
    assert "offline_access" in params["scope"][0]
    slack_user_id, provider = auth0_link.parse_state(params["state"][0])
    assert slack_user_id == "U1"
    assert provider == "google"


def test_exchange_code_for_tokens_calls_authorization_code():
    with patch.object(
        auth0_link.GetToken,
        "authorization_code",
        return_value={"access_token": "at", "refresh_token": "rt", "id_token": "idt"},
    ) as mock_exchange:
        tokens = auth0_link.exchange_code_for_tokens("the-code")

    assert tokens["refresh_token"] == "rt"
    _, kwargs = mock_exchange.call_args
    assert kwargs["code"] == "the-code"
    assert kwargs["redirect_uri"] == "https://example.com/link/callback"


def test_handle_callback_persists_refresh_token_for_new_user(session):
    id_token = jwt.encode({"sub": "auth0|abc123"}, "unused-secret", algorithm="HS256")
    state = auth0_link.make_state("U42", "google")

    with patch.object(
        auth0_link,
        "exchange_code_for_tokens",
        return_value={"access_token": "at", "refresh_token": "rt", "id_token": id_token},
    ):
        auth0_link.handle_callback(code="the-code", state=state, session=session)

    user = session.exec(
        __import__("sqlmodel").select(User).where(User.slack_user_id == "U42")
    ).first()
    assert user is not None
    assert user.auth0_refresh_token == "rt"
    assert user.auth0_user_id == "auth0|abc123"


def test_handle_callback_updates_existing_user(session):
    existing = User(slack_user_id="U42", tz="UTC")
    session.add(existing)
    session.commit()

    state = auth0_link.make_state("U42", "jira")
    with patch.object(
        auth0_link,
        "exchange_code_for_tokens",
        return_value={"access_token": "at", "refresh_token": "rt2", "id_token": None},
    ):
        auth0_link.handle_callback(code="the-code", state=state, session=session)

    session.refresh(existing)
    assert existing.auth0_refresh_token == "rt2"


def test_send_link_prompt_dms_the_authorize_url():
    with patch("integrations.auth0_link.slack_web") as mock_slack:
        mock_slack.open_dm.return_value = "D0123"
        auth0_link.send_link_prompt("U1", "google")

    mock_slack.open_dm.assert_called_once_with("U1")
    channel_id, blocks = mock_slack.post_message.call_args[0]
    assert channel_id == "D0123"
    assert "auth0.com/authorize" in str(blocks)
