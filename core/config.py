"""Environment-backed settings.

Settings.from_env() is called lazily by whatever needs it (agent/main.py, the
scheduler, integrations) — importing this module never touches the environment
by itself, so tests that don't need real credentials stay unaffected.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str
    agent_host: str
    agent_port: int
    slack_bot_token: str
    auth0_domain: str
    auth0_client_id: str
    auth0_client_secret: str
    jira_base_url: str
    google_client_id: str
    google_client_secret: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("DATABASE_URL", "sqlite:///./standup_meet.db"),
            openai_api_key=_require("OPENAI_API_KEY"),
            agent_host=os.environ.get("AGENT_HOST", "0.0.0.0"),
            agent_port=int(os.environ.get("AGENT_PORT", "8000")),
            slack_bot_token=_require("SLACK_BOT_TOKEN"),
            auth0_domain=_require("AUTH0_DOMAIN"),
            auth0_client_id=_require("AUTH0_CLIENT_ID"),
            auth0_client_secret=_require("AUTH0_CLIENT_SECRET"),
            jira_base_url=_require("JIRA_BASE_URL"),
            google_client_id=_require("GOOGLE_CLIENT_ID"),
            google_client_secret=_require("GOOGLE_CLIENT_SECRET"),
        )
