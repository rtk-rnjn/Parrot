from __future__ import annotations

import asyncio
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.errors import CollectionInvalid
from redis.asyncio import Redis

from .models import CommandConfig, GiveawayEntry, GuildConfiguration, ModAction, StarboardEntry, UserConfiguration, UserViolation


class DatabaseMixin:
    """Base contract for database mixins.

    Mixins are stateless domain slices composed by ``DatabaseManager``. They
    may declare the typed collection and cache dependencies they use, expose
    readable public operations, and keep implementation helpers private.
    """

    redis_client: Redis
    mongo_client: AsyncMongoClient

    guilds_collection: AsyncCollection[GuildConfiguration]
    users_collection: AsyncCollection[UserConfiguration]

    giveaways_collection: AsyncCollection[GiveawayEntry]
    starboards_collection: AsyncCollection[StarboardEntry]
    user_violations_collection: AsyncCollection[UserViolation]

    mod_actions_collection: AsyncCollection[ModAction]

    commands_config_collection: AsyncCollection[CommandConfig]

    __slots__ = ()


class IndexesMixin(DatabaseMixin):
    """Creates every MongoDB index the bot relies on."""

    __slots__ = ()

    async def ensure_indexes(self) -> None:
        """Create all indexes. Safe to call on every startup (idempotent)."""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._ensure_guild_indexes())
            tg.create_task(self._ensure_giveaway_indexes())
            tg.create_task(self._ensure_starboard_indexes())
            tg.create_task(self._ensure_violation_indexes())
            tg.create_task(self._ensure_mod_action_indexes())
            tg.create_task(self._ensure_command_config_indexes())

    async def _ensure_guild_indexes(self) -> None:
        await self.guilds_collection.create_indexes(
            [
                IndexModel(
                    [("global_chat_config.channel_id", ASCENDING)],
                    name="global_chat_enabled",
                    partialFilterExpression={"global_chat_config.enabled": True},
                ),
                IndexModel(
                    [("telephone_config.channel_id", ASCENDING)],
                    name="telephone_enabled",
                    partialFilterExpression={"telephone_config.enabled": True},
                ),
            ]
        )

    async def _ensure_giveaway_indexes(self) -> None:
        await self.giveaways_collection.create_indexes(
            [
                IndexModel([("message_id", ASCENDING)], name="giveaway_message", unique=True),
                IndexModel(
                    [("guild_id", ASCENDING), ("ended", ASCENDING), ("ends_at", ASCENDING)],
                    name="giveaway_guild_state",
                ),
                IndexModel(
                    [("ends_at", ASCENDING)],
                    name="giveaway_due",
                    partialFilterExpression={"ended": False},
                ),
            ]
        )

    async def _ensure_starboard_indexes(self) -> None:
        await self.starboards_collection.create_indexes(
            [
                # Reaction on a source message: is it already on the board?
                IndexModel(
                    [("guild_id", ASCENDING), ("source_message_id", ASCENDING)],
                    name="star_source",
                    unique=True,
                ),
                IndexModel([("board_message_id", ASCENDING)], name="star_board_message", unique=True),
                IndexModel(
                    [("guild_id", ASCENDING), ("is_nsfw", ASCENDING), ("star_count", DESCENDING)],
                    name="star_leaderboard",
                ),
                IndexModel([("guild_id", ASCENDING), ("author_id", ASCENDING)], name="star_author"),
            ]
        )

    async def _ensure_violation_indexes(self) -> None:
        await self.user_violations_collection.create_indexes(
            [
                IndexModel(
                    [
                        ("guild_id", ASCENDING),
                        ("user_id", ASCENDING),
                        ("violation_name", ASCENDING),
                        ("issued_at", DESCENDING),
                    ],
                    name="violation_lookup",
                ),
                IndexModel([("expires_at", ASCENDING)], name="violation_ttl", expireAfterSeconds=0),
            ]
        )

    async def _ensure_mod_action_indexes(self) -> None:
        await self.mod_actions_collection.create_indexes(
            [
                IndexModel([("guild_id", ASCENDING), ("case_id", ASCENDING)], name="case_lookup", unique=True),
                IndexModel(
                    [("guild_id", ASCENDING), ("target_ids", ASCENDING), ("created_at", DESCENDING)],
                    name="case_by_target",
                ),
                IndexModel(
                    [("guild_id", ASCENDING), ("moderator_id", ASCENDING), ("created_at", DESCENDING)],
                    name="case_by_moderator",
                ),
                IndexModel(
                    [("expires_at", ASCENDING)],
                    name="case_expiry",
                    partialFilterExpression={"expires_at": {"$type": "date"}},
                ),
            ]
        )

    async def _ensure_command_config_indexes(self) -> None:
        await self.commands_config_collection.create_indexes(
            [
                IndexModel(
                    [("guild_id", ASCENDING), ("command_path", ASCENDING)],
                    name="command_guild_path",
                    unique=True,
                ),
            ]
        )


