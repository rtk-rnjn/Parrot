from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from bson import ObjectId
from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import TodoItem, TodoPriority, TodoStatus, UserConfiguration

CACHE_TTL_SECONDS = 3600
CACHE_FIELD = "data"

STATUS_RANK = {TodoStatus.IN_PROGRESS: 0, TodoStatus.PENDING: 1, TodoStatus.COMPLETED: 2}
PRIORITY_RANK = {TodoPriority.HIGH: 0, TodoPriority.MEDIUM: 1, TodoPriority.LOW: 2, TodoPriority.NONE: 3}


def _to_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _enum[E: StrEnum](enum_type: type[E], value: object, default: E) -> E:
    try:
        return enum_type(value)
    except ValueError:
        return default


def hydrate_todo_item(raw: Mapping[str, Any]) -> TodoItem:
    """Build a normalised :class:`TodoItem` from a MongoDB or cache payload.

    Fills defaults for documents written before ``priority`` and
    ``completed_at`` existed and makes every datetime timezone-aware.
    """
    return TodoItem(
        id=ObjectId(raw["id"]),
        title=raw["title"],
        notes=raw.get("notes"),
        due=_to_datetime(raw.get("due")),
        status=_enum(TodoStatus, raw.get("status"), TodoStatus.PENDING),
        priority=_enum(TodoPriority, raw.get("priority"), TodoPriority.NONE),
        created_at=_to_datetime(raw.get("created_at")) or datetime.now(UTC),
        completed_at=_to_datetime(raw.get("completed_at")),
    )


def sort_todo_items(items: list[TodoItem]) -> list[TodoItem]:
    """Order by status, then soonest due date, then priority, then creation time."""

    def key(item: TodoItem) -> tuple[int, bool, float, int, float]:
        due = item["due"]
        return (
            STATUS_RANK[item["status"]],
            due is None,
            due.timestamp() if due else 0.0,
            PRIORITY_RANK[item["priority"]],
            item["created_at"].timestamp(),
        )

    return sorted(items, key=key)


class _UserTodoMixin(DatabaseMixin):
    """Persistence and caching for per-user to-do items."""

    users_collection: AsyncCollection[UserConfiguration]

    async def _cache_todo_item(self, *, user_id: int, todo_item: TodoItem) -> None:
        item_key = RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_id=str(todo_item["id"]))
        payload = json.dumps(
            {
                **todo_item,
                "id": str(todo_item["id"]),
                "due": _iso(todo_item["due"]),
                "created_at": _iso(todo_item["created_at"]),
                "completed_at": _iso(todo_item["completed_at"]),
                "status": str(todo_item["status"]),
                "priority": str(todo_item["priority"]),
            }
        )
        await self.redis_client.hset(item_key, mapping={CACHE_FIELD: payload})
        await self.redis_client.expire(item_key, CACHE_TTL_SECONDS)

        ids_key = RedisKeys.USER_TODO_ITEM_IDS.format(user_id=user_id)
        await self.redis_client.sadd(ids_key, str(todo_item["id"]))
        await self.redis_client.expire(ids_key, CACHE_TTL_SECONDS)

    async def _invalidate_todo_item(self, *, user_id: int, todo_item_id: ObjectId) -> None:
        await self.redis_client.delete(RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_id=str(todo_item_id)))
        await self.redis_client.srem(RedisKeys.USER_TODO_ITEM_IDS.format(user_id=user_id), str(todo_item_id))

    async def create_user_todo_item(
        self,
        *,
        user_id: int,
        title: str,
        notes: str | None = None,
        due: datetime | None = None,
        priority: TodoPriority = TodoPriority.NONE,
        status: TodoStatus = TodoStatus.PENDING,
    ) -> TodoItem:
        todo_item = TodoItem(
            id=ObjectId(),
            title=title,
            notes=notes,
            due=due,
            status=status,
            priority=priority,
            created_at=datetime.now(UTC),
            completed_at=None,
        )
        document = {**todo_item, "status": str(status), "priority": str(priority)}
        await self.users_collection.update_one({"_id": user_id}, {"$push": {"todo_items": document}}, upsert=True)
        return todo_item

    async def get_user_todo_items(self, *, user_id: int) -> list[TodoItem]:
        user_config = await self.users_collection.find_one({"_id": user_id}, {"todo_items": 1})
        if not user_config or not user_config.get("todo_items"):
            return []
        return sort_todo_items([hydrate_todo_item(raw) for raw in user_config["todo_items"]])

    async def get_user_todo_item(self, *, user_id: int, todo_item_id: ObjectId) -> TodoItem | None:
        item_key = RedisKeys.USER_TODO_ITEM.format(user_id=user_id, todo_id=str(todo_item_id))
        cached = await self.redis_client.hget(item_key, CACHE_FIELD)
        if cached:
            return hydrate_todo_item(json.loads(cached))

        user_config = await self.users_collection.find_one({"_id": user_id, "todo_items.id": todo_item_id}, {"todo_items.$": 1})
        if not user_config or not user_config.get("todo_items"):
            return None

        todo_item = hydrate_todo_item(user_config["todo_items"][0])
        await self._cache_todo_item(user_id=user_id, todo_item=todo_item)
        return todo_item

    async def edit_user_todo_item(
        self,
        *,
        user_id: int,
        todo_item_id: ObjectId,
        title: str = MISSING,
        notes: str | None = MISSING,
        due: datetime | None = MISSING,
        status: TodoStatus = MISSING,
        priority: TodoPriority = MISSING,
    ) -> TodoItem | None:
        """Update the given fields and return the fresh item, or ``None`` if it does not exist."""
        fields: dict[str, Any] = {}
        if title is not MISSING:
            fields["todo_items.$.title"] = title
        if notes is not MISSING:
            fields["todo_items.$.notes"] = notes
        if due is not MISSING:
            fields["todo_items.$.due"] = due
        if priority is not MISSING:
            fields["todo_items.$.priority"] = str(priority)
        if status is not MISSING:
            fields["todo_items.$.status"] = str(status)
            fields["todo_items.$.completed_at"] = datetime.now(UTC) if status == TodoStatus.COMPLETED else None

        if not fields:
            return await self.get_user_todo_item(user_id=user_id, todo_item_id=todo_item_id)

        result = await self.users_collection.update_one({"_id": user_id, "todo_items.id": todo_item_id}, {"$set": fields})
        if result.matched_count == 0:
            return None

        await self._invalidate_todo_item(user_id=user_id, todo_item_id=todo_item_id)
        return await self.get_user_todo_item(user_id=user_id, todo_item_id=todo_item_id)

    async def delete_user_todo_item(self, *, user_id: int, todo_item_id: ObjectId) -> bool:
        result = await self.users_collection.update_one({"_id": user_id}, {"$pull": {"todo_items": {"id": todo_item_id}}})
        if result.modified_count == 0:
            return False
        await self._invalidate_todo_item(user_id=user_id, todo_item_id=todo_item_id)
        return True

    async def clear_completed_user_todo_items(self, *, user_id: int) -> list[TodoItem]:
        """Remove every completed item and return what was removed."""
        completed = [item for item in await self.get_user_todo_items(user_id=user_id) if item["status"] == TodoStatus.COMPLETED]
        if not completed:
            return []

        await self.users_collection.update_one({"_id": user_id}, {"$pull": {"todo_items": {"status": str(TodoStatus.COMPLETED)}}})
        for item in completed:
            await self._invalidate_todo_item(user_id=user_id, todo_item_id=item["id"])
        return completed
