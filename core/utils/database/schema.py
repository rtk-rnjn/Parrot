from __future__ import annotations

import asyncio
from collections.abc import Collection
from enum import Enum
from typing import Any, Literal, get_args

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import CollectionInvalid

from .base import DatabaseMixin
from .models import Events, TodoPriority, TodoStatus
from .models.automod import (
    AllCapsTrigger,
    BanEffect,
    CategoriesCondition,
    ChannelsCondition,
    DeleteMessageEffect,
    DeleteMessagesEffect,
    DurationCondition,
    LengthTrigger,
    ListTrigger,
    MentionsTrigger,
    MessageEffect,
    MuteEffect,
    NicknameEffect,
    NoConfigCondition,
    NoConfigTrigger,
    RegexTrigger,
    RoleEffect,
    RolesCondition,
    SendAlertEffect,
    SendMessageEffect,
    SlowmodeEffect,
    TimeoutEffect,
    TimeWindowTrigger,
    ViolationEffect,
    ViolationsTrigger,
)
from .models.community import GiveawayEntryMode, WelcomeStyle
from .schema_type import Schema

type ValidationLevel = Literal["off", "strict", "moderate"]
type ValidationAction = Literal["error", "warn"]

INT: Schema = {"bsonType": ["int", "long"]}
STR: Schema = {"bsonType": "string"}
BOOL: Schema = {"bsonType": "bool"}
DATE: Schema = {"bsonType": "date"}
OID: Schema = {"bsonType": "objectId"}
ANY_OBJECT: Schema = {"bsonType": "object"}


def desc(schema: Schema, description: str, *, title: str | None = None) -> Schema:
    """Return a copy of ``schema`` with a description (and optionally a title).

    Use it on the shared constants, e.g. ``desc(INT, "Discord guild ID")``;
    the constants themselves are never mutated.
    """
    out: Schema = {**schema, "description": description}
    if title is not None:
        out["title"] = title
    return out


def nullable(schema: Schema) -> Schema:
    """Accept null in addition to whatever ``schema`` accepts.

    ``title`` / ``description`` survive: they are kept on the schema when it has
    a ``bsonType``, and on the ``anyOf`` wrapper otherwise.
    """
    if "bsonType" not in schema:
        return {"anyOf": [schema, {"bsonType": "null"}]}
    types = schema["bsonType"]
    types = types if isinstance(types, list) else [types]
    return {**schema, "bsonType": [*types, "null"]}


def array_of(item: Schema, *, description: str | None = None) -> Schema:
    schema: Schema = {"bsonType": "array", "items": item}
    if description is not None:
        schema["description"] = description
    return schema


def dict_of(value: Schema, *, description: str | None = None) -> Schema:
    """For dict[str, X] fields with dynamic keys."""
    schema: Schema = {"bsonType": "object", "additionalProperties": value}
    if description is not None:
        schema["description"] = description
    return schema


def literal_of(alias: Any) -> Schema:
    """``Literal["a", "b"]`` -> ``{"enum": ["a", "b"]}``."""
    return {"enum": list(get_args(alias))}


def enum_of(cls: type[Enum]) -> Schema:
    return {"enum": [member.value for member in cls]}


def any_of(*members: Schema, title: str, description: str) -> Schema:
    return {"title": title, "description": description, "anyOf": list(members)}


def obj(
    properties: dict[str, Schema],
    *,
    optional: Collection[str] = (),
    title: str | None = None,
    description: str | None = None,
) -> Schema:
    """Closed object: unknown fields are rejected, so typos fail loudly.

    Every property is required except those named in ``optional`` (the
    NotRequired keys of the matching TypedDict). MongoDB rejects an empty
    ``required`` array, so the key is omitted when nothing is required.

    ``title`` / ``description`` are not enforced by MongoDB, but (5.0+) the
    ``description`` of a failing property is echoed back in the validation
    error details, which makes "Document failed validation" much easier to read.
    """
    unknown = set(optional) - set(properties)
    if unknown:
        msg = f"optional keys not in properties: {sorted(unknown)}"
        raise ValueError(msg)

    schema: Schema = {"bsonType": "object"}
    if title is not None:
        schema["title"] = title
    if description is not None:
        schema["description"] = description
    schema["properties"] = properties
    schema["additionalProperties"] = False
    if required := [key for key in properties if key not in optional]:
        schema["required"] = required
    return schema


