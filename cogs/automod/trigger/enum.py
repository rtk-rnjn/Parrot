from __future__ import annotations

from enum import StrEnum


class TriggerType(StrEnum):
    ALL_CAPS = "all_caps"
    MESSAGE_MENTIONS = "message_mentions"
    ANY_LINK = "any_link"

    VIOLATIONS = "violations"

    WORD_DENYLIST = "word_denylist"
    WORD_ALLOWLIST = "word_allowlist"

    WEBSITE_DENYLIST = "website_denylist"
    WEBSITE_ALLOWLIST = "website_allowlist"

    SERVER_INVITES = "server_invites"
    GOOGLE_FLAGGED_BAD_LINKS = "google_flagged_bad_links"

    USER_MESSAGES = "user_messages"
    CHANNEL_MESSAGES = "channel_messages"

    USER_MENTIONS = "user_mentions"
    CHANNEL_MENTIONS = "channel_mentions"

    MESSAGE_REGEX = "message_regex"
    MESSAGE_NOT_REGEX = "message_not_regex"

    CONSECUTIVE_IDENTICAL_MESSAGES = "consecutive_identical_messages"

    NICKNAME_REGEX = "nickname_regex"
    NICKNAME_NOT_REGEX = "nickname_not_regex"
    NICKNAME_WORD_ALLOWLIST = "nickname_word_allowlist"
    NICKNAME_WORD_DENYLIST = "nickname_word_denylist"

    USER_ATTACHMENTS = "user_attachments"
    CHANNEL_ATTACHMENTS = "channel_attachments"

    JOIN_USERNAME_WORD_ALLOWLIST = "join_username_word_allowlist"
    JOIN_USERNAME_WORD_DENYLIST = "join_username_word_denylist"
    JOIN_USERNAME_REGEX = "join_username_regex"
    JOIN_USERNAME_NOT_REGEX = "join_username_not_regex"
    JOIN_USERNAME_INVITE = "join_username_invite"

    NEW_MEMBER = "new_member"

    MESSAGE_WITHOUT_ATTACHMENTS = "message_without_attachments"
    MESSAGE_WITH_ATTACHMENTS = "message_with_attachments"

    FLAGGED_SCAM_LINKS = "flagged_scam_links"

    MESSAGE_LENGTH_GT = "message_length_gt"
    MESSAGE_LENGTH_LT = "message_length_lt"

    USER_LINKS = "user_links"
    CHANNEL_LINKS = "channel_links"

    DISCORD_AUTOMOD = "discord_automod"
