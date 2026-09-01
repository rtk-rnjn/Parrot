from __future__ import annotations

from enum import StrEnum

from core.utils import enum_docstrings


@enum_docstrings
class TriggerType(StrEnum):
    ALL_CAPS = "all_caps"
    """Fires when a message exceeds a certain percentage of uppercase characters."""

    MESSAGE_MENTIONS = "message_mentions"
    """Fires when a message exceeds the configured threshold for unique user @mentions."""

    ANY_LINK = "any_link"
    """Fires when a message contains any valid link."""

    VIOLATIONS = "violations"
    """Fires when the offending user has amassed x violations in y minutes."""

    WORD_DENYLIST = "word_denylist"
    """Fires when a message contains any word from the specified denylist."""

    WORD_ALLOWLIST = "word_allowlist"
    """Fires when a message contains words not in the specified allowlist."""

    WEBSITE_DENYLIST = "website_denylist"
    """Fires when a message contains any link to a domain from the specified denylist."""

    WEBSITE_ALLOWLIST = "website_allowlist"
    """Fires when a message contains links not in the specified allowlist."""

    SERVER_INVITES = "server_invites"
    """Fires when a message contains a server invite link."""

    GOOGLE_FLAGGED_BAD_LINKS = "google_flagged_bad_links"
    """Fires when a message contains a link that Google has flagged as malicious."""

    USER_MESSAGES = "user_messages"
    """Fires when the offending user has sent x messages in y seconds."""

    CHANNEL_MESSAGES = "channel_messages"
    """Fires when the channel has received x messages in y seconds."""

    USER_MENTIONS = "user_mentions"
    """Fires when the offending user has mentioned x users in y seconds."""

    CHANNEL_MENTIONS = "channel_mentions"
    """Fires when the channel has received x mentions in y seconds."""

    MESSAGE_REGEX = "message_regex"
    """Fires when a message matches the specified regular expression."""

    MESSAGE_NOT_REGEX = "message_not_regex"
    """Fires when a message does not match the specified regular expression."""

    X_CONSECUTIVE_IDENTICAL_MESSAGES = "x_consecutive_identical_messages"
    """Fires when the offending user has sent x identical messages in a row."""

    NICKNAME_REGEX = "nickname_regex"
    """Fires when the nickname of the user matches the specified regular expression."""

    NICKNAME_NOT_REGEX = "nickname_not_regex"
    """Fires when the nickname of the user does not match the specified regular expression."""

    NICKNAME_WORD_ALLOWLIST = "nickname_word_allowlist"
    """Fires when the nickname contains words not in the specified allowlist."""

    NICKNAME_WORD_DENYLIST = "nickname_word_denylist"
    """Fires when the nickname contains any word from the specified denylist."""

    USER_ATTACHMENTS = "user_attachments"
    """Fires when the offending user has sent x attachments in y seconds."""

    CHANNEL_ATTACHMENTS = "channel_attachments"
    """Fires when the channel has received x attachments in y seconds."""

    JOIN_USERNAME_WORD_ALLOWLIST = "join_username_word_allowlist"
    """Fires when the username of a user joining contains words not in the specified allowlist."""

    JOIN_USERNAME_WORD_DENYLIST = "join_username_word_denylist"
    """Fires when the username of a user joining contains any word from the specified denylist."""

    JOIN_USERNAME_REGEX = "join_username_regex"
    """Fires when the username of a user joining matches the specified regular expression."""

    JOIN_USERNAME_NOT_REGEX = "join_username_not_regex"
    """Fires when the username of a user joining does not match the specified regular expression."""

    JOIN_USERNAME_INVITE = "join_username_invite"
    """Fires when the username of a user joining contains a server invite link."""

    NEW_MEMBER = "new_member"
    """Fires when a new member joins the server."""

    MESSAGE_WITHOUT_ATTACHMENTS = "message_without_attachments"
    """Fires when a message does not contain any attachments."""

    MESSAGE_WITH_ATTACHMENTS = "message_with_attachments"
    """Fires when a message contains attachments."""

    FLAGGED_SCAM_LINKS = "flagged_scam_links"
    """Fires when a message contains a link that has been flagged as a scam."""

    MESSAGE_LENGTH_GT = "message_length_gt"
    """Fires when a message contains more than x characters."""

    MESSAGE_LENGTH_LT = "message_length_lt"
    """Fires when a message contains less than x characters."""

    X_USER_LINKS_IN_Y_MINUTES = "x_user_links_in_y_minutes"
    """Fires when the offending user has sent x links in y seconds."""

    X_CHANNEL_LINKS_IN_Y_MINUTES = "x_channel_links_in_y_minutes"
    """Fires when the channel has received x links in y seconds."""

    DISCORD_AUTOMOD = "discord_automod"
    """Fires when a message triggers Discord's Automod."""

    X_USER_MESSAGE_IN_Y_MINUTES = "x_message_in_y_minutes"
    """Fires when the offending user has sent x messages in y minutes."""

    X_CHANNEL_MESSAGE_IN_Y_MINUTES = "x_channel_message_in_y_minutes"
    """Fires when the channel has received x messages in y minutes."""

    X_VOILATION_IN_Y_MINUTES = "x_violation_in_y_minutes"
    """Fires when the offending user has amassed x violations in y minutes."""

    X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES = "x_user_message_mentions_in_y_minutes"
    """Fires when the offending user has mentioned x users in y minutes."""

    X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES = "x_channel_message_mentions_in_y_minutes"
    """Fires when the channel has received x mentions in y minutes."""
