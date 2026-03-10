"""
Generic endpoint interface for rule actions.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..rules.rules_engine import MatchResult


class Endpoint(abc.ABC):
    """Abstract base class for rule action endpoints."""

    @abc.abstractmethod
    def handle_action(self, action_key: str, action_value: Any, result: MatchResult) -> bool:
        """
        Handle a rule action.
        
        Args:
            action_key: The specific action key (e.g. 'vkb_set_shift').
            action_value: The value associated with the action.
            result: The full match result for context.
            
        Returns:
            True if the action was handled by this endpoint, False otherwise.
        """
        pass

    @abc.abstractmethod
    def on_session_event(self, event_type: str) -> None:
        """Called on session-level events (Commander, LoadGame, Shutdown)."""
        pass

    @abc.abstractmethod
    def connect(self) -> bool:
        """Initialize connection if required."""
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close connection if required."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return the display name of the endpoint."""
        pass
