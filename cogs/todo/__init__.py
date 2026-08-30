from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, NotRequired, TypedDict

from bson import ObjectId
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot


class TodoStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoItem(TypedDict):
    _id: NotRequired[ObjectId]
    user_id: int
    title: str
    notes: str | None
    due: datetime | None
    status: TodoStatus
    parent_id: ObjectId | None


class Todo(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="todo")
    async def todo(self, ctx: commands.Context) -> None:
        """Manage your to-do list."""
        if ctx.invoked_subcommand is None:
            # List TODO(s)
            await ctx.send_help(ctx.command)


async def setup(bot: Parrot) -> None:
    """Load the Todo cog."""
    await bot.add_cog(Todo(bot))
