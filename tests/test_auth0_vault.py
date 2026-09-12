"""Tests for Auth0 Token Vault delegated token retrieval (C1)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.models import User
from integrations import auth0_vault


@pytest.fixture(autouse=True)
def auth0_env(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "test-tenant.auth0.com")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AUTH0_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AUTH0_GOOGLE_CONNECTION", "google-oauth2")
    monkeypatch.setenv("AUTH0_JIRA_CONNECTION", "jira-custom-connection")


@pytest.fixture()
def linked_user():
    return User(slack_user_id="U1", tz="UTC", auth0_refresh_token="stored-refresh-token")


def test_get_token_raises_when_user_has_not_linked_account():
    unlinked_user = User(slack_user_id="U2", tz="UTC")

    with pytest.raises(RuntimeError, match="has not linked"):
        auth0_vault.get_token(unlinked_user, "google")


def test_get_token_exchanges_refresh_token_for_google_connection(linked_user):
    with patch.object(
        auth0_vault.GetToken,
        "access_token_for_connection",
        return_value={"access_token": "google-access-token"},
    ) as mock_exchange:
        token = auth0_vault.get_token(linked_user, "google")

    assert token == "google-access-token"
    _, kwargs = mock_exchange.call_args
    assert kwargs["connection"] == "google-oauth2"
    assert kwargs["subject_token"] == "stored-refresh-token"
    assert kwargs["subject_token_type"] == "urn:ietf:params:oauth:token-type:refresh_token"
    assert (
        kwargs["requested_token_type"]
        == "http://auth0.com/oauth/token-type/federated-connection-access-token"
    )


def test_get_token_exchanges_refresh_token_for_jira_connection(linked_user):
    with patch.object(
        auth0_vault.GetToken,
        "access_token_for_connection",
        return_value={"access_token": "jira-access-token"},
    ) as mock_exchange:
        token = auth0_vault.get_token(linked_user, "jira")

    assert token == "jira-access-token"
    _, kwargs = mock_exchange.call_args
    assert kwargs["connection"] == "jira-custom-connection"


def test_get_token_raises_clear_error_when_connection_env_var_missing(linked_user, monkeypatch):
    monkeypatch.delenv("AUTH0_GOOGLE_CONNECTION", raising=False)

    with pytest.raises(RuntimeError, match="AUTH0_GOOGLE_CONNECTION"):
        auth0_vault.get_token(linked_user, "google")