def entry(kinds: Any, config: Schema, *, optional_config: bool = False) -> Schema:
    """One member of an Entry[...] / EntryOptional[...] union.

    The title is derived from the Literal's values, e.g. ``"all_caps"``.
    """
    return obj(
        {"type": literal_of(kinds), "config": config},
        optional=["config"] if optional_config else (),
        title=" / ".join(map(str, get_args(kinds))),
    )


NO_CONFIG = obj({}, title="No config")

# trigger configs
ALL_CAPS_CONFIG = obj({"min_count": INT, "percentage": INT}, title="All caps trigger config")
COUNT_CONFIG = obj({"count": INT}, title="Count trigger config")
TIME_WINDOW_CONFIG = obj({"count": INT, "within_minutes": INT}, title="Time window trigger config")
LIST_CONFIG = obj({"list": nullable(STR)}, optional=["list"], title="List trigger config")
REGEX_CONFIG = obj({"regex": STR}, title="Regex trigger config")
LENGTH_CONFIG = obj({"length": INT}, title="Length trigger config")
VIOLATION_TRIGGER_CONFIG = obj(
    {"violation_name": STR, "number_of_violations": INT, "within_minutes": INT},
    title="Violations trigger config",
)

# condition configs
ROLES_CONFIG = obj(
    {"roles": array_of(INT), "require_all": BOOL},
    optional=["require_all"],
    title="Roles condition config",
)
CHANNELS_CONFIG = obj({"channels": array_of(INT)}, title="Channels condition config")
CATEGORIES_CONFIG = obj({"categories": array_of(INT)}, title="Categories condition config")
DURATION_CONFIG = obj({"minutes": INT}, title="Duration condition config")

# effect configs
VIOLATION_EFFECT_CONFIG = obj(
    {"name": nullable(STR)},
    optional=["name"],
    title="Violation effect config",
)
MESSAGE_CONFIG = obj({"message": nullable(STR)}, optional=["message"], title="Message effect config")
BAN_CONFIG = obj(
    {"duration_minutes": INT, "delete_days": INT, "message": nullable(STR)},
    optional=["message"],
    title="Ban effect config",
)
MUTE_CONFIG = obj(
    {"duration_minutes": INT, "message": nullable(STR)},
    optional=["message"],
    title="Mute effect config",
)
TIMEOUT_CONFIG = obj(
    {"duration_minutes": INT, "message": nullable(STR)},
    optional=["message"],
    title="Timeout effect config",
)
NICKNAME_CONFIG = obj({"nickname": nullable(STR)}, optional=["nickname"], title="Nickname effect config")
DELETE_MESSAGES_CONFIG = obj(
    {"count": INT, "max_age_seconds": INT},
    title="Delete messages effect config",
)
ROLE_CONFIG = obj(
    {"duration_seconds": INT, "role_id": nullable(INT)},
    optional=["role_id"],
    title="Role effect config",
)
SLOWMODE_CONFIG = obj(
    {"duration_seconds": INT, "ratelimit_seconds": INT},
    title="Slowmode effect config",
)
SEND_MESSAGE_CONFIG = obj(
    {
        "message": STR,
        "delete_after_seconds": INT,
        "ping_user": BOOL,
        "channel_id": nullable(INT),
    },
    optional=["ping_user", "channel_id"],
    title="Send message effect config",
)
ALERT_CONFIG = obj(
    {"message": STR, "channel_id": nullable(INT)},
    optional=["channel_id"],
    title="Send alert effect config",
)

