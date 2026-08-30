from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, Final

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

__all__: tuple[str, ...] = (
    "DiscordColor",
    "Player",
    "DEFAULT_COLOR",
    "chunk",
    "BaseView",
    "double_wait",
    "wait_for_delete",
)

DiscordColor = discord.Color | int
Player = discord.User | discord.Member

DEFAULT_COLOR: Final[discord.Color] = discord.Color(0xFFFFFF)


def chunk[T](iterable: list[T], *, count: int) -> list[list[T]]:
    return [iterable[i : i + count] for i in range(0, len(iterable), count)]


async def wait_for_delete(  # noqa: PLR0913
    ctx: commands.Context[Parrot],
    message: discord.Message,
    *,
    emoji: str = "\N{BLACK SQUARE FOR STOP}",
    bot: Parrot | None = None,
    user: discord.User | discord.Member | tuple[discord.User | discord.Member, ...] | None = None,
    timeout: float | None = None,
) -> bool:
    if not user:
        user = ctx.author
    try:
        await message.add_reaction(emoji)
    except discord.DiscordException:
        pass

    def check(reaction: discord.Reaction, _user: discord.User) -> bool:
        if reaction.emoji == emoji and reaction.message.id == message.id:
            if isinstance(user, tuple):
                return _user in user
            else:
                return _user == user
        return False

    resolved_bot: discord.Client = bot or ctx.bot
    try:
        await resolved_bot.wait_for("reaction_add", timeout=timeout, check=check)
    except TimeoutError:
        return False
    else:
        await message.delete()
        return True


async def double_wait[A: bool, B: bool](
    task1: Coroutine[Any, Any, A],
    task2: Coroutine[Any, Any, B],
    /,
    *,
    loop: asyncio.AbstractEventLoop | None = None,
) -> tuple[
    set[asyncio.Task[A] | asyncio.Task[B]],
    set[asyncio.Task[A] | asyncio.Task[B]],
]:
    if not loop:
        loop = asyncio.get_running_loop()

    done, pending = await asyncio.wait(
        [
            loop.create_task(task1),
            loop.create_task(task2),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    return done, pending


class BaseView(discord.ui.View):
    message: discord.Message | None = None

    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        self.disable_all()
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
        self.stop()

    async def on_error(self, interaction: discord.Interaction[Parrot], error: Exception, item: discord.ui.Item[Any], /) -> None:
        raise error
