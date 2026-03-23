from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent import AgentRole, Agent

from .errors import PermissionDenied
from .utils import parse_text_list


@dataclass(frozen=True)
class PermissionContext:
    """
    Minimal context required for permission checks.

    Currently, category-based access is driven by `Ticket.category_id`.
    """

    ticket_category_id: Optional[int]


class OperatorPermissionsService:
    """
    Checks whether an operator can perform a given `action` (permission).

    Sources:
    - `agents.category_access` (list of category ids)
    - `agents.permissions` (list of permission names)
    """

    def __init__(self, session: Session):
        self.session = session

    def assert_can(
        self,
        agent: Agent,
        action: str,
        context: PermissionContext,
    ) -> None:
        # Admin shortcut.
        if getattr(agent, "role", None) == AgentRole.admin:
            return

        if getattr(agent, "is_active", True) is False:
            raise PermissionDenied("Agent is inactive")

        allowed_actions = set(parse_text_list(agent.permissions))
        if action not in allowed_actions:
            raise PermissionDenied("Action permission is not granted")

        # If we have no category in context, we can't evaluate category_access.
        if context.ticket_category_id is None:
            return

        allowed_categories = set()
        for c in parse_text_list(agent.category_access):
            try:
                allowed_categories.add(int(c))
            except ValueError:
                continue

        if allowed_categories and context.ticket_category_id not in allowed_categories:
            raise PermissionDenied("Agent has no access to this category")

