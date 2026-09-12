"""Per-user delegated token retrieval from Auth0 Token Vault.

Frozen interface — see TASKS.md Epic 0 (F5). Implemented in C1.
"""
from __future__ import annotations

from core.models import User
from core.types import Provider


def get_token(user: User, provider: Provider) -> str:
    raise NotImplementedError("C1: wire Auth0 Token Vault lookup")
