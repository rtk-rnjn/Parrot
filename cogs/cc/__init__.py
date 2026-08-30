from __future__ import annotations

from typing import TYPE_CHECKING

from colorama import Fore
from discord.ext import commands

from .jinja import format_sandbox_error, render_sandboxed

if TYPE_CHECKING:
    from core.bot import Parrot


class CustomCommand(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def cc(self, ctx: commands.Context) -> None:
        """Manage custom commands."""
        await ctx.send_help(ctx.command)

    @cc.command(name="test")
    @commands.is_owner()
    async def add_custom_command(self, ctx: commands.Context, *, response: str) -> None:
        response = response.strip("`")
        try:
            rendered = await render_sandboxed(response, send=ctx.send)
        except Exception as e:
            await ctx.send(f"```ansi\n{Fore.BLUE}Error while rendering cc id: None``````ansi\n{Fore.RED}{format_sandbox_error(e)}```")
            return
        await ctx.send(rendered)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(CustomCommand(bot))
