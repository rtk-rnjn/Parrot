from __future__ import annotations

import asyncio

from pymongo import ASCENDING, DESCENDING, IndexModel

from .base import DatabaseMixin


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
            tg.create_task(self._ensure_tag_indexes())

    async def _ensure_tag_indexes(self) -> None:
        await self.tags_collection.create_indexes(
            [
                IndexModel([("guild_id", ASCENDING), ("name", ASCENDING)], name="tag_name", unique=True),
                IndexModel([("guild_id", ASCENDING), ("aliases", ASCENDING)], name="tag_alias"),
                IndexModel([("guild_id", ASCENDING), ("creator_id", ASCENDING)], name="tag_creator"),
            ]
        )

    async def _ensure_guild_indexes(self) -> None:
        await self.guilds_collection.create_indexes(
            [
                IndexModel(
                    [("global_chat_config.channel_id", ASCENDING)],
                    name="global_chat_enabled",
                    partialFilterExpression={"global_chat_config.enabled": True},
                ),
                IndexModel(
                    [("global_chat_config.webhook_uri", ASCENDING)],
                    name="global_chat_webhook",
                    partialFilterExpression={
                        "global_chat_config.enabled": True,
                        "global_chat_config.webhook_uri": {"$exists": True, "$ne": None},
                    },
                ),
                IndexModel(
                    [("telephone_config.channel_id", ASCENDING)],
                    name="telephone_enabled",
                    partialFilterExpression={"telephone_config.enabled": True},
                ),
                IndexModel(
                    [("leveling_config.channel_id", ASCENDING)],
                    name="leveling_enabled",
                    partialFilterExpression={"leveling_config.enabled": True},
                ),
                IndexModel(
                    [("giveaway_config.giveaway_channel_id", ASCENDING)],
                    name="giveaway_enabled",
                    partialFilterExpression={"giveaway_config.enabled": True},
                ),
                IndexModel(
                    [("welcome_config.on_member_join_channel_id", ASCENDING)],
                    name="welcome_join_channel",
                    partialFilterExpression={"welcome_config.enabled": True},
                ),
                IndexModel(
                    [("welcome_config.on_member_leave_channel_id", ASCENDING)],
                    name="welcome_leave_channel",
                    partialFilterExpression={"welcome_config.enabled": True},
                ),
                IndexModel(
                    [("starboard_config.channel_id", ASCENDING)],
                    name="starboard_enabled",
                    partialFilterExpression={"starboard_config.enabled": True},
                ),
                IndexModel(
                    [("birthday_config.channel_id", ASCENDING)],
                    name="birthday_enabled",
                    partialFilterExpression={"birthday_config.enabled": True},
                ),
                IndexModel(
                    [("ticket_config.channel_id", ASCENDING)],
                    name="ticket_enabled",
                    partialFilterExpression={"ticket_config.enabled": True},
                ),
                IndexModel(
                    [("ticket_config.bot_message_id", ASCENDING)],
                    name="ticket_bot_message",
                    partialFilterExpression={"ticket_config.bot_message_id": {"$exists": True, "$ne": None}},
                ),
                IndexModel([("hub_channel_id", ASCENDING)], name="guild_hub_channel"),
                IndexModel([("suggestion_channel_id", ASCENDING)], name="guild_suggestion_channel"),
                IndexModel(
                    [("muted_members", ASCENDING)],
                    name="guild_muted_members",
                    partialFilterExpression={"muted_members": {"$exists": True, "$ne": []}},
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
