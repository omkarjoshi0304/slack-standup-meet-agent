"""Per-user delegated token retrieval from Auth0 Token Vault.

Exchanges a user's stored Auth0 refresh token for a federated connection's
access token (Google, Jira) via Auth0's Token Vault token-exchange grant
(RFC 8693 + Auth0's federated-connection-access-token extension). Constants
and the GetToken.access_token_for_connection call are verified against the
installed `auth0-python` SDK source, not guessed.

Reads AUTH0_* env vars directly (like core/db.py reads DATABASE_URL) rather
than through core.config.Settings, so a token lookup doesn't require
unrelated credentials (Slack/Jira base URL/etc) to be set.

Implements the frozen interface from TASKS.md Epic 0 (F5).
"""
from __future__ import annotations

import os

from auth0.authentication.get_token import GetToken

from core.models import User
from core.types import Provider

_SUBJECT_TYPE_REFRESH_TOKEN = "urn:ietf:params:oauth:token-type:refresh_token"
_REQUESTED_TOKEN_TYPE_FEDERATED_ACCESS_TOKEN = (
    "http://auth0.com/oauth/token-type/federated-connection-access-token"
)

# Shared with integrations/auth0_link.py (C2), which needs the same
# connection-name-per-provider lookup to build the initial /authorize URL.
CONNECTION_ENV_VAR: dict[Provider, str] = {
    "google": "AUTH0_GOOGLE_CONNECTION",
    "jira": "AUTH0_JIRA_CONNECTION",
}


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def connection_for(provider: Provider) -> str:
    return require_env(CONNECTION_ENV_VAR[provider])


def get_token(user: User, provider: Provider) -> str:
    if not user.auth0_refresh_token:
        raise RuntimeError(
            f"User {user.slack_user_id!r} has not linked their {provider} account "
            "via Auth0 yet (see task C2: account-linking flow)."
        )

    client = GetToken(
        domain=require_env("AUTH0_DOMAIN"),
        client_id=require_env("AUTH0_CLIENT_ID"),
        client_secret=require_env("AUTH0_CLIENT_SECRET"),
    )
    response = client.access_token_for_connection(
        subject_token_type=_SUBJECT_TYPE_REFRESH_TOKEN,
        subject_token=user.auth0_refresh_token,
        requested_token_type=_REQUESTED_TOKEN_TYPE_FEDERATED_ACCESS_TOKEN,
        connection=connection_for(provider),
    )
    return response["access_token"]
