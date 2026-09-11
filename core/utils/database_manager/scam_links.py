from __future__ import annotations

from redis.asyncio import Redis

from .cache_keys import RedisKeys

__all__ = ("_ScamLinksMixin",)

class _ScamLinksMixin:
    redis_client: Redis

    async def add_scam_link(self, *links: str) -> None:
        """Add a scam link to the Redis cache."""
        await self.redis_client.sadd(RedisKeys.SCAM_LINKS_CACHE, *links)

    async def remove_scam_link(self, *links: str) -> None:
        """Remove a scam link from the Redis cache."""
        await self.redis_client.srem(RedisKeys.SCAM_LINKS_CACHE, *links)

    async def is_scam_link(self, link: str) -> bool:
        """Check if a link is a scam link in the Redis cache."""
        result = await self.redis_client.sismember(RedisKeys.SCAM_LINKS_CACHE, link)
        return bool(result)

    async def get_all_scam_links(self):
        """Retrieve all scam links from the Redis cache."""
        async for link in self.redis_client.sscan_iter(RedisKeys.SCAM_LINKS_CACHE):
            yield str(link)

    async def invalidate_scam_links_cache(self) -> None:
        """Invalidate the scam links cache in Redis."""
        await self.redis_client.delete(RedisKeys.SCAM_LINKS_CACHE)

    async def get_scam_links_count(self) -> int:
        """Get the count of scam links in the Redis cache."""
        count = await self.redis_client.scard(RedisKeys.SCAM_LINKS_CACHE)
        return int(count)

    async def is_scam_links_cache_exists(self) -> bool:
        """Check if the scam links cache exists in Redis."""
        exists = await self.redis_client.exists(RedisKeys.SCAM_LINKS_CACHE)
        return bool(exists)

    async def flag_link_as_warned(self, *, link: str, channel_id: int) -> None:
        """Mark a link as warned in the Redis cache."""
        await self.redis_client.sadd(RedisKeys.SCAM_LINK_WARNED.format(channel_id=channel_id), link)
        await self.redis_client.expire(RedisKeys.SCAM_LINK_WARNED.format(channel_id=channel_id), 300)

    async def check_if_link_warned(self, *, link: str, channel_id: int) -> bool:
        """Check if a link has been warned in the Redis cache."""
        result = await self.redis_client.sismember(RedisKeys.SCAM_LINK_WARNED.format(channel_id=channel_id), link)
        return bool(result)
