from enum import StrEnum

from core import enum_docstrings


@enum_docstrings
class ConditionType(StrEnum):
    IGNORED_ROLES = "ignored_roles"
    """Ignore users who have any of the chosen roles."""

    REQUIRED_ROLES = "required_roles"
    """Only apply the rule to users who have the selected roles."""

    IGNORED_CHANNELS = "ignored_channels"
    """Skip messages from the selected channels."""

    ACTIVE_CHANNELS = "active_channels"
    """Only check the rule in the selected channels."""

    ACCOUNT_AGE_ABOVE = "account_age_above"
    """Only apply this rule to accounts older than the chosen age."""

    ACCOUNT_AGE_BELOW = "account_age_below"
    """Only apply this rule to newer accounts under the chosen age."""

    MEMBER_DURATION_ABOVE = "member_duration_above"
    """Only apply this rule to members who have been in the server longer than the selected time."""

    MEMBER_DURATION_BELOW = "member_duration_below"
    """Only apply this rule to newer members who joined more recently than the selected time."""

    IGNORE_BOTS = "ignore_bots"
    """Ignore messages from bots."""

    ONLY_BOTS = "only_bots"
    """Only apply the rule to bot messages."""

    IGNORED_CATEGORIES = "ignored_categories"
    """Skip messages from channels in the selected categories."""

    ACTIVE_CATEGORIES = "active_categories"
    """Only check the rule in the selected categories."""

    NEW_MESSAGE = "new_message"
    """Only apply the rule to brand new messages."""

    EDITED_MESSAGE = "edited_message"
    """Only apply the rule to messages that were edited."""

    ACTIVE_IN_THREADS = "active_in_threads"
    """Only apply the rule in threads."""

    IGNORE_THREADS = "ignore_threads"
    """Skip messages sent in threads."""

    IGNORE_FORWARDS = "ignore_forwards"
    """Ignore messages that include forwarded content."""

    ONLY_FORWARDS = "only_forwards"
    """Only apply the rule to messages that include forwarded content."""
