from __future__ import annotations

import discord

from ..mixin import DatabaseMixin

__all__ = ("_UserSupercellMixin",)


class _UserSupercellMixin(DatabaseMixin):
    async def get_supercell_account(self, user_id: int, game: str, /):
        document = await self.users_collection.find_one({"_id": user_id}, {f"supercell.{game}": 1})
        return ((document or {}).get("supercell") or {}).get(game)

    async def set_supercell_account(self, user_id: int, game: str, /, *, tag: str, verified: bool = False) -> None:
        account = {"tag": tag, "verified": verified, "linked_at": discord.utils.utcnow()}
        await self.users_collection.update_one({"_id": user_id}, {"$set": {f"supercell.{game}": account}}, upsert=True)

    async def remove_supercell_account(self, user_id: int, game: str, /) -> bool:
        result = await self.users_collection.update_one({"_id": user_id}, {"$unset": {f"supercell.{game}": ""}})
        return result.modified_count > 0

    async def get_supercell_owners(self, game: str, tag: str, /, *, limit: int = 5) -> list[tuple[int, bool]]:
        """Return ``(user_id, verified)`` for every user who linked ``tag``."""
        cursor = self.users_collection.find({f"supercell.{game}.tag": tag}, {f"supercell.{game}.verified": 1}).limit(limit)
        return [(document["_id"], bool(document["supercell"][game].get("verified"))) async for document in cursor]
