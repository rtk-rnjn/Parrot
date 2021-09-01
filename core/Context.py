from __future__ import annotations
from discord.ext import commands
import functools
import discord, typing
__all__ = ("Context", )


class Context(commands.Context):
    """A custom implementation of commands.Context class."""
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    def with_type(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            context = args[0] if isinstance(args[0], commands.Context) else args[1]
            async with context.typing():
                await func(*args, **kwargs)
        return wrapped
    
    async def send(self, content: typing.Optional[str] = None, **kwargs) -> typing.Optional[discord.Message]:
        if not (_perms := self.channel.permissions_for(self.me)).send_messages:
            try:
                await self.author.send(
                    "Bot don't have permission to send message in that channel. Please give me sufficient permissions to do so."
                )
            except discord.Forbidden:
                pass
            return
        
        return await super().send(content, **kwargs)
    
    async def reply(self, content: typing.Optional[str] = None, **kwargs) -> typing.Optional[discord.Message]:
        if not (_perms := self.channel.permissions_for(self.me)).send_messages:
            try:
                await self.author.send(
                    "Bot don't have permission to send message in that channel. Please give me sufficient permissions to do so."
                )
            except discord.Forbidden:
                pass
            return
        
        return await super().reply(content, **kwargs)
    