# Python ints that fit in 32 bits are stored as int32, larger ones as int64,
# so accept both. Discord snowflakes are always int64 in practice.
INT: dict[str, Any] = {"bsonType": ["int", "long"]}
STR: dict[str, Any] = {"bsonType": "string"}
BOOL: dict[str, Any] = {"bsonType": "bool"}
DATE: dict[str, Any] = {"bsonType": "date"}
OID: dict[str, Any] = {"bsonType": "objectId"}


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    types = schema["bsonType"]
    types = types if isinstance(types, list) else [types]
    return {**schema, "bsonType": [*types, "null"]}


def array_of(item: dict[str, Any]) -> dict[str, Any]:
    return {"bsonType": "array", "items": item}


def dict_of(value: dict[str, Any]) -> dict[str, Any]:
    """For dict[str, X] fields with dynamic keys."""
    return {"bsonType": "object", "additionalProperties": value}


def obj(properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    """Closed object: unknown fields are rejected, so typos fail loudly."""
    return {
        "bsonType": "object",
        "required": list(properties) if required is None else required,
        "properties": properties,
        "additionalProperties": False,
    }


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
    }
)

USER_VIOLATION = obj(
    {
        "_id": OID,
        "violation_name": STR,
        "user_id": INT,
        "guild_id": INT,
        "issued_at": DATE,
        "issued_by": nullable(INT),
        "expires_at": nullable(DATE),
        "metadata": dict_of(STR),
    }
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
        "entry_mode": {"enum": ["button", "reaction"]},
        "entrants": array_of(INT),
        "ended": BOOL,
        "created_at": DATE,
        "winner_ids": array_of(INT),
    }
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
    }
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
    }
)

# Guild document: validate the shape, not every nested detail. NotRequired
# fields (e.g. welcome_config.on_member_join_style) are listed in `properties`
# but left out of `required`.
GUILD = obj(
    {
        "_id": INT,
        "command_prefix": STR,
        "hub_channel_id": nullable(INT),
        "suggestion_channel_id": nullable(INT),
        "hub_channel_owners": dict_of(INT),
        "muted_members": array_of(INT),
        "mod_case_counter": INT,
        "afk_users": dict_of(STR),
        "leveling_data": dict_of(INT),
        "custom_commands_db": dict_of(STR),
        "custom_commands_logs": array_of(STR),
        "moderator_config": obj(
            {
                "moderator_role_ids": array_of(INT),
                "moderator_logs_channel_id": nullable(INT),
                "mute_role_id": nullable(INT),
            }
        ),
        "global_chat_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "webhook_uri": nullable(STR),
            }
        ),
        "telephone_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "blocked_servers": array_of(INT),
            }
        ),
        "ticket_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "bot_message_id": nullable(INT),
                "bot_channel_channel_id": nullable(INT),
            }
        ),
        "birthday_config": obj({"enabled": BOOL, "channel_id": nullable(INT)}),
        "leveling_config": obj(
            {
                "enabled": BOOL,
                "channel_id": nullable(INT),
                "level_roles": dict_of(INT),
            }
        ),
        "giveaway_config": obj(
            {
                "enabled": BOOL,
                "giveaway_channel_id": nullable(INT),
                "giveaway_role_id": nullable(INT),
            }
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
            }
        ),
        "automod": obj(
            {
                "word_allowlist": array_of(STR),
                "word_denylist": array_of(STR),
                "website_allowlist": array_of(STR),
                "website_denylist": array_of(STR),
                "custom_lists": dict_of(array_of(STR)),
                "logs": array_of(STR),
                # Items are only checked as objects here; see "Deep validation" below.
                "rules": array_of({"bsonType": "object"}),
            }
        ),
        # Add welcome_config, events, custom_commands and tags the same way.
        # Until you do, they are accepted by `additionalProperties: False`
        # only if listed, so list them (even loosely) or the guild insert fails:
        "welcome_config": {"bsonType": "object"},
        "events": {"bsonType": "object"},
        "custom_commands": array_of({"bsonType": "object"}),
        "tags": array_of({"bsonType": "object"}),
    }
)


class SchemaMixin(DatabaseMixin):
    """Applies server-side JSON Schema validators."""

    __slots__ = ()

    async def ensure_schemas(self, *, level: str = "strict", action: str = "error") -> None:
        async with asyncio.TaskGroup() as tg:
            for collection, schema in (
                (self.guilds_collection, GUILD),
                (self.mod_actions_collection, MOD_ACTION),
                (self.user_violations_collection, USER_VIOLATION),
                (self.giveaways_collection, GIVEAWAY),
                (self.starboards_collection, STARBOARD_ENTRY),
                (self.commands_config_collection, COMMAND_CONFIG),
            ):
                tg.create_task(self._apply_validator(collection, schema, level, action))

    @staticmethod
    async def _apply_validator(collection: AsyncCollection[Any], schema: dict[str, Any], level: str, action: str) -> None:
        validator = {"$jsonSchema": schema}
        db = collection.database
        try:
            # New collection: create it with the validator attached.
            await db.create_collection(
                collection.name,
                validator=validator,
                validationLevel=level,
                validationAction=action,
            )
        except CollectionInvalid:
            # Already exists: update its validator in place.
            await db.command(
                {
                    "collMod": collection.name,
                    "validator": validator,
                    "validationLevel": level,
                    "validationAction": action,
                }
            )
