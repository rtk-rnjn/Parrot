from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from ._common import NoConfigDict


class Entry[K: str, C](TypedDict):
    type: K
    config: C


class EntryOptional[K: str, C](TypedDict):
    type: K
    config: NotRequired[C]


NoConfigTrigger = Literal[
    "any_link",
    "server_invites",
    "join_username_invite",
    "new_member",
    "message_without_attachments",
    "message_with_attachments",
    "flagged_scam_links",
    "discord_automod",
]
AllCapsTrigger = Literal["all_caps"]
MentionsTrigger = Literal["message_mentions"]
ViolationsTrigger = Literal["violations"]
ListTrigger = Literal[
    "word_denylist",
    "word_allowlist",
    "website_denylist",
    "website_allowlist",
    "nickname_word_allowlist",
    "nickname_word_denylist",
    "join_username_word_allowlist",
    "join_username_word_denylist",
]
RegexTrigger = Literal[
    "message_regex",
    "message_not_regex",
    "nickname_regex",
    "nickname_not_regex",
    "join_username_regex",
    "join_username_not_regex",
]
TimeWindowTrigger = Literal[
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
]
LengthTrigger = Literal["message_length_gt", "message_length_lt"]

NoConfigCondition = Literal[
    "ignore_bots",
    "only_bots",
    "new_message",
    "edited_message",
    "active_in_threads",
    "ignore_threads",
    "ignore_forwards",
    "only_forwards",
]
RolesCondition = Literal["ignored_roles", "required_roles"]
ChannelsCondition = Literal["ignored_channels", "active_channels"]
CategoriesCondition = Literal["ignored_categories", "active_categories"]
DurationCondition = Literal[
    "account_age_above",
    "account_age_below",
    "member_duration_above",
    "member_duration_below",
]

DeleteMessageEffect = Literal["delete_message"]
ViolationEffect = Literal["add_violation", "reset_violations"]
MessageEffect = Literal["kick_user", "warn_user"]
BanEffect = Literal["ban_user"]
MuteEffect = Literal["mute_user"]
TimeoutEffect = Literal["timeout_user"]
NicknameEffect = Literal["set_nickname"]
DeleteMessagesEffect = Literal["delete_multiple_messages"]
RoleEffect = Literal["give_role", "remove_role"]
SlowmodeEffect = Literal["enable_slowmode"]
SendMessageEffect = Literal["send_message"]
SendAlertEffect = Literal["send_alert"]


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
    EntryOptional[NoConfigTrigger, NoConfigDict]
    | Entry[AllCapsTrigger, AllCapsConfigDict]
    | Entry[MentionsTrigger, CountConfigDict]
    | Entry[ViolationsTrigger, ViolationTriggerConfigDict]
    | EntryOptional[ListTrigger, ListConfigDict]
    | Entry[RegexTrigger, RegexConfigDict]
    | Entry[TimeWindowTrigger, TimeWindowConfigDict]
    | Entry[LengthTrigger, LengthConfigDict]
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
    EntryOptional[NoConfigCondition, NoConfigDict]
    | Entry[RolesCondition, RolesConfigDict]
    | Entry[ChannelsCondition, ChannelsConfigDict]
    | Entry[CategoriesCondition, CategoriesConfigDict]
    | Entry[DurationCondition, DurationConfigDict]
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
    EntryOptional[DeleteMessageEffect, NoConfigDict]
    | EntryOptional[ViolationEffect, ViolationEffectConfigDict]
    | EntryOptional[MessageEffect, MessageConfigDict]
    | Entry[BanEffect, BanConfigDict]
    | Entry[MuteEffect, MuteConfigDict]
    | Entry[TimeoutEffect, TimeoutConfigDict]
    | EntryOptional[NicknameEffect, NicknameConfigDict]
    | Entry[DeleteMessagesEffect, DeleteMessagesConfigDict]
    | Entry[RoleEffect, RoleConfigDict]
    | Entry[SlowmodeEffect, SlowmodeConfigDict]
    | Entry[SendMessageEffect, SendMessageConfigDict]
    | Entry[SendAlertEffect, AlertConfigDict]
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
