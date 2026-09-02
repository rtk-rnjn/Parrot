from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

import arrow
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildTagsMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_tag(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
        creator_id: int,
        aliases: list[str] | None,
        created_at: datetime,
        used_count: Mapping[str, int] | None,
    ):
        """Cache a tag in Redis."""
        await self.redis_client.sadd(RedisKeys.GUILD_TAG_NAMES.format(guild_id=guild_id), name)
        await self.redis_client.set(RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=name), content)
        await self.redis_client.set(RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=name), creator_id)
        await self.redis_client.set(RedisKeys.GUILD_TAG_CREATED_AT.format(guild_id=guild_id, tag_name=name), created_at.isoformat())
        if aliases:
            await self.redis_client.sadd(RedisKeys.GUILD_TAG_ALIASES.format(guild_id=guild_id, tag_name=name), *aliases)
            await self.redis_client.hset(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), mapping=dict.fromkeys(aliases, name))

        if used_count is not None:
            await self.redis_client.hset(RedisKeys.GUILD_TAG_USED_COUNT.format(guild_id=guild_id, tag_name=name), mapping=used_count)  # pyright: ignore[reportArgumentType]

    async def _invalidate_tag_cache(self, *, guild_id: int, name: str):
        """Invalidate a tag's cache in Redis."""
        await self.redis_client.srem(RedisKeys.GUILD_TAG_NAMES.format(guild_id=guild_id), name)
        await self.redis_client.delete(
            RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_CREATED_AT.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_ALIASES.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id),
            RedisKeys.GUILD_TAG_USED_COUNT.format(guild_id=guild_id, tag_name=name),
        )

    async def create_tag(
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
        creator_id: int,
        aliases: list[str] | None = None,
    ):
        """Create a new tag in the database and cache."""
        # Create the tag in the database
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {
                "$push": {
                    "tags": {
                        "name": name,
                        "content": content,
                        "creator_id": creator_id,
                        "aliases": aliases or [],
                        "created_at": arrow.utcnow().datetime,
                        "used_count": {},
                    },
                },
            },
            upsert=True,
        )
        await self._cache_tag(
            guild_id=guild_id,
            name=name,
            content=content,
            creator_id=creator_id,
            aliases=aliases,
            created_at=arrow.utcnow().datetime,
            used_count=None,
        )

    async def delete_tag(self, *, guild_id: int, name: str):
        """Delete a tag from the database and invalidate its cache."""
        # Delete the tag from the database
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"tags": {"name": name}}},
        )
        await self._invalidate_tag_cache(guild_id=guild_id, name=name)

    async def edit_tag_content(
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
    ):
        """Edit a tag's content in the database and update its cache."""
        # Update the tag in the database
        update_fields = {}
        update_fields["tags.$.content"] = content

        if update_fields:
            await self.guilds_collection.update_one(
                {"_id": guild_id, "tags.name": name},
                {"$set": update_fields},
            )

            await self.redis_client.set(
                RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=name),
                content,
            )

    async def increment_tag_used_count(self, *, guild_id: int, name_or_alias: str, author_id: int):
        """Increment a tag's used count in the database and update its cache."""
        # Increment the used count in the database
        await self.guilds_collection.update_one(
            {"_id": guild_id, "tags": {"$elemMatch": {"$or": [{"name": name_or_alias}, {"aliases": name_or_alias}]}}},
            {"$inc": {"tags.$.used_count." + str(author_id): 1}},
        )

        tag_name = await self.redis_client.hget(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), name_or_alias)
        if tag_name is None:
            tag_name = name_or_alias

        # Increment the used count in the cache
        await self.redis_client.hincrby(
            RedisKeys.GUILD_TAG_USED_COUNT.format(guild_id=guild_id, tag_name=tag_name),
            str(author_id),
        )

    async def transfer_tag_ownership(self, *, guild_id: int, name: str, new_creator_id: int):
        """Transfer ownership of a tag in the database and update its cache."""
        # Update the creator_id in the database
        await self.guilds_collection.update_one(
            {"_id": guild_id, "tags.name": name},
            {"$set": {"tags.$.creator_id": new_creator_id}},
        )
        # Update the cache
        await self.redis_client.set(
            RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=name),
            new_creator_id,
        )

    async def get_tag_content(self, *, guild_id: int, name_or_alias: str) -> str | None:
        alias_map_key = RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id)
        tag_name = await self.redis_client.hget(alias_map_key, name_or_alias)
        if tag_name is None:
            tag_name = name_or_alias

        content_key = RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=tag_name)
        content = await self.redis_client.get(content_key)
        if content is not None and isinstance(content, str):
            return content

        guild = await self.guilds_collection.find_one(
            {
                "_id": guild_id,
                "tags": {
                    "$elemMatch": {
                        "$or": [
                            {"name": name_or_alias},
                            {"aliases": name_or_alias},
                        ],
                    },
                },
            },
            {"tags.$": 1},
        )
        if guild is None:
            return None

        tag = guild["tags"][0]

        await self._cache_tag(
            guild_id=guild_id,
            name=tag["name"],
            content=tag["content"],
            creator_id=tag["creator_id"],
            aliases=tag.get("aliases", []),
            created_at=tag["created_at"],
            used_count=tag.get("used_count"),
        )

        return tag["content"]

    async def is_tag_present(self, *, guild_id: int, name_or_alias: str) -> bool:
        """Check if a tag exists in the database or cache."""
        alias_map_key = RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id)
        tag_name = await self.redis_client.hget(alias_map_key, name_or_alias)
        if tag_name is None:
            tag_name = name_or_alias

        tag_names_key = RedisKeys.GUILD_TAG_NAMES.format(guild_id=guild_id)
        exists_in_cache = await self.redis_client.sismember(tag_names_key, tag_name)  # pyright: ignore[reportArgumentType]
        if exists_in_cache:
            return True

        guild = await self.guilds_collection.find_one(
            {
                "_id": guild_id,
                "tags": {
                    "$elemMatch": {
                        "$or": [
                            {"name": name_or_alias},
                            {"aliases": name_or_alias},
                        ],
                    },
                },
            },
            {"tags.$": 1},
        )
        if guild is None:
            return False

        tag = guild["tags"][0]

        await self._cache_tag(
            guild_id=guild_id,
            name=tag["name"],
            content=tag["content"],
            creator_id=tag["creator_id"],
            aliases=tag.get("aliases", []),
            created_at=tag["created_at"],
            used_count=tag.get("used_count"),
        )

        return True