TRIGGER = any_of(
    entry(NoConfigTrigger, NO_CONFIG, optional_config=True),
    entry(AllCapsTrigger, ALL_CAPS_CONFIG),
    entry(MentionsTrigger, COUNT_CONFIG),
    entry(ViolationsTrigger, VIOLATION_TRIGGER_CONFIG),
    entry(ListTrigger, LIST_CONFIG, optional_config=True),
    entry(RegexTrigger, REGEX_CONFIG),
    entry(TimeWindowTrigger, TIME_WINDOW_CONFIG),
    entry(LengthTrigger, LENGTH_CONFIG),
    title="Automod trigger",
    description="What makes an automod rule fire. One of the trigger kinds below.",
)

CONDITION = any_of(
    entry(NoConfigCondition, NO_CONFIG, optional_config=True),
    entry(RolesCondition, ROLES_CONFIG),
    entry(ChannelsCondition, CHANNELS_CONFIG),
    entry(CategoriesCondition, CATEGORIES_CONFIG),
    entry(DurationCondition, DURATION_CONFIG),
    title="Automod condition",
    description="An extra check that must pass before a rule's effects run.",
)

EFFECT = any_of(
    entry(DeleteMessageEffect, NO_CONFIG, optional_config=True),
    entry(ViolationEffect, VIOLATION_EFFECT_CONFIG, optional_config=True),
    entry(MessageEffect, MESSAGE_CONFIG, optional_config=True),
    entry(BanEffect, BAN_CONFIG),
    entry(MuteEffect, MUTE_CONFIG),
    entry(TimeoutEffect, TIMEOUT_CONFIG),
    entry(NicknameEffect, NICKNAME_CONFIG, optional_config=True),
    entry(DeleteMessagesEffect, DELETE_MESSAGES_CONFIG),
    entry(RoleEffect, ROLE_CONFIG),
    entry(SlowmodeEffect, SLOWMODE_CONFIG),
    entry(SendMessageEffect, SEND_MESSAGE_CONFIG),
    entry(SendAlertEffect, ALERT_CONFIG),
    title="Automod effect",
    description="An action taken when a rule fires and its conditions pass.",
)

RULE = obj(
    {
        "name": STR,
        "trigger": TRIGGER,
        "conditions": array_of(CONDITION),
        "effects": array_of(EFFECT),
        "enabled": BOOL,
        "priority": INT,
    },
    title="Automod rule",
    description="A trigger, optional conditions, and the effects to apply.",
)

AUTOMOD = obj(
    {
        "word_allowlist": array_of(STR),
        "word_denylist": array_of(STR),
        "website_allowlist": array_of(STR),
        "website_denylist": array_of(STR),
        "custom_lists": dict_of(array_of(STR), description="Custom string lists, keyed by name."),
        "logs": array_of(STR),
        "rules": array_of(RULE),
    },
    title="Automod config",
    description="Per-guild automod word/website lists and rules.",
)

WELCOME_STYLE = literal_of(WelcomeStyle)
WELCOME_CONFIG = obj(
    {
        "enabled": BOOL,
        "on_member_join_message": nullable(STR),
        "on_member_join_channel_id": nullable(INT),
        "on_member_join_role_id": nullable(INT),
        "on_member_leave_message": nullable(STR),
        "on_member_leave_channel_id": nullable(INT),
        # NotRequired in the TypedDict
        "on_member_join_style": WELCOME_STYLE,
        "on_member_leave_style": WELCOME_STYLE,
        "accent_color": nullable(INT),
        "banner_url": nullable(STR),
    },
    optional=["on_member_join_style", "on_member_leave_style", "accent_color", "banner_url"],
    title="Welcome config",
)

EVENT_CONFIG = obj(
    {"enabled": BOOL, "webhook_uri": nullable(STR)},
    title="Event config",
    description="Whether an event is logged and the webhook it is sent to (null = none).",
)
EVENTS = obj(
    dict.fromkeys(Events.__annotations__, EVENT_CONFIG),
    title="Events",
    description="One config per logged Discord event. Every event key must be present.",
)

MOD_ACTION = obj(
    {
        "_id": OID,
        "guild_id": INT,
        "case_id": INT,
        "action": STR,
        "moderator_id": nullable(INT),
        "target_ids": array_of(INT),
        "reason": nullable(STR),
        "created_at": DATE,
        "expires_at": nullable(DATE),
        "metadata": dict_of(STR),
    },
    title="Moderation action",
    description="One moderation case (ban, mute, warn, ...) within a guild.",
)

