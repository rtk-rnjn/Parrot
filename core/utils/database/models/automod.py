from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from ._common import NoConfigDict


class Entry[K: str, C](TypedDict):
    type: K
    config: C


class EntryOptional[K: str, C](TypedDict):
    type: K
    config: NotRequired[C]


class AllCapsConfigDict(TypedDict):
    min_count: int
    percentage: int


class CountConfigDict(TypedDict):
    count: int


class TimeWindowConfigDict(TypedDict):
    count: int
    within_minutes: int


class ListConfigDict(TypedDict):
    list: NotRequired[str | None]


class RegexConfigDict(TypedDict):
    regex: str


class LengthConfigDict(TypedDict):
    length: int


class ViolationTriggerConfigDict(TypedDict):
    violation_name: str
    number_of_violations: int
    within_minutes: int


type TriggerDict = (
    EntryOptional[
        Literal[
            "any_link",
            "server_invites",
            "join_username_invite",
            "new_member",
            "message_without_attachments",
            "message_with_attachments",
            "flagged_scam_links",
            "discord_automod",
        ],
        NoConfigDict,
    ]
    | Entry[Literal["all_caps"], AllCapsConfigDict]
    | Entry[Literal["message_mentions"], CountConfigDict]
    | Entry[Literal["violations"], ViolationTriggerConfigDict]
    | EntryOptional[
        Literal[
            "word_denylist",
            "word_allowlist",
            "website_denylist",
            "website_allowlist",
            "nickname_word_allowlist",
            "nickname_word_denylist",
            "join_username_word_allowlist",
            "join_username_word_denylist",
        ],
        ListConfigDict,
    ]
    | Entry[
        Literal[
            "message_regex",
            "message_not_regex",
            "nickname_regex",
            "nickname_not_regex",
            "join_username_regex",
            "join_username_not_regex",
        ],
        RegexConfigDict,
    ]
    | Entry[
        Literal[
            "x_consecutive_identical_messages",
            "x_user_attachments_in_y_minutes",
            "x_channel_attachments_in_y_minutes",
            "x_user_links_in_y_minutes",
            "x_channel_links_in_y_minutes",
            "x_violation_in_y_minutes",
            "x_user_message_in_y_minutes",
            "x_channel_message_in_y_minutes",
            "x_user_message_mentions_in_y_minutes",
            "x_channel_message_mentions_in_y_minutes",
        ],
        TimeWindowConfigDict,
    ]
    | Entry[Literal["message_length_gt", "message_length_lt"], LengthConfigDict]
)


class RolesConfigDict(TypedDict):
    roles: list[int]
    require_all: NotRequired[bool]


class ChannelsConfigDict(TypedDict):
    channels: list[int]


class CategoriesConfigDict(TypedDict):
    categories: list[int]


class DurationConfigDict(TypedDict):
    minutes: int


type ConditionDict = (
    EntryOptional[
        Literal[
            "ignore_bots",
            "only_bots",
            "new_message",
            "edited_message",
            "active_in_threads",
            "ignore_threads",
            "ignore_forwards",
            "only_forwards",
        ],
        NoConfigDict,
    ]
    | Entry[Literal["ignored_roles", "required_roles"], RolesConfigDict]
    | Entry[Literal["ignored_channels", "active_channels"], ChannelsConfigDict]
    | Entry[Literal["ignored_categories", "active_categories"], CategoriesConfigDict]
    | Entry[
        Literal["account_age_above", "account_age_below", "member_duration_above", "member_duration_below"],
        DurationConfigDict,
    ]
)


class ViolationEffectConfigDict(TypedDict):
    name: NotRequired[str | None]


class MessageConfigDict(TypedDict):
    message: NotRequired[str | None]


class BanConfigDict(TypedDict):
    duration_minutes: int
    delete_days: int
    message: NotRequired[str | None]


class MuteConfigDict(TypedDict):
    duration_minutes: int
    message: NotRequired[str | None]


class TimeoutConfigDict(TypedDict):
    duration_minutes: int
    message: NotRequired[str | None]


class NicknameConfigDict(TypedDict):
    nickname: NotRequired[str | None]


class DeleteMessagesConfigDict(TypedDict):
    count: int
    max_age_seconds: int


class RoleConfigDict(TypedDict):
    duration_seconds: int
    role_id: NotRequired[int | None]


class SlowmodeConfigDict(TypedDict):
    duration_seconds: int
    ratelimit_seconds: int


class SendMessageConfigDict(TypedDict):
    message: str
    delete_after_seconds: int
    ping_user: NotRequired[bool]
    channel_id: NotRequired[int | None]


class AlertConfigDict(TypedDict):
    message: str
    channel_id: NotRequired[int | None]


type EffectDict = (
    EntryOptional[Literal["delete_message"], NoConfigDict]
    | EntryOptional[Literal["add_violation", "reset_violations"], ViolationEffectConfigDict]
    | EntryOptional[Literal["kick_user", "warn_user"], MessageConfigDict]
    | Entry[Literal["ban_user"], BanConfigDict]
    | Entry[Literal["mute_user"], MuteConfigDict]
    | Entry[Literal["timeout_user"], TimeoutConfigDict]
    | EntryOptional[Literal["set_nickname"], NicknameConfigDict]
    | Entry[Literal["delete_multiple_messages"], DeleteMessagesConfigDict]
    | Entry[Literal["give_role", "remove_role"], RoleConfigDict]
    | Entry[Literal["enable_slowmode"], SlowmodeConfigDict]
    | Entry[Literal["send_message"], SendMessageConfigDict]
    | Entry[Literal["send_alert"], AlertConfigDict]
)


class RuleDict(TypedDict):
    name: str
    trigger: TriggerDict
    conditions: list[ConditionDict]
    effects: list[EffectDict]
    enabled: bool
    priority: int


class AutomodConfig(TypedDict):
    word_denylist: list[str]
    word_allowlist: list[str]
    website_denylist: list[str]
    website_allowlist: list[str]

    custom_lists: dict[str, list[str]]  # list_name -> list of items
    rules: list[RuleDict]
    logs: list[str]
