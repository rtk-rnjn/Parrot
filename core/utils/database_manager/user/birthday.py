from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..models import UserConfiguration


class _UserBirthdayMixin:
    redis_client: Redis
    users_collection: AsyncCollection[UserConfiguration]

    async def set_user_birthday(self, *, user_id: int, birthday: str) -> None:
        await self.users_collection.update_one({"_id": user_id}, {"$set": {"birthday": birthday}}, upsert=True)

    async def clear_user_birthday(self, user_id: int, /) -> None:
        await self.users_collection.update_one({"_id": user_id}, {"$unset": {"birthday": ""}})

    async def get_user_birthday(self, user_id: int, /) -> str | None:
        user = await self.users_collection.find_one({"_id": user_id, "birthday": {"$exists": True}}, {"birthday": 1})
        return user.get("birthday") if user else None

    async def get_users_with_birthdays(self) -> list[UserConfiguration]:
        return await self.users_collection.find({"birthday": {"$exists": True}}, {"_id": 1, "birthday": 1}).to_list()
