from enum import StrEnum

from core.utils import enum_docstrings


@enum_docstrings
class EffectType(StrEnum):
    DELETE_MESSAGE = "delete_message"
    """Delete the message that triggered the rule."""

    ADD_VIOLATION = "add_violation"
    """Add a violations to the user's record."""

    KICK_USER = "kick_user"
    """Kick the user that triggered the rule."""

    BAN_USER = "ban_user"
    """Ban the user from the server."""

    MUTE_USER = "mute_user"
    """Mute the user that triggered the rule."""

    WARN_USER = "warn_user"
    """Warn the user that triggered the rule."""

    SET_NICKNAME = "set_nickname"
    """Change the user's nickname."""

    RESET_VIOLATIONS = "reset_violations"
    """Clear a specific violations record for the user."""

    DELETE_MULTIPLE_MESSAGES = "delete_multiple_messages"
    """Remove several recent messages from the user."""

    GIVE_ROLE = "give_role"
    """Give the user a role for a set amount of time or permanently."""

    ENABLE_SLOWMODE = "enable_slowmode"
    """Turn on slowmode in the channel where the rule fired."""

    REMOVE_ROLE = "remove_role"
    """Take a role away from the user."""

    SEND_MESSAGE = "send_message"
    """Send a custom message to a chosen channel."""

    TIMEOUT_USER = "timeout_user"
    """Apply Discord timeout to the user."""

    SEND_ALERT = "send_alert"
    """Send an alert embed to a chosen channel."""
