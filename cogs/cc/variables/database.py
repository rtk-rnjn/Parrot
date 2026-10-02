from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Protocol

import discord


class GetFunc(Protocol):
    def __call__(self, *, guild_id: int, key: str, default: str | None = None) -> Awaitable[str | None]: ...


class SetFunc(Protocol):
    def __call__(self, *, guild_id: int, key: str, value: str) -> Awaitable[None]: ...


class DeleteFunc(Protocol):
    def __call__(self, *, guild_id: int, key: str) -> Awaitable[None]: ...


class ExistsFunc(Protocol):
    def __call__(self, *, guild_id: int, key: str) -> Awaitable[bool]: ...


class Database(ABC):
    @abstractmethod
    async def get(self, key: str, default: str | None = None) -> str | None:
        """Get a value by key."""
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Set a value."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether a key exists."""
        raise NotImplementedError


class ServerDatabase(Database):
    def __init__(self, *, guild: discord.Guild, get_func: GetFunc, set_func: SetFunc, delete_func: DeleteFunc, exists_func: ExistsFunc) -> None:
        self.guild_id = guild.id
        self.get_func = get_func
        self.set_func = set_func
        self.delete_func = delete_func
        self.exists_func = exists_func

    async def get(self, key: str, default: str | None = None) -> str | None:
        return await self.get_func(guild_id=self.guild_id, key=key, default=default)

    async def set(self, key: str, value: str) -> None:
        await self.set_func(guild_id=self.guild_id, key=key, value=value)

    async def delete(self, key: str) -> None:
        await self.delete_func(guild_id=self.guild_id, key=key)

    async def exists(self, key: str) -> bool:
        return await self.exists_func(guild_id=self.guild_id, key=key)