USER_VIOLATION = obj(
    {
        "_id": OID,
        "violation_name": desc(STR, 'Name of the violation; "default" is the default name.'),
        "user_id": INT,
        "guild_id": INT,
        "issued_at": DATE,
        "issued_by": desc(nullable(INT), "Moderator ID; null if issued by automod."),
        "expires_at": nullable(DATE),
        "metadata": dict_of(
            STR,
            description="Optional metadata for the violation, e.g. rule name, reason.",
        ),
    },
    title="User violation",
    description="A violation issued to a user in a guild.",
)

GIVEAWAY = obj(
    {
        "_id": OID,
        "guild_id": INT,
        "channel_id": INT,
        "message_id": INT,
        "host_id": INT,
        "prize": STR,
        "winners": INT,
        "ends_at": DATE,
        "entry_mode": literal_of(GiveawayEntryMode),
        "entrants": array_of(INT),
        "ended": BOOL,
        "created_at": DATE,
        "winner_ids": array_of(INT),
    },
    title="Giveaway",
)

STARBOARD_ENTRY = obj(
    {
        "_id": OID,
        "guild_id": INT,
        "source_message_id": INT,
        "board_message_id": INT,
        "source_channel_id": INT,
        "author_id": INT,
        "is_nsfw": BOOL,
        "star_count": INT,
        "created_at": DATE,
        "users": array_of(INT),
    },
    title="Starboard entry",
)

COMMAND_CONFIG = obj(
    {
        "_id": OID,
        "command_path": STR,
        "guild_id": INT,
        "enabled": BOOL,
        "ignored_roles": array_of(INT),
        "ignored_channels": array_of(INT),
        "allowed_roles": array_of(INT),
        "allowed_channels": array_of(INT),
    },
    title="Command config",
    description="Per-guild enable/ignore/allow settings for one command.",
)

TAG = obj(
    {
        "_id": OID,
        "guild_id": INT,
        "name": STR,
        "content": STR,
        "nsfw": BOOL,
        "creator_id": INT,
        "created_at": DATE,
        "aliases": array_of(STR),
        "used_count": dict_of(INT),
    },
    title="Tag",
)

CUSTOM_COMMAND = obj(
    {
        "_id": OID,
        "guild_id": INT,
        "name": STR,
        "response": STR,
        "ignored_roles": array_of(INT),
        "ignored_channels": array_of(INT),
        "enabled": BOOL,
        "require_prefix": BOOL,
    },
    optional=["require_prefix"],
    title="Custom command",
)

GUILD = obj(
    {
        "_id": desc(INT, "Discord guild ID."),
        "command_prefix": STR,
        "hub_channel_id": nullable(INT),
        "suggestion_channel_id": nullable(INT),
        "hub_channel_owners": dict_of(INT, description="channel_id -> owner_id"),
        "muted_members": array_of(INT),
        "mod_case_counter": desc(INT, "Counter used to assign moderation case IDs."),
        "afk_users": dict_of(STR),
        "leveling_data": dict_of(INT, description="user_id -> xp"),
        "custom_commands_db": dict_of(STR),
        "custom_commands_logs": array_of(STR),
        "moderator_config": obj(
            {
                "moderator_role_ids": array_of(INT),
                "moderator_logs_channel_id": nullable(INT),
                "mute_role_id": nullable(INT),
            },
            title="Moderator config",
        ),
        "automod": AUTOMOD,
        "welcome_config": WELCOME_CONFIG,
        "events": EVENTS,
        "global_chat_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "webhook_uri": nullable(STR),
            },
            title="Global chat config",
        ),
        "telephone_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "blocked_servers": array_of(INT),
            },
            title="Telephone config",
        ),
        "ticket_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "bot_message_id": nullable(INT),
                "bot_channel_channel_id": nullable(INT),
            },
            title="Ticket config",
        ),
        "birthday_config": obj(
            {"enabled": BOOL, "channel_id": nullable(INT)},
            title="Birthday config",
        ),
        "leveling_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "level_roles": dict_of(INT),
            },
            title="Leveling config",
        ),
        "giveaway_config": obj(
            {
                "enabled": BOOL,
                "giveaway_channel_id": nullable(INT),
                "giveaway_role_id": nullable(INT),
            },
            title="Giveaway config",
        ),
        "starboard_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "threshold": INT,
                "emoji": STR,
                "self_star": BOOL,
                "allow_nsfw": BOOL,
                "max_age_days": INT,
                "ignored_channels": array_of(INT),
                "ignored_roles": array_of(INT),
                "ignored_users": array_of(INT),
            },
            title="Starboard config",
        ),
    },
    title="Guild configuration",
    description="All per-guild settings, one document per Discord guild.",
)

