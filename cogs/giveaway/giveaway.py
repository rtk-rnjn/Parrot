from __future__ import annotations

from typing import Annotated, Optional

import cogs.giveaway.method as mt
import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.time import ShortTime


class Giveaways(Cog):
    """Giveaway commands. Let's start a giveaway!."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{PARTY POPPER}")

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await mt.add_reactor(self.bot, payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await mt.remove_reactor(self.bot, payload)

    @commands.group(name="giveaway", aliases=["gw"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: Context):
        """To create giveaway."""
        if not ctx.invoked_subcommand:
            post = await mt._make_giveaway(ctx)
            await self.bot.create_timer(_event_name="giveaway", **post)

    @giveaway.command(name="drop")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_drop(
        self,
        ctx: Context,
        duration: ShortTime,
        winners: Annotated[int, Optional[int]] = 1,
        *,
        prize: str | None = None,
    ):
        """To create giveaway in quick format."""
        if not prize:
            return await ctx.send(f"{ctx.author.mention} you didn't give the prize argument")
        post = await mt._make_giveaway_drop(ctx, duration=duration, winners=winners, prize=prize)
        await self.bot.create_timer(_event_name="giveaway", **post)

    @giveaway.command(name="end")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_end(self, ctx: Context, message_id: int):
        """To end the giveaway."""
        if data := await self.bot.giveaways.find_one_and_update(
            {"message_id": message_id, "status": "ONGOING"},
            {"$set": {"status": "END"}},
        ):
            member_ids = await mt.end_giveaway(self.bot, **data)
            if not member_ids:
                return await ctx.send(f"{ctx.author.mention} no winners!")

            joiner = ">, <@".join([str(i) for i in member_ids])

            await ctx.send(
                f"Congrats <@{joiner}> you won {data.get('prize')}\n"
                f"> https://discord.com/channels/{data.get('guild_id')}/{data.get('giveaway_channel')}/{data.get('message_id')}",
            )

    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_reroll(self, ctx: Context, message_id: int, winners: int = 1):
        """To end the giveaway."""
        if data := await self.bot.giveaways.find_one({"message_id": message_id}):
            if data["status"].upper() == "ONGOING":
                return await ctx.send(f"{ctx.author.mention} can not reroll the ongoing giveaway")

            data["winners"] = winners

            member_ids = await mt.end_giveaway(self.bot, **data)

            if not member_ids:
                return await ctx.send(f"{ctx.author.mention} no winners!")

            joiner = ">, <@".join([str(i) for i in member_ids])

            await ctx.send(
                f"Contragts <@{joiner}> you won {data.get('prize')}\n"
                f"> https://discord.com/channels/{data.get('guild_id')}/{data.get('giveaway_channel')}/{data.get('message_id')}",
            )
            return
        await ctx.send(f"{ctx.author.mention} no giveaway found on message ID: `{message_id}`")

    @giveaway.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_list(self, ctx: Context):
        """To list all the running giveaway in the server."""
        if data := await self.bot.giveaways.find({"guild_id": ctx.guild.id}).to_list(length=10):
            embed = discord.Embed(title="Giveaway list", color=self.bot.color)
            for i in data:
                embed.add_field(
                    name=f"Message ID: {i.get('message_id')}",
                    value=(
                        f"Prize: {i.get('prize')}\n"
                        f"Winners: {i.get('winners')}\n"
                        f"Channel: <#{i.get('giveaway_channel', 0)}>\n"
                        f"Status: {i.get('status')}\n"
                    ),
                    inline=False,
                )
            await ctx.send(embed=embed)
            return
        await ctx.send(f"{ctx.author.mention} no giveaway found in this server")
