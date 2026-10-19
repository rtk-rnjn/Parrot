from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from bson import ObjectId
from discord.utils import MISSING

from ..mixin import DatabaseMixin

if TYPE_CHECKING:
    from ..models import UserViolation


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
        violation = {
            "_id": ObjectId(),
            "violation_name": violation_name,
            "user_id": user_id,
            "issued_at": issued_at,
            "issued_by": issued_by,
            "expires_at": expired_at,
            "metadata": metadata or {},
        }
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$push": {"user_violations": violation}},
            upsert=True,
        )

    async def reset_violations(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> int:
        """Reset the violation count for a user in a guild and return the previous count."""
        previous_count = await self.get_violation_count(guild_id=guild_id, violation_name=violation_name, user_id=user_id)

        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"user_violations": {"violation_name": violation_name, "user_id": user_id}}},
        )

        return previous_count

    async def delete_violation(self, *, guild_id: int, _id: ObjectId) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"user_violations": {"_id": _id}}},
        )

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
        }
        if issued_by is not MISSING:
            filters["issued_by"] = issued_by
        if within is not MISSING:
            filters["issued_at"] = {"$gte": datetime.now(UTC) - within} if within is not None else {"$eq": None}

        cursor = await self.guilds_collection.aggregate(
            [
                {"$match": {"_id": guild_id}},
                {"$unwind": "$user_violations"},
                {"$match": {f"user_violations.{k}": v for k, v in filters.items()}},
                {"$count": "count"},
            ]
        )
        count = 0
        async for doc in cursor:
            count = doc.get("count", 0)
        return count

    async def get_violations(
        self,
        *,
        guild_id: int,
        user_id: int,
        violation_name: str = "default",
        active_only: bool = False,
    ) -> list[UserViolation]:
        """Violations of one user, newest first. ``active_only`` drops expired ones (``expires_at`` in the past)."""
        violation_filter = {"user_id": user_id, "violation_name": violation_name}
        if active_only:
            violation_filter["$or"] = [{"expires_at": None}, {"expires_at": {"$gt": datetime.now(UTC)}}]

        cursor = await self.guilds_collection.aggregate(
            [
                {"$match": {"_id": guild_id}},
                {"$unwind": "$user_violations"},
                {"$replaceRoot": {"newRoot": "$user_violations"}},
                {"$match": violation_filter},
                {"$sort": {"issued_at": -1}},
            ]
        )
        return [document async for document in cursor]  # pyright: ignore[reportReturnType]
