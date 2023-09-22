from __future__ import annotations

import asyncio
import random
from contextlib import suppress
from typing import Annotated

from pymongo import ReturnDocument
from tabulate import tabulate

import discord
from core import Cog, Context, Parrot
from core import MongoCollection as Collection
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.rankcard import rank_card
from utilities.robopages import SimplePages


class Leveling(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.message_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.member)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{CHART WITH UPWARDS TREND}")

    @commands.command(aliases=["level"])
    @commands.bot_has_permissions(attach_files=True)
    async def rank(self, ctx: Context, *, member: discord.Member = None):
        """To get the level of the user."""
        member = member or ctx.author
        try:
            enable = self.bot.guild_configurations_cache[ctx.guild.id]["leveling"]["enable"]
            if not enable:
                return await ctx.send(f"{ctx.author.mention} leveling system is disabled in this server")
        except KeyError:
            return await ctx.send(f"{ctx.author.mention} leveling system is disabled in this server")
        else:
            collection = self.bot.guild_level_db[f"{member.guild.id}"]
            if data := await collection.find_one_and_update(
                {"_id": member.id},
                {"$inc": {"xp": 0}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            ):
                level = int((data["xp"] // 42) ** 0.55)
                xp = await self.__get_required_xp(level + 1)
                rank = await self.__get_rank(collection=collection, member=member) or 0
                file = await asyncio.to_thread(
                    rank_card,
                    level,
                    rank,
                    member,
                    current_xp=data["xp"],
                    custom_background="#000000",
                    xp_color="#FFFFFF",
                    next_level_xp=xp,
                )
                await ctx.reply(file=file)
                return
            if ctx.author.id == member.id:
                return await ctx.reply(f"{ctx.author.mention} you don't have any xp yet. Consider sending some messages")
            return await ctx.reply(f"{ctx.author.mention} **{member}** don't have any xp yet.")

    @commands.command(aliases=["leaderboard"])
    async def lb(self, ctx: Context, *, limit: int | None = None):
        """To display the Leaderboard."""
        limit = limit or 10
        collection = self.bot.guild_level_db[f"{ctx.guild.id}"]
        entries = await self.__get_entries(collection=collection, limit=limit, guild=ctx.guild)
        if not entries:
            return await ctx.send(f"{ctx.author.mention} there is no one in the leaderboard")
        pages = SimplePages(entries, ctx=ctx, per_page=10)
        await pages.start()

    async def __get_required_xp(self, level: int) -> int:
        xp = 0
        while True:
            xp += 12
            lvl = int((xp // 42) ** 0.55)
            if lvl == level:
                return xp
            await asyncio.sleep(0)

    async def __get_rank(self, *, collection: Collection, member: discord.Member) -> int:  # type: ignore
        countr = 0

        # you can't use `enumerate`
        async for data in collection.find({}, sort=[("xp", -1)]):
            countr += 1
            if data["_id"] == member.id:  # type: ignore
                return countr

    async def __get_entries(self, *, collection: Collection, limit: int, guild: discord.Guild):
        ls = []
        async for data in collection.find({}, limit=limit, sort=[("xp", -1)]):
            if member := await self.bot.get_or_fetch_member(guild, data["_id"]):  # type: ignore
                ls.append(f"{member} (`{member.id}`)")
        return ls

    @commands.group(name="leveling", aliases=["ranking"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def leveling(self, ctx: Context, toggle: Annotated[bool, convert_bool] = True):
        """To configure leveling."""
        if not ctx.invoked_subcommand:
            await self.bot.guild_configurations.update_one({"_id": ctx.guild.id}, {"$set": {"leveling.enable": toggle}})
            await ctx.reply(f"{ctx.author.mention} set leveling system to: **{toggle}**")

    @leveling.command(name="show")
    @commands.has_permissions(administrator=True)
    async def leveling_show(self, ctx: Context):
        """To show leveling system."""
        try:
            leveling: dict = self.bot.guild_configurations_cache[ctx.guild.id]["leveling"]
        except KeyError:
            return await ctx.reply(f"{ctx.author.mention} leveling system is not set up yet!")
        reward: list[dict[str, int]] = leveling.get("reward", [])
        rwrd_tble = []
        for i in reward:
            role = ctx.guild.get_role(i["role"]) or None
            rwrd_tble.append([i["lvl"], role.name if role else None])
        ignored_roles = ", ".join(
            [str(ctx.guild.get_role(r)) for r in leveling.get("ignore_role", []) if ctx.guild.get_role(r)],
        )
        ignored_channel = ", ".join(
            [str(ctx.guild.get_channel(r)) for r in leveling.get("ignore_channel", []) if ctx.guild.get_channel(r)],
        )

        await ctx.reply(
            f"""Configuration of this server [leveling system]:
`Enabled :` **{leveling.get("enable", False)}**
`Channel :` **{getattr(ctx.guild.get_channel(leveling.get("channel", 0)), "name", "None")}**
`Ignore Roles   :` **{ignored_roles}**
`Ignore Channels:` **{ignored_channel}** ```
{str(tabulate(rwrd_tble, headers=["Level", "Role"], tablefmt="pretty"))}
```""",
        )

    @leveling.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def leveling_channel(self, ctx: Context, *, channel: discord.TextChannel = None):
        """To configure leveling channel."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"leveling.channel": channel.id if channel else None}},
        )
        if channel:
            await ctx.reply(f"{ctx.author.mention} all leveling like annoucement will posted in {channel.mention}")
            return
        await ctx.reply(f"{ctx.author.mention} reset annoucement channel for the leveling")

    @leveling.group(name="ignore", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def leveling_ignore_set(self, ctx: Context):
        """To configure the ignoring system of leveling."""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @leveling_ignore_set.command(name="role")
    @commands.has_permissions(administrator=True)
    async def leveling_ignore_role(self, ctx: Context, *, role: discord.Role):
        """To configure leveling ignore role."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"leveling.ignore_role": role.id}},
        )
        await ctx.reply(f"{ctx.author.mention} all leveling for role will be ignored **{role.name}**")

    @leveling_ignore_set.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def leveling_ignore_channel(self, ctx: Context, *, channel: discord.TextChannel):
        """To configure leveling ignore channel."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"leveling.ignore_channel": channel.id}},
        )
        await ctx.reply(f"{ctx.author.mention} all leveling will be ignored in **{channel.mention}**")

    @leveling.group(name="unignore", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def leveling_unignore_set(self, ctx: Context):
        """To configure the ignoring system of leveling."""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @leveling_unignore_set.command(name="role")
    @commands.has_permissions(administrator=True)
    async def leveling_unignore_role(self, ctx: Context, *, role: discord.Role):
        """To configure leveling unignore role."""
        update_result = await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$pull": {"leveling.ignore_role": role.id}},
        )
        if update_result.modified_count == 0:
            return await ctx.reply(f"{ctx.author.mention} **{role.name}** is not in the ignore list")

        await ctx.reply(f"{ctx.author.mention} removed **{role.name}** from ignore list.")

    @leveling_unignore_set.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def leveling_unignore_channel(self, ctx: Context, *, channel: discord.TextChannel):
        """To configure leveling ignore channel."""
        update_result = await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$pull": {"leveling.ignore_channel": channel.id}},
        )
        if update_result.modified_count == 0:
            return await ctx.reply(f"{ctx.author.mention} **{channel.mention}** is not in the ignore list")

        await ctx.reply(f"{ctx.author.mention} removed **{channel.mention}** from ignore list.")

    @leveling.command(name="addreward")
    @commands.has_permissions(administrator=True)
    async def level_reward_add(self, ctx: Context, level: int, role: discord.Role = None):
        """To add the level reward."""
        if _ := await self.bot.guild_configurations.find_one({"_id": ctx.guild.id, "leveling.reward": level}):
            role = ctx.guild.get_role(_["role"])
            return await ctx.error(
                f"{ctx.author.mention} conflit in adding {level}. It already exists with reward of role ID: **{getattr(role, 'name', 'Role Not Found')}**",
            )
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"leveling.reward": {"lvl": level, "role": role.id if role else None}}},
        )
        if not role:
            await ctx.reply(f"{ctx.author.mention} reset the role on level **{level}**")
            return
        await ctx.reply(f"{ctx.author.mention} set role {role.name} at level **{level}**")

    @leveling.command(name="removereward")
    @commands.has_permissions(administrator=True)
    async def level_reward_remove(self, ctx: Context, level: int):
        """To remove the level reward."""
        await self.bot.guild_configurations.update_one({"_id": ctx.guild.id}, {"$pull": {"leveling.reward": {"lvl": level}}})
        await ctx.reply(f"{ctx.author.mention} updated/removed reward at level: **{level}**")

    async def _on_message_leveling(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        assert isinstance(message.author, discord.Member)

        bucket: commands.Cooldown | None = self.message_cooldown.get_bucket(message)
        if bucket is None:
            return

        if bucket.update_rate_limit():
            return

        try:
            enable: bool = self.bot.guild_configurations_cache[message.guild.id]["leveling"]["enable"]
        except KeyError:
            return

        if not enable:
            return

        try:
            role: list[int] = self.bot.guild_configurations_cache[message.guild.id]["leveling"]["ignore_role"] or []
        except KeyError:
            role = []

        if any(message.author.get_role(r) for r in role):
            return

        try:
            ignore_channel: list = self.bot.guild_configurations_cache[message.guild.id]["leveling"]["ignore_channel"] or []
        except KeyError:
            ignore_channel = []

        if message.channel.id in ignore_channel:
            return

        await self._add_xp(member=message.author, xp=random.randint(10, 15), msg=message)

        try:
            announce_channel: int = self.bot.guild_configurations_cache[message.guild.id]["leveling"]["channel"] or 0
        except KeyError:
            return
        else:
            collection = self.bot.guild_level_db[f"{message.guild.id}"]
            ch: discord.TextChannel | None = await self.bot.getch(
                self.bot.get_channel,  # type: ignore
                self.bot.fetch_channel,  # type: ignore
                announce_channel,
                force_fetch=True,
            )
            if ch and (
                data := await collection.find_one_and_update(
                    {"_id": message.author.id},
                    {"$inc": {"xp": 0}},
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                )
            ):
                level = int((data["xp"] // 42) ** 0.55)
                xp = await self.__get_required_xp(level + 1)
                rank = await self.__get_rank(collection=collection, member=message.author)
                file: discord.File = await asyncio.to_thread(
                    rank_card,
                    level,
                    rank,
                    message.author,
                    current_xp=data["xp"],
                    custom_background="#000000",
                    xp_color="#FFFFFF",
                    next_level_xp=xp,
                )
                await message.reply("GG! Level up!", file=file)

    async def _add_xp(
        self,
        *,
        member: discord.Member,
        xp: int,
        msg: discord.Message,
    ):
        collection = self.bot.guild_level_db[f"{member.guild.id}"]
        data = await collection.find_one_and_update(
            {"_id": member.id},
            {"$inc": {"xp": xp}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        level = int((data["xp"] // 42) ** 0.55)
        await self._add_role_xp(msg.guild.id, level, msg)

    async def _add_role_xp(self, guild_id: int, level: int, msg: discord.Message):
        assert isinstance(msg.author, discord.Member)
        try:
            ls = self.bot.guild_configurations_cache[guild_id]["leveling"]["reward"]
        except KeyError:
            return

        for reward in ls:
            if reward["lvl"] <= level:
                await self.__add_roles(
                    msg.author,
                    discord.Object(id=reward["role"]),
                    reason=f"Level Up role! On reaching: {level}",
                )

    async def __add_roles(
        self,
        member: discord.Member,
        role: discord.abc.Snowflake,
        reason: str | None = None,
    ):
        with suppress(discord.Forbidden, discord.HTTPException):
            await member.add_roles(role, reason=reason)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._on_message_leveling(message)

    @Cog.listener()
    async def on_command(self, ctx: Context):
        if ctx.command.cog.qualified_name == "Leveling":
            self.bot.update_server_config_cache.start(ctx.guild.id)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Leveling(bot))
