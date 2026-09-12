"""One-time Auth0 account-linking flow (C2).

Builds the Auth0 /authorize URL for a given Slack user + provider, DMs it to
them, and handles the OAuth callback: exchanges the authorization code for
tokens and persists the refresh token onto core.models.User so C1
(integrations/auth0_vault.get_token) can use it later.

/authorize parameters (response_type, client_id, redirect_uri, scope, state,
connection, connection_scope) are documented, standard Auth0 Authentication
API parameters — verified via Auth0's docs/community references, not guessed.
`state` is HMAC-signed here (not an Auth0 concept) so the callback can
recover which Slack user + provider initiated the flow, and so a tampered
state is rejected instead of silently trusted.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from urllib.parse import urlencode

import jwt
from auth0.authentication.get_token import GetToken
from sqlmodel import Session, select

from core.models import User
from core.types import Provider
from integrations import slack_web
from integrations.auth0_vault import connection_for, require_env

_SCOPE = "openid profile email offline_access"


def _state_secret() -> bytes:
    return require_env("LINK_STATE_SECRET").encode("utf-8")


def make_state(slack_user_id: str, provider: Provider) -> str:
    payload = json.dumps({"slack_user_id": slack_user_id, "provider": provider}).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    signature = hmac.new(_state_secret(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def parse_state(state: str) -> tuple[str, Provider]:
    try:
        payload_b64, signature = state.split(".", 1)
    except ValueError:
        raise ValueError("Malformed state: expected '<payload>.<signature>'")

    expected_signature = hmac.new(
        _state_secret(), payload_b64.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid state signature — possible tampering")

    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return payload["slack_user_id"], payload["provider"]


def build_authorize_url(slack_user_id: str, provider: Provider) -> str:
    params = {
        "response_type": "code",
        "client_id": require_env("AUTH0_CLIENT_ID"),
        "redirect_uri": require_env("AUTH0_REDIRECT_URI"),
        "scope": _SCOPE,
        "connection": connection_for(provider),
        "state": make_state(slack_user_id, provider),
    }

    connection_scope_env = {"google": "AUTH0_GOOGLE_CONNECTION_SCOPE", "jira": "AUTH0_JIRA_CONNECTION_SCOPE"}
    connection_scope = os.environ.get(connection_scope_env[provider])
    if connection_scope:
        params["connection_scope"] = connection_scope

    domain = require_env("AUTH0_DOMAIN")
    return f"https://{domain}/authorize?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    client = GetToken(
        domain=require_env("AUTH0_DOMAIN"),
        client_id=require_env("AUTH0_CLIENT_ID"),
        client_secret=require_env("AUTH0_CLIENT_SECRET"),
    )
    return client.authorization_code(code=code, redirect_uri=require_env("AUTH0_REDIRECT_URI"))


def _extract_sub(id_token: str | None) -> str | None:
    """Best-effort, unverified decode — used only as an informational label,
    never as an authorization decision, so signature verification is not
    required here."""
    if not id_token:
        return None
    try:
        return jwt.decode(id_token, options={"verify_signature": False}).get("sub")
    except jwt.PyJWTError:
        return None


def handle_callback(code: str, state: str, session: Session) -> str:
    slack_user_id, provider = parse_state(state)
    tokens = exchange_code_for_tokens(code)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "Auth0 did not return a refresh_token. Check that 'Allow Offline Access' "
            "is enabled for this application/API in the Auth0 dashboard."
        )

    user = session.exec(select(User).where(User.slack_user_id == slack_user_id)).first()
    if user is None:
        user = User(slack_user_id=slack_user_id, tz="UTC")
        session.add(user)

    user.auth0_refresh_token = refresh_token
    sub = _extract_sub(tokens.get("id_token"))
    if sub:
        user.auth0_user_id = sub

    session.commit()
    return f"Linked your {provider} account. You can close this tab."


def send_link_prompt(slack_user_id: str, provider: Provider) -> None:
    url = build_authorize_url(slack_user_id, provider)
    channel_id = slack_web.open_dm(slack_user_id)
    slack_web.post_message(
        channel_id,
        [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Connect your {provider} account so I can act on your behalf: <{url}|Link {provider}>",
                },
            }
        ],
    )
