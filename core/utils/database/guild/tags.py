from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, cast

import arrow
from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import Tag, TagUserUsage, TagUserUsageRow, TopTagUsage

_CACHE_TTL = 6 * 60 * 60
_NO_USAGE: dict[str, int] = {"used_count": 0}


def _text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value


def _map_key(guild_id: int) -> str:
    return RedisKeys.GUILD_TAG_ALIAS_MAP.format(guild_id=guild_id)


def _content_key(guild_id: int, name: str) -> str:
    return RedisKeys.GUILD_TAG_CONTENT.format(guild_id=guild_id, tag_name=name)


def _nsfw_key(guild_id: int, name: str) -> str:
    return RedisKeys.GUILD_TAG_NSFW.format(guild_id=guild_id, tag_name=name)


class _GuildTagsMixin(DatabaseMixin):
    @staticmethod
    def _lookup(guild_id: int, name_or_alias: str) -> dict[str, Any]:
        return {"guild_id": guild_id, "$or": [{"name": name_or_alias}, {"aliases": name_or_alias}]}

    @staticmethod
    def _owned(guild_id: int, name: str, creator_id: int, is_admin: bool) -> dict[str, Any]:
        """Filter for a tag the caller may modify (owner, or anyone if admin)."""
        flt: dict[str, Any] = {"guild_id": guild_id, "name": name}
        if not is_admin:
            flt["creator_id"] = creator_id
        return flt

    async def _name_taken(self, guild_id: int, names: Sequence[str]) -> bool:
        """Whether any of ``names`` is already a tag name or alias in this guild."""
        wanted = list(names)
        found = await self.tags_collection.find_one(
            {"guild_id": guild_id, "$or": [{"name": {"$in": wanted}}, {"aliases": {"$in": wanted}}]},
            projection={"_id": 1},
        )
        return found is not None

    async def _cache_tag(self, tag: Tag) -> None:
        guild_id, name = tag["guild_id"], tag["name"]
        resolve = {name: name, **dict.fromkeys(tag.get("aliases", []), name)}
        map_key = _map_key(guild_id)

        async with self.redis_client.pipeline(transaction=False) as pipe:
            pipe.hset(map_key, mapping=resolve)
            pipe.expire(map_key, _CACHE_TTL)
            pipe.set(_content_key(guild_id, name), tag["content"], ex=_CACHE_TTL)
            pipe.set(_nsfw_key(guild_id, name), int(tag["nsfw"]), ex=_CACHE_TTL)
            await pipe.execute()

    async def _uncache_tag(self, *, guild_id: int, name: str, aliases: Sequence[str]) -> None:
        async with self.redis_client.pipeline(transaction=False) as pipe:
            pipe.hdel(_map_key(guild_id), name, *aliases)
            pipe.delete(_content_key(guild_id, name), _nsfw_key(guild_id, name))
            await pipe.execute()

    async def _load_tag(self, guild_id: int, name_or_alias: str) -> Tag | None:
        """Read a tag from Mongo and (re)populate the cache."""
        tag = await self.tags_collection.find_one(self._lookup(guild_id, name_or_alias), projection=_NO_USAGE)
        if tag is not None:
            await self._cache_tag(tag)
        return tag

    async def create_tag(
        self,
        *,
        guild_id: int,
        name: str,
        content: str,
        creator_id: int,
        nsfw: bool = False,
        aliases: list[str] | None = None,
    ) -> bool:
        """Create a tag. Returns ``False`` if the name or any alias is already in use."""
        aliases = [a for a in dict.fromkeys(aliases or []) if a != name]
        if await self._name_taken(guild_id, [name, *aliases]):
            return False

        tag: Tag = {
            "_id": ObjectId(),
            "guild_id": guild_id,
            "name": name,
            "content": content,
            "nsfw": nsfw,
            "creator_id": creator_id,
            "created_at": arrow.utcnow().datetime,
            "aliases": aliases,
            "used_count": {},
        }
        try:
            await self.tags_collection.insert_one(tag)
        except DuplicateKeyError:  # lost a race on the unique (guild_id, name) index
            return False

        await self._cache_tag(tag)
        return True

    async def delete_tag(self, *, guild_id: int, name: str, creator_id: int, is_admin: bool = False) -> bool:
        """Delete a tag the caller owns (or any tag, if admin)."""
        # find_one_and_delete returns the document, so we know which aliases to evict.
        deleted = await self.tags_collection.find_one_and_delete(
            self._owned(guild_id, name, creator_id, is_admin),
            projection=_NO_USAGE,
        )
        if deleted is None:
            return False

        await self._uncache_tag(guild_id=guild_id, name=deleted["name"], aliases=deleted.get("aliases", []))
        return True

    async def get_tag_name(self, *, guild_id: int, name_or_alias: str) -> str | None:
        """Resolve a name or alias to the tag's canonical name."""
        cached = await self.redis_client.hget(_map_key(guild_id), name_or_alias)
        if cached is not None:
            return _text(cached)

        tag = await self._load_tag(guild_id, name_or_alias)
        return tag["name"] if tag else None

    async def is_tag_present(self, *, guild_id: int, name_or_alias: str) -> bool:
        return await self.get_tag_name(guild_id=guild_id, name_or_alias=name_or_alias) is not None

    async def get_tag_content(self, *, guild_id: int, name_or_alias: str) -> str | None:
        name = await self.get_tag_name(guild_id=guild_id, name_or_alias=name_or_alias)
        if name is None:
            return None

        cached = await self.redis_client.get(_content_key(guild_id, name))
        if cached is not None:
            return _text(cached)

        tag = await self._load_tag(guild_id, name)
        return tag["content"] if tag else None

    async def is_tag_nsfw(self, *, guild_id: int, name_or_alias: str) -> bool:
        name = await self.get_tag_name(guild_id=guild_id, name_or_alias=name_or_alias)
        if name is None:
            return False

        cached = await self.redis_client.get(_nsfw_key(guild_id, name))
        if cached is not None:
            return _text(cached) == "1"

        tag = await self._load_tag(guild_id, name)
        return bool(tag and tag["nsfw"])

    async def get_tag_owner_id(self, *, guild_id: int, name_or_alias: str) -> int | None:
        """Owner lookup for permission checks. One indexed query, so it isn't cached."""
        tag = await self.tags_collection.find_one(
            self._lookup(guild_id, name_or_alias),
            projection={"creator_id": 1},
        )
        return tag["creator_id"] if tag else None

    async def get_all_tags(self, *, guild_id: int) -> list[Tag]:
        """All tags in a guild, sorted by name. Does not touch the cache."""
        cursor = self.tags_collection.find({"guild_id": guild_id}).sort("name", ASCENDING)
        return await cursor.to_list(length=None)

    async def search_tags(self, *, guild_id: int, query: str, limit: int = 25) -> list[str]:
        """Tag names whose name or alias contains ``query`` (case-insensitive)."""
        pattern = {"$regex": re.escape(query), "$options": "i"}  # escape: query is user input
        cursor = (
            self.tags_collection.find(
                {"guild_id": guild_id, "$or": [{"name": pattern}, {"aliases": pattern}]},
                projection={"name": 1},
            )
            .sort("name", ASCENDING)
            .limit(limit)
        )
        return [tag["name"] async for tag in cursor]

    async def edit_tag_content(
        self,
        *,
        guild_id: int,
        creator_id: int,
        name: str,
        content: str,
        is_admin: bool = False,
    ) -> bool:
        result = await self.tags_collection.update_one(
            self._owned(guild_id, name, creator_id, is_admin),
            {"$set": {"content": content}},
        )
        if result.matched_count == 0:
            return False

        await self.redis_client.set(_content_key(guild_id, name), content, ex=_CACHE_TTL)
        return True

    async def mark_tag_nsfw(
        self,
        *,
        guild_id: int,
        name: str,
        creator_id: int,
        is_admin: bool = False,
        nsfw: bool = True,
    ) -> bool:
        result = await self.tags_collection.update_one(
            self._owned(guild_id, name, creator_id, is_admin),
            {"$set": {"nsfw": nsfw}},
        )
        if result.matched_count == 0:
            return False

        await self.redis_client.set(_nsfw_key(guild_id, name), int(nsfw), ex=_CACHE_TTL)
        return True

    async def transfer_tag_ownership(self, *, guild_id: int, name: str, new_creator_id: int) -> bool:
        # creator_id isn't cached, so there's nothing to invalidate.
        result = await self.tags_collection.update_one(
            {"guild_id": guild_id, "name": name},
            {"$set": {"creator_id": new_creator_id}},
        )
        return result.matched_count > 0

    async def add_tag_alias(self, *, guild_id: int, name: str, alias: str) -> bool:
        """Returns ``False`` if the alias is taken or the tag doesn't exist."""
        if await self._name_taken(guild_id, [alias]):
            return False

        result = await self.tags_collection.update_one(
            {"guild_id": guild_id, "name": name},
            {"$addToSet": {"aliases": alias}},
        )
        if result.modified_count == 0:
            return False

        map_key = _map_key(guild_id)
        async with self.redis_client.pipeline(transaction=False) as pipe:
            pipe.hset(map_key, alias, name)
            pipe.expire(map_key, _CACHE_TTL)
            await pipe.execute()
        return True

    async def remove_tag_alias(
        self,
        *,
        guild_id: int,
        name: str,
        alias: str,
        creator_id: int,
        is_admin: bool = False,
    ) -> bool:
        result = await self.tags_collection.update_one(
            self._owned(guild_id, name, creator_id, is_admin),
            {"$pull": {"aliases": alias}},
        )
        if result.modified_count == 0:
            return False

        await self.redis_client.hdel(_map_key(guild_id), alias)
        return True

    async def increment_tag_used_count(self, *, guild_id: int, name_or_alias: str, author_id: int) -> bool:
        result = await self.tags_collection.update_one(
            self._lookup(guild_id, name_or_alias),
            {"$inc": {f"used_count.{author_id}": 1}},
        )
        return result.matched_count > 0

    async def get_tag_usage(self, *, guild_id: int, name_or_alias: str) -> dict[str, int] | None:
        tag = await self.tags_collection.find_one(
            self._lookup(guild_id, name_or_alias),
            projection={"used_count": 1},
        )
        return None if tag is None else tag.get("used_count", {})

    async def get_top_tag_users(self, *, guild_id: int, limit: int = 10) -> list[TagUserUsage]:
        cursor = await self.tags_collection.aggregate(
            [
                {"$match": {"guild_id": guild_id}},
                {"$project": {"counts": {"$objectToArray": {"$ifNull": ["$used_count", {}]}}}},
                {"$unwind": "$counts"},
                {"$group": {"_id": "$counts.k", "count": {"$sum": "$counts.v"}}},
                {"$sort": {"count": -1, "_id": 1}},
                {"$limit": limit},
            ]
        )
        rows = cast(list[TagUserUsageRow], [row async for row in cursor])
        return [{"user_id": int(row["_id"]), "count": int(row["count"])} for row in rows]

    async def get_top_used_tags(self, *, guild_id: int, limit: int = 10) -> list[TopTagUsage]:
        cursor = await self.tags_collection.aggregate(
            [
                {"$match": {"guild_id": guild_id}},
                {
                    "$project": {
                        "_id": 0,
                        "name": 1,
                        # Sum the per-user counts in place; no $unwind needed.
                        "count": {
                            "$sum": {
                                "$map": {
                                    "input": {"$objectToArray": {"$ifNull": ["$used_count", {}]}},
                                    "as": "entry",
                                    "in": "$$entry.v",
                                }
                            }
                        },
                    }
                },
                {"$sort": {"count": -1, "name": 1}},
                {"$limit": limit},
            ]
        )
        rows = cast(list[TopTagUsage], [row async for row in cursor])
        return [{"name": row["name"], "count": int(row["count"])} for row in rows]
