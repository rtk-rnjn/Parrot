from __future__ import annotations

import asyncio
from contextlib import suppress
import unicodedata
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import discord
from core import Cog
from discord.ext import commands, tasks
from utilities.checks import in_support_server
from datetime import datetime

try:
    import topgg

    HAS_TOP_GG = True
except ImportError:
    HAS_TOP_GG = False


if TYPE_CHECKING:
    from pymongo.collection import Collection

    from core import Context, Parrot

    if HAS_TOP_GG:
        from topgg.types import BotVoteData

from utilities.config import SUPPORT_SERVER_ID

EMOJI = "\N{WASTEBASKET}"
MESSAGE_ID = 1025455601398075535
VOTER_ROLE_ID = 836492413312040990
QU_ROLE = 851837681688248351
MEMBER_ROLE_ID = 1022216700650868916


class Sector1729(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._cache: Dict[int, int] = {}
        self.vote_reseter.start()
        self.ON_TESTING = False

        self.lock: "asyncio.Lock" = asyncio.Lock()
        self.__assignable_roles: List[int] = [
            1022896161167777835,  # NSFW ACCESS
            1022896162107310130,  # BOT ACCESS
            1022897174624866426,  # MUSIC ACCESS
        ]

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.guild is not None and ctx.guild.id == getattr(
            ctx.bot.server, "id", SUPPORT_SERVER_ID
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:  # sourcery skip: use-contextlib-suppress
        if (
            payload.message_id != MESSAGE_ID
            or str(payload.emoji) != EMOJI
            and unicodedata.name(str(payload.emoji)) != "WASTEBASKET"
        ):
            return
        user_id: int = payload.user_id
        user: Optional[discord.User] = await self.bot.getch(
            self.bot.get_user, self.bot.fetch_user, user_id
        )

        channel: Optional[discord.TextChannel] = self.bot.get_channel(
            payload.channel_id
        )

        if channel is None:
            return

        msg: discord.Message = await self.bot.get_or_fetch_message(channel, MESSAGE_ID)

        async def __remove_reaction(msg: discord.Message) -> None:
            for reaction in msg.reactions:
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except discord.HTTPException:
                    pass
                return

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
            f"<@{payload.user_id}> deleting messages - 0/50"
        )

        if user is None or user.bot:
            return

        dm: discord.DMChannel = await user.create_dm()

        i = 1
        async for msg in dm.history(limit=50):
            if msg.author.id == self.bot.user.id:
                await msg.delete()
            i += 1
            if i % 10 == 0:
                await _msg.edit(
                    content=f"<@{payload.user_id}> deleting messages - {i}/50"
                )

        await __remove_reaction(msg)
        await _msg.edit(
            content=f"<@{payload.user_id}> deleting messages - 50/50! Done!",
            delete_after=2,
        )

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

        await member.add_roles(
            discord.Object(id=MEMBER_ROLE_ID), reason="Member role add"
        )
        if await self.bot.topgg.get_user_vote(member.id):
            await member.add_roles(
                discord.Object(id=VOTER_ROLE_ID), reason="Voted for the bot on Top.gg"
            )

    @commands.command(name="claimvote", hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @in_support_server()
    async def claim_vote(self, ctx: Context):
        if ctx.author._roles.has(VOTER_ROLE_ID):
            return await ctx.error("You already have the vote role.")

        if await self.bot.user_collections_ind.find_one(
            {"_id": ctx.author.id, "topgg_vote_expires": {"$gte": time()}}
        ) or await self.bot.topgg.get_user_vote(ctx.author.id):
            role = discord.Object(id=VOTER_ROLE_ID)
            await ctx.author.add_roles(role, reason="Voted for the bot on Top.gg")
            await ctx.send(
                "You have claimed your vote for the bot on Top.gg. Added Golden Role."
            )
            return

        await ctx.send(
            "Seems you haven't voted for the bot on Top.gg Yet. This might be error. "
            f"Consider asking the owner of the bot ({self.bot.author_obj})"
        )

    @commands.command(name="myvotes", hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @in_support_server()
    async def my_votes(self, ctx: Context):
        if data := await self.bot.mongo.user_misc.find_one(
            {"_id": ctx.author.id, "topgg_votes": {"$exists": True}}
        ):
            await ctx.send(
                f"You voted for **{self.bot.user}** for **{len(data['topgg_votes'])}** times on Top.gg"
            )
        else:
            await ctx.send("You haven't voted for the bot on Top.gg yet.")

    async def __add_to_db(self, member: discord.Member) -> None:
        col: Collection = self.bot.user_collections_ind
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

    @tasks.loop(minutes=5)
    async def vote_reseter(self):
        async with self.lock:
            col: Collection = self.bot.user_collections_ind
            now_plus_12_hours = time() + 43200

            async for doc in col.find(
                {"topgg_vote_expires": {"$lte": now_plus_12_hours}}
            ):
                guild = self.bot.server
                role = discord.Object(id=VOTER_ROLE_ID)

                await col.update_one(
                    {"_id": doc["_id"]}, {"$set": {"topgg_vote_expires": 0}}
                )
                if member := guild.get_member(doc["_id"]):
                    await member.remove_roles(role, reason="Top.gg vote expired")

    @vote_reseter.before_loop
    async def before_vote_reseter(self):
        await self.bot.wait_until_ready()

    async def cog_unload(self) -> None:
        self.vote_reseter.cancel()

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is not None and message.guild.id == SUPPORT_SERVER_ID:
            created: datetime = getattr(message.author, "created_at", None)
            joined: datetime = getattr(message.author, "joined_at", None)
            if joined and created:
                seconds = (created - joined).total_seconds()
                if seconds >= 86400 and message.author._roles.has(QU_ROLE):
                    with suppress(discord.HTTPException):
                        await message.author.remove_roles(
                            discord.Object(id=QU_ROLE),
                            reason="Account age crosses 1d",
                        )

    @commands.group(
        name="sector", aliases=["sector1729", "sector17"], invoke_without_command=True
    )
    async def sector_17_29(self, ctx: Context):
        """Commands related to SECTOR 17-29"""
        if not ctx.invoked_subcommand:
            await ctx.bot.invoke_help_command(ctx)

    @sector_17_29.command(name="info", aliases=["about"])
    @in_support_server()
    async def sector_17_29_about(self, ctx: Context):
        """Information about the SECTOR 17-29"""
        description = (
            f"SECTOR 17-29 is support server of the bot (Parrot) and formely a "
            f"community server for the stream Beasty Stats.\n"
            f"[Click here]({self.bot.support_server}) to join the server"
        )
        await ctx.send(embed=discord.Embed(description=description))

    @sector_17_29.command(name="color")
    @in_support_server()
    async def sector_17_29_color(self, ctx: Context, *, color: Optional[str] = None):
        """Assign yourself color role"""
        if not color:
            return

        role = discord.utils.get(
            ctx.bot.server.roles, name=f"[SELF] - COLOR {color.upper()}"
        )
        if role is None:
            await ctx.error(f"{ctx.author.mention} no color named {color}!")
            return

        if ctx.author._roles.has(role.id):
            return await ctx.wrong()

        await ctx.author.add_roles(role, reason="Color role added")
        await ctx.tick()

    @sector_17_29.command(name="uncolor")
    @in_support_server()
    async def sector_17_29_uncolor(self, ctx: Context, *, color: Optional[str] = None):
        """Unassign yourself color role"""
        if not color:
            return

        role = discord.utils.get(
            ctx.bot.server.roles, name=f"[SELF] - COLOR {color.upper()}"
        )
        if role is None:
            await ctx.error(f"{ctx.author.mention} no color named {color}!")
            return

        if ctx.author._roles.has(role.id):
            await ctx.author.remove_roles(role, reason="Color role removed")
            await ctx.tick()
            return

        await ctx.wrong()

    @sector_17_29.command(name="role")
    @in_support_server()
    async def sector_17_29_role(self, ctx: Context, *, role: Optional[discord.Role]):
        """Assign yourself role"""
        if not role:
            await ctx.error(f"{ctx.author.mention} that role do not exists")
            return

        if not role.name.startswith("[SELF]"):
            await ctx.error(
                f"{ctx.author.roles} you don't have permission to assign yourself that role"
            )
            return

        if ctx.author._roles.has(role.id):
            await ctx.error(f"{ctx.author.mention} you already have that role")
            return

        await ctx.author.add_roles(role, reason="Self role - Role")
        await ctx.tick()

    @sector_17_29.command(name="unrole")
    @in_support_server()
    async def sector_17_29_unrole(self, ctx: Context, *, role: Optional[discord.Role]):
        """Unassign yourself role"""
        if not role:
            await ctx.error(f"{ctx.author.mention} that role do not exists")
            return

        if role.id not in self.__assignable_roles:
            await ctx.error(
                f"{ctx.author.mention} you don't have permission to unassign yourself that role"
            )
            return

        if not ctx.author._roles.has(role.id):
            await ctx.error(f"{ctx.author.mention} you do not have that role")
            return

        await ctx.author.remove_roles(role, reason="Self role - Unrole")
        await ctx.tick()