TODO_ITEM = obj(
    {
        "id": OID,
        "title": STR,
        "notes": nullable(STR),
        "due": nullable(DATE),
        "status": enum_of(TodoStatus),
        "priority": enum_of(TodoPriority),
        "created_at": DATE,
        "completed_at": nullable(DATE),
    },
    title="Todo item",
)
HIGHLIGHT = obj({"guild_id": INT, "words": array_of(STR)}, title="Highlight")
SUPERCELL_ACCOUNT = obj(
    {"tag": STR, "verified": BOOL, "linked_at": DATE},
    title="Supercell account",
)
CHESS_ACCOUNT = obj(
    {"username": STR, "verified": BOOL, "code": nullable(STR), "linked_at": DATE},
    title="Chess.com account",
)
# total=False in the TypedDict: every key is optional
WEATHER_SETTINGS = obj(
    {"location": ANY_OBJECT, "units": STR, "lang": STR},
    optional=["location", "units", "lang"],
    title="Weather settings",
)

USER_CONFIGURATION = obj(
    {
        "_id": desc(INT, "Discord user ID."),
        "birthday": STR,
        "timezone": STR,
        "todo_items": array_of(TODO_ITEM),
        "highlights": array_of(HIGHLIGHT),
        "highlight_ignored_users": array_of(INT),
        "supercell": obj(
            {
                "clash_royale": nullable(SUPERCELL_ACCOUNT),
                "clash_of_clans": nullable(SUPERCELL_ACCOUNT),
            },
            title="Supercell accounts",
        ),
        "chess_com": nullable(CHESS_ACCOUNT),
        "weather": WEATHER_SETTINGS,
    },
    title="User configuration",
    description="Per-user settings, one document per Discord user.",
)


class SchemaMixin(DatabaseMixin):
    """Applies server-side JSON Schema validators."""

    __slots__ = ()

    async def ensure_schemas(
        self,
        *,
        level: ValidationLevel = "strict",
        action: ValidationAction = "error",
    ) -> None:
        targets = (
            (self.guilds_collection, GUILD),
            (self.users_collection, USER_CONFIGURATION),
            (self.mod_actions_collection, MOD_ACTION),
            (self.user_violations_collection, USER_VIOLATION),
            (self.giveaways_collection, GIVEAWAY),
            (self.starboards_collection, STARBOARD_ENTRY),
            (self.commands_config_collection, COMMAND_CONFIG),
            (self.custom_commands_collection, CUSTOM_COMMAND),
            (self.tags_collection, TAG),
        )
        async with asyncio.TaskGroup() as task_group:
            for collection, schema in targets:
                task_group.create_task(self._apply_validator(collection, schema, level, action))

    @staticmethod
    async def _apply_validator(
        collection: AsyncCollection[Any],
        schema: Schema,
        level: ValidationLevel,
        action: ValidationAction,
    ) -> None:
        validator = {"$jsonSchema": schema}
        db = collection.database
        try:
            await db.create_collection(
                collection.name,
                validator=validator,
                validationLevel=level,
                validationAction=action,
            )
        except CollectionInvalid:
            await db.command(
                {
                    "collMod": collection.name,
                    "validator": validator,
                    "validationLevel": level,
                    "validationAction": action,
                }
            )
