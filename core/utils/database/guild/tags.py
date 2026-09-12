from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

import arrow
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration, Tag, TagUserUsage, TopTagUsage, _TagUserUsageRow, _TopTagUsageRow


class _GuildTagsMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_tag(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
        nsfw: bool,
        creator_id: int,
        aliases: list[str] | None,
        created_at: datetime,
        used_count: Mapping[str, int] | None,
    ):
        """Cache a tag in Redis."""
        await self.redis_client.sadd(RedisKeys.GUILD_TAG_NAMES.format(guild_id=guild_id), name)
        await self.redis_client.set(RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=name), content)
        await self.redis_client.set(RedisKeys.GUILD_TAG_NSFW.format(guild_id=guild_id, tag_name=name), int(nsfw))
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
            RedisKeys.GUILD_TAG_NSFW.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_CREATED_AT.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_ALIASES.format(guild_id=guild_id, tag_name=name),
            RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id),
            RedisKeys.GUILD_TAG_USED_COUNT.format(guild_id=guild_id, tag_name=name),
        )

    async def create_tag(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
        creator_id: int,
        nsfw: bool = False,
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
                        "nsfw": nsfw,
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
            nsfw=nsfw,
            creator_id=creator_id,
            aliases=aliases,
            created_at=arrow.utcnow().datetime,
            used_count=None,
        )

    async def delete_tag(self, *, guild_id: int, name: str, creator_id: int, is_admin: bool = False) -> bool:
        """Delete a tag from the database and invalidate its cache."""
        # Delete the tag from the database
        tag_filter = {"name": name} if is_admin else {"name": name, "creator_id": creator_id}
        updated = await self.guilds_collection.update_one(
            {"_id": guild_id, "tags": {"$elemMatch": tag_filter}},
            {
                "$pull": {"tags": tag_filter},
            },
        )
        if updated.modified_count > 0:
            await self._invalidate_tag_cache(guild_id=guild_id, name=name)
        return updated.modified_count > 0

    async def get_tag_name(self, *, guild_id: int, name_or_alias: str) -> str | None:
        """Get a tag's canonical name by its name or alias."""
        alias_map_key = RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id)
        tag_name = await self.redis_client.hget(alias_map_key, name_or_alias)
        if tag_name is not None:
            return tag_name.decode() if isinstance(tag_name, bytes) else tag_name

        guild = await self.guilds_collection.find_one(
            {
                "_id": guild_id,
                "tags": {
                    "$elemMatch": {
                        "$or": [{"name": name_or_alias}, {"aliases": name_or_alias}],
                    },
                },
            },
            {"tags.$": 1},
        )
        if guild is None:
            return None
        tag = guild["tags"][0]
        await self.redis_client.sadd(RedisKeys.GUILD_TAG_NAMES.format(guild_id=guild_id), tag["name"])
        aliases = tag.get("aliases", [])
        if aliases:
            await self.redis_client.hset(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), mapping=dict.fromkeys(aliases, tag["name"]))
        return tag["name"]

    async def get_tag_owner_id(self, *, guild_id: int, name_or_alias: str) -> int | None:
        """Get a tag owner's ID without loading the tag content."""
        tag_name = await self.get_tag_name(guild_id=guild_id, name_or_alias=name_or_alias)
        if tag_name is None:
            return None

        cached = await self.redis_client.get(RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=tag_name))
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "tags.name": tag_name},
            {"tags.$": 1},
        )
        if guild is None:
            return None

        creator_id = guild["tags"][0]["creator_id"]
        await self.redis_client.set(RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=tag_name), creator_id)
        return creator_id

    async def is_tag_nsfw(self, *, guild_id: int, name_or_alias: str) -> bool:
        """Return whether a tag is marked as NSFW."""
        tag_name = await self.redis_client.hget(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), name_or_alias)
        if tag_name is None:
            tag_name = name_or_alias
        elif isinstance(tag_name, bytes):
            tag_name = tag_name.decode()

        cached = await self.redis_client.get(RedisKeys.GUILD_TAG_NSFW.format(guild_id=guild_id, tag_name=tag_name))
        if cached is not None:
            return cached in {"1", b"1", True}

        guild = await self.guilds_collection.find_one(
            {
                "_id": guild_id,
                "tags": {
                    "$elemMatch": {
                        "$or": [{"name": name_or_alias}, {"aliases": name_or_alias}],
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
            nsfw=tag.get("nsfw", False),
            aliases=tag.get("aliases", []),
            created_at=tag["created_at"],
            used_count=tag.get("used_count"),
        )
        return tag.get("nsfw", False)

    async def mark_tag_nsfw(self, *, guild_id: int, name: str, creator_id: int, is_admin: bool = False) -> bool:
        """Mark a tag as NSFW when requested by its owner or a server admin."""
        tag_filter = {"name": name} if is_admin else {"name": name, "creator_id": creator_id}
        updated = await self.guilds_collection.update_one(
            {"_id": guild_id, "tags": {"$elemMatch": tag_filter}},
            {"$set": {"tags.$.nsfw": True}},
        )
        if updated.modified_count > 0:
            await self.redis_client.set(RedisKeys.GUILD_TAG_NSFW.format(guild_id=guild_id, tag_name=name), 1)
        return updated.modified_count > 0

    async def search_tags(self, *, guild_id: int, query: str) -> list[str]:
        """Find tag names and aliases matching a case-insensitive query."""
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"tags.name": 1, "tags.aliases": 1},
        )
        if guild is None:
            return []

        query = query.casefold()
        matches = []
        for tag in guild.get("tags", []):
            names = [tag["name"], *tag.get("aliases", [])]
            if any(query in value.casefold() for value in names):
                matches.append(tag["name"])
        return matches

    async def get_tag_usage(self, *, guild_id: int, name_or_alias: str) -> dict[str, int] | None:
        """Get a tag's usage counts without caching them."""
        tag_name = await self.get_tag_name(guild_id=guild_id, name_or_alias=name_or_alias)
        if tag_name is None:
            return None

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "tags.name": tag_name},
            {"tags.$.used_count": 1},
        )
        if guild is None:
            return None
        return guild["tags"][0].get("used_count", {})

    async def get_top_tag_users(self, *, guild_id: int, limit: int = 10) -> list[TagUserUsage]:
        """Get users with the most tag uses in a guild."""
        cursor = await self.guilds_collection.aggregate(
            [
                {"$match": {"_id": guild_id}},
                {"$unwind": "$tags"},
                {"$project": {"counts": {"$objectToArray": {"$ifNull": ["$tags.used_count", {}]}}}},
                {"$unwind": "$counts"},
                {"$group": {"_id": "$counts.k", "count": {"$sum": "$counts.v"}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ],
        )
        rows = cast(list[_TagUserUsageRow], [row async for row in cursor])
        return [{"user_id": int(row["_id"]), "count": int(row["count"])} for row in rows]

    async def get_top_used_tags(self, *, guild_id: int, limit: int = 10) -> list[TopTagUsage]:
        """Get tags with the most uses in a guild."""
        cursor = await self.guilds_collection.aggregate(
            [
                {"$match": {"_id": guild_id}},
                {"$unwind": "$tags"},
                {"$project": {"name": "$tags.name", "counts": {"$objectToArray": {"$ifNull": ["$tags.used_count", {}]}}}},
                {"$unwind": {"path": "$counts", "preserveNullAndEmptyArrays": True}},
                {"$group": {"_id": "$name", "count": {"$sum": {"$ifNull": ["$counts.v", 0]}}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ],
        )
        rows = cast(list[_TopTagUsageRow], [row async for row in cursor])
        return [{"name": row["_id"], "count": int(row["count"])} for row in rows]

    async def edit_tag_content(
        self,
        *,
        guild_id: int,
        creator_id: int,
        name: str,
        content: str,
    ):
        """Edit a tag's content in the database and update its cache."""
        # Update the tag in the database
        update_fields = {}
        update_fields["tags.$.content"] = content

        if update_fields:
            await self.guilds_collection.update_one(
                {"_id": guild_id, "tags.name": name, "tags.creator_id": creator_id},
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
            {
                "_id": guild_id,
                "tags": {
                    "$elemMatch": {
                        "$or": [{"name": name_or_alias}, {"aliases": name_or_alias}],
                    },
                },
            },
            {"$inc": {f"tags.$.used_count.{str(author_id)}": 1}},
        )

        tag_name = await self.redis_client.hget(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), name_or_alias)
        if tag_name is None:
            tag_name = name_or_alias
        elif isinstance(tag_name, bytes):
            tag_name = tag_name.decode()

        # Increment the used count in the cache
        await self.redis_client.hincrby(
            RedisKeys.GUILD_TAG_USED_COUNT.format(guild_id=guild_id, tag_name=tag_name),
            str(author_id),
        )

    async def transfer_tag_ownership(self, *, guild_id: int, name: str, new_creator_id: int):
        """Transfer ownership of a tag in the database and update its cache."""
        # Update the creator_id in the database
        updated = await self.guilds_collection.update_one(
            {"_id": guild_id, "tags.name": name},
            {"$set": {"tags.$.creator_id": new_creator_id}},
        )
        # Update the cache
        await self.redis_client.set(
            RedisKeys.GUILD_TAG_CREATOR_ID.format(guild_id=guild_id, tag_name=name),
            new_creator_id,
        )
        return updated.modified_count > 0

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
            nsfw=tag.get("nsfw", False),
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
            nsfw=tag.get("nsfw", False),
            aliases=tag.get("aliases", []),
            created_at=tag["created_at"],
            used_count=tag.get("used_count"),
        )

        return True

    async def get_all_tags(self, *, guild_id: int) -> list[Tag]:
        """Get all tags in a guild."""
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "tags": {"$exists": True}},
            {"tags": 1},
        )
        if not guild or "tags" not in guild:
            return []

        tags = guild["tags"]
        for tag in tags:
            await self._cache_tag(
                guild_id=guild_id,
                name=tag["name"],
                content=tag["content"],
                creator_id=tag["creator_id"],
                nsfw=tag.get("nsfw", False),
                aliases=tag.get("aliases", []),
                created_at=tag["created_at"],
                used_count=tag.get("used_count"),
            )

        return tags

    async def add_tag_alias(self, *, guild_id: int, name: str, alias: str):
        """Add an alias to a tag in the database and update its cache."""
        # Update the tag in the database
        updated = await self.guilds_collection.update_one(
            {"_id": guild_id, "tags.name": name},
            {"$addToSet": {"tags.$.aliases": alias}},
        )

        if updated.modified_count > 0:
            # Update the cache
            await self.redis_client.sadd(RedisKeys.GUILD_TAG_ALIASES.format(guild_id=guild_id, tag_name=name), alias)
            await self.redis_client.hset(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), mapping={alias: name})

    async def remove_tag_alias(self, *, guild_id: int, name: str, alias: str, creator_id: int, is_admin: bool = False):
        """Remove an alias from a tag in the database and update its cache."""
        # Update the tag in the database
        tag_filter = {"name": name} if is_admin else {"name": name, "creator_id": creator_id}
        updated = await self.guilds_collection.update_one(
            {"_id": guild_id, "tags": {"$elemMatch": tag_filter}},
            {"$pull": {"tags.$.aliases": alias}},
        )

        if updated.modified_count > 0:
            # Update the cache
            await self.redis_client.srem(RedisKeys.GUILD_TAG_ALIASES.format(guild_id=guild_id, tag_name=name), alias)
            await self.redis_client.hdel(RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id), alias)
