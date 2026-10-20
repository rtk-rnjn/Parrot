from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import discord

__all__ = ("CallbackButton", "CallbackChannelSelect", "CallbackMentionableSelect", "CallbackRoleSelect", "CallbackStringSelect")

type ButtonHandler = Callable[[discord.Interaction[Any]], Awaitable[None]]
type ChannelHandler = Callable[[discord.Interaction[Any], list[int]], Awaitable[None]]
type RoleHandler = Callable[[discord.Interaction[Any], list[discord.Role]], Awaitable[None]]
type StringHandler = Callable[[discord.Interaction[Any], list[str]], Awaitable[None]]
type MentionableHandler = Callable[[discord.Interaction[Any], list[discord.abc.Snowflake]], Awaitable[None]]


class CallbackButton(discord.ui.Button):
    """A button that forwards presses to a coroutine."""

    def __init__(self, handler: ButtonHandler, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._handler(interaction)


class CallbackChannelSelect(discord.ui.ChannelSelect):
    """A channel picker that hands the chosen channel ids to a coroutine."""

    def __init__(self, handler: ChannelHandler, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._handler(interaction, [channel.id for channel in self.values])


class CallbackRoleSelect(discord.ui.RoleSelect):
    """A role picker that hands the chosen roles to a coroutine."""

    def __init__(self, handler: RoleHandler, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._handler(interaction, list(self.values))


class CallbackStringSelect(discord.ui.Select):
    """A plain select menu that hands the chosen values to a coroutine."""

    def __init__(self, handler: StringHandler, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._handler(interaction, list(self.values))


class CallbackMentionableSelect(discord.ui.MentionableSelect):
    """A mentionable picker that hands the chosen mentionables to a coroutine."""

    def __init__(self, handler: MentionableHandler, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._handler(interaction, list(self.values))
