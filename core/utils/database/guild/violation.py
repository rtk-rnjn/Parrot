from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from bson import ObjectId

from ..mixin import DatabaseMixin

if TYPE_CHECKING:
    from ..models import UserViolation

MISSING: Any = sentinel("MISSING")


class _GuildViolationMixin(DatabaseMixin):
    """Guild violation counters, backed by MongoDB and Redis."""

    async def add_violation(
        self,
        *,
        guild_id: int,
        violation_name: str = "default",
        user_id: int,
        issued_at: datetime,
        issued_by: int | None,
        expired_at: datetime | None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Add a violation for a user in a guild."""
        violation: UserViolation = {
            "_id": ObjectId(),
            "violation_name": violation_name,
            "user_id": user_id,
            "issued_at": issued_at,
            "guild_id": guild_id,
            "issued_by": issued_by,
            "expires_at": expired_at,
            "metadata": metadata or {},
        }
        await self.user_violations_collection.insert_one(violation)

    async def reset_violations(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> int:
        """Reset the violation count for a user in a guild and return the previous count."""
        previous_count = await self.get_violation_count(guild_id=guild_id, violation_name=violation_name, user_id=user_id)

        await self.user_violations_collection.delete_many({"violation_name": violation_name, "user_id": user_id, "guild_id": guild_id})

        return previous_count

    async def delete_violation(self, *, guild_id: int, _id: ObjectId) -> None:
        await self.user_violations_collection.delete_one({"_id": _id, "guild_id": guild_id})

    async def get_violation_count(
        self,
        *,
        guild_id: int,
        violation_name: str = "default",
        user_id: int,
        issued_by: int | None = MISSING,
        within: timedelta | None = MISSING,
    ) -> int:
        filters = {
            "user_id": user_id,
            "violation_name": violation_name,
            "guild_id": guild_id,
        }
        if issued_by is not MISSING:
            filters["issued_by"] = issued_by
        if within is not MISSING:
            filters["issued_at"] = {"$gte": datetime.now(UTC) - within} if within is not None else {"$eq": None}

        return await self.user_violations_collection.count_documents(filters)

    async def get_violations(
        self,
        *,
        guild_id: int,
        user_id: int,
        violation_name: str = "default",
        active_only: bool = False,
    ) -> list[UserViolation]:
        """Violations of one user, newest first. ``active_only`` drops expired ones (``expires_at`` in the past)."""
        filters = {
            "user_id": user_id,
            "violation_name": violation_name,
            "guild_id": guild_id,
        }
        if active_only:
            filters["$or"] = [
                {"expires_at": {"$eq": None}},
                {"expires_at": {"$gt": datetime.now(UTC)}},
            ]

        cursor = self.user_violations_collection.find(filters).sort("issued_at", -1)
        return await cursor.to_list(length=None)
