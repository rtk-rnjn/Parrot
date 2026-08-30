from enum import StrEnum


class ConditionType(StrEnum):
    IGNORED_ROLES = "ignored_roles"
    REQUIRED_ROLES = "required_roles"

    IGNORED_CHANNELS = "ignored_channels"
    ACTIVE_CHANNELS = "active_channels"

    ACCOUNT_AGE_ABOVE = "account_age_above"
    ACCOUNT_AGE_BELOW = "account_age_below"

    MEMBER_DURATION_ABOVE = "member_duration_above"
    MEMBER_DURATION_BELOW = "member_duration_below"

    IGNORE_BOTS = "ignore_bots"
    ONLY_BOTS = "only_bots"

    IGNORED_CATEGORIES = "ignored_categories"
    ACTIVE_CATEGORIES = "active_categories"

    NEW_MESSAGE = "new_message"
    EDITED_MESSAGE = "edited_message"

    ACTIVE_IN_THREADS = "active_in_threads"
    IGNORE_THREADS = "ignore_threads"

    IGNORE_FORWARDS = "ignore_forwards"
    ONLY_FORWARDS = "only_forwards"
