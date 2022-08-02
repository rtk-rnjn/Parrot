from __future__ import annotations

import asyncio
import unicodedata
from time import time
from typing import TYPE_CHECKING, Dict, Optional

import discord
from core import Cog
from discord.ext import commands
from utilities.checks import in_support_server

try:
    import topgg

    HAS_TOP_GG = True
except ImportError:
    HAS_TOP_GG = False


if TYPE_CHECKING:
    from core import Context, Parrot
    from pymongo.collection import Collection

    if HAS_TOP_GG:
        from topgg.types import BotVoteData

from utilities.config import SUPPORT_SERVER_ID

EMOJI = "\N{WASTEBASKET}"
MESSAGE_ID = 1003600244098998283
VOTER_ROLE_ID = 836492413312040990


class Sector1729(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._cache: Dict[int, int] = {}

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.guild is not None and ctx.guild.id == getattr(
            ctx.bot.server, "id", SUPPORT_SERVER_ID
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.message_id == MESSAGE_ID and (
            str(payload.emoji) == EMOJI or unicodedata.name(str(payload.emoji)) == "WASTEBASKET"
        ):
            user_id: int = payload.user_id
            user: Optional[discord.User] = await self.bot.getch(
                self.bot.get_user, self.bot.fetch_user, user_id
            )

            channel: Optional[discord.TextChannel] = self.bot.get_channel(payload.channel_id)

            if channel is None:
                return

            msg: discord.Message = await self.bot.get_or_fetch_message(channel, MESSAGE_ID)

            async def __remove_reaction(msg: discord.Message) -> None:
                for reaction in msg.reactions:
                    if unicodedata.name(reaction.emoji) == "WASTEBASKET":
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.HTTPException:
                            pass

            if then := self._cache.get(payload.user_id):
                if abs(time() - then) < 60:
                    await channel.send(
                        f"<@{payload.user_id}> You can only use the emoji once every minute.",
                        delete_after=7,
                    )
                    await __remove_reaction(msg)
                    return

            self._cache[payload.user_id] = time() + 60

            _msg: discord.Message = await channel.send(
                f"<@{payload.user_id}> deleting messages - 0/100"
            )

            if user is None or user.bot:
                return

            dm: discord.DMChannel = await user.create_dm()

            i = 1
            async for msg in dm.history(limit=50):
                if msg.author.id == self.bot.user.id:
                    await msg.delete(delay=0)
                i += 1

            await __remove_reaction(msg)
            await _msg.edit(content=f"<@{payload.user_id}> done!", delete_after=7)

    @Cog.listener("on_dbl_vote")
    async def on_dbl_vote(self, data: BotVoteData):
        member: Optional[discord.Member] = await self.bot.get_or_fetch_member(
            self.bot.server, data.user
        )

        if member is None:
            return

        await member.add_roles(
            discord.Object(id=VOTER_ROLE_ID), reason="Voted for the bot on Top.gg"
        )
        await self.__add_to_db(member)

    @Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != SUPPORT_SERVER_ID:
            return

        if await self.bot.topgg.get_user_vote(member.id):
            await member.add_roles(
                discord.Object(id=VOTER_ROLE_ID), reason="Voted for the bot on Top.gg"
            )

    @commands.command(name="claimvote", hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @in_support_server()
    async def claim_vote(self, ctx: Context):
        if ctx.author._roles.has(VOTER_ROLE_ID):
            return await ctx.send("You already have the vote role.")

        if await self.bot.mongo.extra.user_misc.find_one(
            {"_id": ctx.author.id, "topgg_vote_expires": {"$lte": time()}}
        ) or await self.bot.topgg.get_user_vote(ctx.author.id):
            role = discord.Object(id=VOTER_ROLE_ID)
            await ctx.author.add_roles(role, reason="Voted for the bot on Top.gg")
            await ctx.send("You have claimed your vote for the bot on Top.gg. Added Golden Role.")
            return

        await ctx.send(
            "Seems you haven't voted for the bot on Top.gg Yet. This might be error. "
            f"Consider asking the owner of the bot ({self.bot.author_obj})"
        )

    async def __add_to_db(self, member: discord.Member) -> None:
        col: Collection = self.bot.mongo.extra.user_misc
        now = time()
        await col.update_one(
            {"_id": member.id},
            {
                "$set": {
                    "topgg_vote_time": now,
                    "topgg_vote_expires": now + 43200,
                },
                "$inc": {"topgg_votes": 1},
            },
            upsert=True,
        )
