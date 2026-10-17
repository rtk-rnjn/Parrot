from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bson import ObjectId
from discord.utils import MISSING
from pymongo import ReturnDocument

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin

if TYPE_CHECKING:
    from ..models import ModAction

MAX_MOD_ACTIONS_PER_GUILD = 1000


class _GuildModeratorMixin(DatabaseMixin):
    """Guild moderator configuration, backed by MongoDB and Redis."""

    async def get_moderator_role_ids(self, *, guild_id: int) -> list[int]:
        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        role_ids = await self.redis_client.smembers(key)
        if role_ids:
            return [int(role_id) for role_id in role_ids]

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "moderator_config": {"$exists": True}},
            {"moderator_config.moderator_role_ids": 1},
        )
        if guild_config is None:
            return []

        role_ids = guild_config["moderator_config"]["moderator_role_ids"]
        if role_ids:
            await self.redis_client.sadd(key, *role_ids)

        return role_ids

    async def get_moderator_logs_channel_id(self, *, guild_id: int) -> int | None:
        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_LOGS_CHANNEL_ID.format(guild_id=guild_id)
        channel_id = await self.redis_client.get(key)
        if channel_id:
            return int(channel_id)

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "moderator_config": {"$exists": True}},
            {"moderator_config.moderator_logs_channel_id": 1},
        )
        if guild_config is None:
            return None

        channel_id = guild_config["moderator_config"]["moderator_logs_channel_id"]
        if channel_id:
            await self.redis_client.set(key, channel_id)

        return channel_id

    async def edit_moderator_config(
        self,
        *,
        guild_id: int,
        moderator_role_ids: list[int] | None = MISSING,
        moderator_logs_channel_id: int | None = MISSING,
    ) -> None:
        update_data = {}
        if moderator_role_ids is not MISSING:
            update_data["moderator_config.moderator_role_ids"] = moderator_role_ids
            key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
            await self.redis_client.delete(key)

        if moderator_logs_channel_id is not MISSING:
            update_data["moderator_config.moderator_logs_channel_id"] = moderator_logs_channel_id
            key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_LOGS_CHANNEL_ID.format(guild_id=guild_id)
            await self.redis_client.delete(key)

        if update_data:
            await self.guilds_collection.update_one({"_id": guild_id}, {"$set": update_data}, upsert=True)

    async def add_moderator_role(self, *, guild_id: int, role_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$addToSet": {"moderator_config.moderator_role_ids": role_id}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        await self.redis_client.sadd(key, role_id)

    async def remove_moderator_role(self, *, guild_id: int, role_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"moderator_config.moderator_role_ids": role_id}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        await self.redis_client.srem(key, role_id)


class _GuildModActionMixin(DatabaseMixin):
    """Capped per-guild moderation history. Newest ``MAX_MOD_ACTIONS_PER_GUILD`` cases are kept."""

    async def ensure_mod_action_indexes(self) -> None:
        await self.mod_actions_collection.create_index([("guild_id", 1), ("case_id", -1)], unique=True)
        await self.mod_actions_collection.create_index([("guild_id", 1), ("target_ids", 1), ("case_id", -1)])

    async def _next_mod_case_id(self, *, guild_id: int) -> int:
        """Atomically allocate the next case number for a guild."""
        document = await self.guilds_collection.find_one_and_update(
            {"_id": guild_id},
            {"$inc": {"mod_case_counter": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"mod_case_counter": 1},
        )
        if TYPE_CHECKING:
            assert document is not None

        return document["mod_case_counter"]

    async def add_mod_action(
        self,
        *,
        guild_id: int,
        action: str,
        moderator_id: int | None,
        target_ids: list[int],
        reason: str | None,
        created_at: datetime,
        expires_at: datetime | None = None,
        metadata: dict[str, str] | None = None,
    ):
        """Store an action, assign its case number and prune the oldest cases."""
        case_id = await self._next_mod_case_id(guild_id=guild_id)

        document: ModAction = {
            "_id": ObjectId(),
            "guild_id": guild_id,
            "case_id": case_id,
            "action": action,
            "moderator_id": moderator_id,
            "target_ids": target_ids,
            "reason": reason,
            "created_at": created_at,
            "expires_at": expires_at,
            "metadata": metadata or {},
        }
        await self.mod_actions_collection.insert_one(document)

        # Case ids only ever grow, so "older than the newest N" is a cheap indexed range delete.
        await self.mod_actions_collection.delete_many(
            {"guild_id": guild_id, "case_id": {"$lte": case_id - MAX_MOD_ACTIONS_PER_GUILD}},
        )
        return document

    async def get_mod_action(self, *, guild_id: int, case_id: int):
        return await self.mod_actions_collection.find_one({"guild_id": guild_id, "case_id": case_id})

    async def get_mod_actions(
        self,
        *,
        guild_id: int,
        target_id: int | None = None,
        moderator_id: int | None = None,
        limit: int = 100,
    ):
        """Newest first. Optionally filter by target user and/or moderator."""
        query = {"guild_id": guild_id}
        if target_id is not None:
            query["target_ids"] = target_id
        if moderator_id is not None:
            query["moderator_id"] = moderator_id

        cursor = self.mod_actions_collection.find(query).sort("case_id", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def delete_mod_actions(self, *, guild_id: int) -> int:
        """Delete a guild's whole history (e.g. when the bot is removed from the guild)."""
        result = await self.mod_actions_collection.delete_many({"guild_id": guild_id})
        return result.deleted_count
