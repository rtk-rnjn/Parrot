from __future__ import annotations

import discord

from ..mixin import DatabaseMixin

__all__ = ("_UserChessMixin",)


class _UserChessMixin(DatabaseMixin):
    """Linked chess.com account, stored as ``chess_com`` on the user document."""

    async def get_chess_account(self, user_id: int, /):
        document = await self.users_collection.find_one({"_id": user_id}, {"chess_com": 1})
        return (document or {}).get("chess_com")

    async def set_chess_account(self, user_id: int, /, *, username: str) -> None:
        account = {"username": username, "verified": False, "code": None, "linked_at": discord.utils.utcnow()}
        await self.users_collection.update_one({"_id": user_id}, {"$set": {"chess_com": account}}, upsert=True)

    async def set_chess_verification(self, user_id: int, /, *, verified: bool, code: str | None) -> None:
        await self.users_collection.update_one(
            {"_id": user_id},
            {"$set": {"chess_com.verified": verified, "chess_com.code": code}},
        )

    async def remove_chess_account(self, user_id: int, /) -> bool:
        result = await self.users_collection.update_one({"_id": user_id}, {"$unset": {"chess_com": ""}})
        return result.modified_count > 0

    async def get_chess_owners(self, username: str, /, *, limit: int = 5) -> list[tuple[int, bool]]:
        """Return ``(user_id, verified)`` for every user who linked ``username``."""
        cursor = self.users_collection.find({"chess_com.username": username}, {"chess_com.verified": 1}).limit(limit)
        return [(document["_id"], bool(document["chess_com"].get("verified"))) async for document in cursor]
