from __future__ import annotations

from typing import Literal

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildAutomodMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def create_automod_rule(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        rule_name: str,
        triggers: dict,
        conditions: list[dict],
        effects: list[dict],
        priority: int = 0,
        condition_match_mode: Literal["any", "all"] = "all",
    ):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {
                "$set": {
                    f"automod.{rule_name}": {
                        "triggers": triggers,
                        "conditions": conditions,
                        "effects": effects,
                        "priority": priority,
                        "condition_match_mode": condition_match_mode,
                    },
                },
            },
            upsert=True,
        )

    async def delete_automod_rule(self, *, guild_id: int, rule_name: str):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$unset": {f"automod.{rule_name}": ""}},
        )

    async def disable_automod_rule(self, *, guild_id: int, rule_name: str):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"automod.{rule_name}.enabled": False}},
        )

    async def enable_automod_rule(self, *, guild_id: int, rule_name: str):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"automod.{rule_name}.enabled": True}},
        )

    async def set_automod_rule_priority(self, *, guild_id: int, rule_name: str, priority: int):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"automod.{rule_name}.priority": priority}},
        )

    async def set_automod_rule_condition_match_mode(self, *, guild_id: int, rule_name: str, match_mode: Literal["any", "all"]):
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"automod.{rule_name}.condition_match_mode": match_mode}},
        )

    async def get_automod_rule(self, *, guild_id: int, rule_name: str) -> dict | None:
        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, f"automod.{rule_name}": {"$exists": True}},
            {f"automod.{rule_name}": 1},
        )
        if guild_config is None:
            return None

        return guild_config["automod"][rule_name]

    async def get_all_automod_rules(self, *, guild_id: int) -> dict[str, dict]:
        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "automod": {"$exists": True}},
            {"automod": 1},
        )
        if guild_config is None:
            return {}

        return guild_config["automod"]
