from __future__ import annotations

from datetime import datetime
from typing import Literal

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import TodoItem, TodoStatus, UserConfiguration


class _UserTodoMixin:
    """User timezone operations."""

    redis_client: Redis
    users_collection: AsyncCollection[UserConfiguration]

    async def _cache_user_todo_item(
        self,
        *,
        user_id: int,
        todo_item: TodoItem,
    ):
        user_todo_item_cache_key = RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_item_id=str(todo_item["id"]))
        await self.redis_client.hset(user_todo_item_cache_key, mapping={str(k): str(v) for k, v in todo_item.items()})

        redis_todo_item_ids_cache_key = RedisKeys.USER_TODO_ITEM_IDS.format(user_id=user_id)
        await self.redis_client.sadd(redis_todo_item_ids_cache_key, str(todo_item["id"]))

    async def _invalidate_user_todo_item_cache(
        self,
        *,
        user_id: int,
        todo_item_id: ObjectId,
    ):
        redis_key = RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_item_id=str(todo_item_id))
        await self.redis_client.delete(redis_key)

        redis_todo_item_ids_cache_key = RedisKeys.USER_TODO_ITEM_IDS.format(user_id=user_id)
        await self.redis_client.srem(redis_todo_item_ids_cache_key, str(todo_item_id))

    async def create_user_todo_item(  # noqa: PLR0913
        self,
        *,
        user_id: int,
        title: str,
        notes: str | None = None,
        due: datetime | None = None,
        status: Literal["pending", "in_progress", "completed"] = "pending",
        parent_id: ObjectId | None = None,
    ):
        todo_item: TodoItem = TodoItem(
            id=ObjectId(),
            title=title,
            notes=notes,
            due=due,
            status=TodoStatus(status),
            parent_id=parent_id,
        )

        await self.users_collection.update_one(
            {"_id": user_id},
            {"$push": {"todo_items": todo_item}},
            upsert=True,
        )
        return todo_item

    async def get_user_todo_items(self, *, user_id: int) -> list[TodoItem]:
        user_config = await self.users_collection.find_one(
            {"_id": user_id, "todo_items": {"$exists": True}},
            {"todo_items": 1},
        )
        if not user_config:
            return []

        for todo_item in user_config["todo_items"]:
            await self._cache_user_todo_item(user_id=user_id, todo_item=todo_item)

        return user_config["todo_items"]

    async def get_user_todo_item(self, *, user_id: int, todo_item_id: ObjectId) -> TodoItem | None:
        redis_key = RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_item_id=str(todo_item_id))
        cached_todo_item: dict[str, str] = await self.redis_client.hgetall(redis_key)  # pyright: ignore[reportAssignmentType]
        if cached_todo_item:
            return TodoItem(
                id=ObjectId(cached_todo_item["id"]),
                title=cached_todo_item["title"],
                notes=cached_todo_item.get("notes"),
                due=datetime.fromisoformat(cached_todo_item["due"]) if cached_todo_item.get("due") else None,
                status=TodoStatus(cached_todo_item["status"]),
                parent_id=ObjectId(cached_todo_item["parent_id"]) if cached_todo_item.get("parent_id") else None,
            )

        user_config = await self.users_collection.find_one(
            {"_id": user_id, "todo_items.id": todo_item_id},
            {"todo_items.$": 1},
        )
        if not user_config or not user_config.get("todo_items"):
            return None

        todo_item = user_config["todo_items"][0]
        await self._cache_user_todo_item(user_id=user_id, todo_item=todo_item)
        return todo_item
