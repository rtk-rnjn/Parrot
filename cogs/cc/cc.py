from __future__ import annotations
import asyncio

from collections import defaultdict
import re
from typing import Optional, Union
from cogs.cc.method import (
    CustomCommandsExecutionOnJoin,
    CustomCommandsExecutionOnMsg,
    CustomCommandsExecutionOnReaction,
    CustomCommandsExecutionOnRemove,
    indent,
)
from cogs.cc import method
import importlib

from core import Parrot, Context, Cog

import discord
from discord.ext import commands

importlib.reload(method)

BUCKET = {
    "channel": commands.BucketType.channel,
    "guild": commands.BucketType.guild,
    "member": commands.BucketType.member,
}

MAGICAL_WORD_REGEX = r"(__)([a-z]+)(__)"
TRIGGER_TYPE = [
    "on_message",
    "reaction_add",
    "reaction_remove",
    "reaction_add_or_remove",
    "message_edit",
    "member_join",
    "member_remove",
]

ERROR_ON_MAX_CONCURRENCY = """
```ini
[Failed processing the command {} in the guild {} due to the max concurrency limit]
```
"""
ERROR_ON_REVIEW_REQUIRED = """
```ini
[Failed processing the command {} in the guild {} due to the review required]
```
"""


class ContentCode:
    def __init__(self, argument: str):
        try:
            block, code = argument.split("\n", 1)
        except ValueError:
            self.source = argument
            self.language = None
        else:
            if not block.startswith("```") and not code.endswith("```"):
                self.source = argument
                self.language = None
            else:
                self.language = block[3:]
                self.source = code.rstrip("`").replace("```", "")


class CCFlag(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = None
    # name: str = None
    trigger_type: str = "on_message"

    requied_role: discord.Role = None
    ignored_role: discord.Role = None

    requied_channel: discord.TextChannel = None
    ignored_channel: discord.TextChannel = None


class CustomCommand(Cog):
    def __init__(
        self,
        bot: Parrot,
    ) -> None:
        self.bot = bot

        def default_value():
            return 0

        self.default_dict = defaultdict(default_value)
        self.data = {}

    async def cog_load(self):
        async for data in self.bot.mongo.cc.commands.find({}):
            data[f"{data['_id']}"] = data

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    async def cc(self, ctx: Context, *, name: str = None):
        """
        The feture is in Beta (still in Testing). May get bugs/errors.
        """
        if ctx.invoked_subcommand is None:
            if data := await self.bot.mongo.cc.commands.find_one(
                {"_id": ctx.guild.id, "commands.name": name},
                {"_id": 0, "commands.$": 1},
            ):
                for command in data.get("commands", []):
                    if command.get("name") == name:
                        embed = discord.Embed(
                            title="Custom Command",
                            color=self.bot.color,
                            description=f"```python\n{command['code']}\n```",
                        )
                        embed.set_footer(
                            text=f"Command name: {command['name']} | Trigger type: {command['trigger_type']}"
                        )
                        return await ctx.send(embed=embed)

    @cc.command(name="review", aliases=["approve"], hidden=True)
    @commands.is_owner()
    async def cc_review(
        self, ctx: Context, name: str, guild: Union[discord.Guild, int]
    ):
        """To review the code"""
        guild = guild.id if isinstance(guild, discord.Guild) else guild

        def check_reaction(reaction, user) -> bool:
            return user.id == ctx.author.id

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": guild, "commands.review_needed": True},
            {"_id": 0, "commands.$": 1},
        ):
            for command in data.get("commands", []):
                if command.get("name") == name:
                    embed = discord.Embed(
                        title="Custom Command",
                        color=self.bot.color,
                        description=f"```python\n{command['code']}\n```",
                    )
                    embed.set_footer(
                        text=f"Command name: {command['name']} | Trigger type: {command['trigger_type']}"
                    )
                    msg = await ctx.send(embed=embed)
                    await ctx.bulk_add_reactions(
                        msg, "\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"
                    )
                    r, u = await self.bot.wait_for("reaction_add", check=check_reaction)
                    if r.emoji == "\N{WHITE HEAVY CHECK MARK}":
                        await self.bot.mongo.cc.commands.update_one(
                            {"_id": guild, "commands.name": name},
                            {"$set": {"commands.$.review_needed": False}},
                        )
                        return await ctx.send("Approved")
                    return await ctx.send("Rejected")
        return await ctx.send(f"{ctx.author.mention} no codes to review at this time")

    @cc.command(name="make")
    @commands.has_permissions(manage_guild=True)
    async def cc_make(
        self,
        ctx: Context,
    ):
        """To create custom commands in interactive format"""

        def check(msg: discord.Message) -> bool:
            return msg.author == ctx.author and msg.channel == ctx.channel

        async def wait_for(**kwargs) -> Optional[discord.Message]:
            try:
                return await self.bot.wait_for("message", **kwargs)
            except asyncio.TimeoutError:
                raise commands.BadArgument("Timed out waiting for input")

        await ctx.send(f"{ctx.author.mention} Please enter the name of the command")
        name = await wait_for(check=check)

        await ctx.send(
            f"{ctx.author.mention} Please enter the trigger type."
            f"\n(on_message, reaction_add, reaction_remove, reaction_add_or_remove, message_edit, member_join, member_remove)"
        )
        trigger_type = await wait_for(check=check)
        if trigger_type.content not in TRIGGER_TYPE:
            raise commands.BadArgument("Invalid trigger type")

        await ctx.send(f"{ctx.author.mention} Please enter the code of the command.")
        code = await wait_for(check=check)
        code = ContentCode(code.content)
        code = code.source

        if trigger_type.content.lower() in ("on_message", "on_message_edit"):
            code = indent(code, "MESSAGE")
        elif trigger_type.content.lower() in (
            "reaction_add_or_remove",
            "reaction_add",
            "reaction_remove",
        ):
            code = indent(code, "REACTION")
        elif trigger_type.content.lower() in ("member_join", "member_remove"):
            code = indent(code, "MEMBER")

        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id, "commands.name": name.content},
            {
                "$addToSet": {
                    "commands": {
                        "name": name.content,
                        "trigger_type": trigger_type.content.lower(),
                        "code": code,
                        "review_needed": bool(re.findall(MAGICAL_WORD_REGEX, code)),
                        "trigger_type": trigger_type.lower(),
                        "requied_role": None,
                        "ignored_role": None,
                        "requied_channel": None,
                        "ignored_channel": None,
                    }
                }
            },
            upsert=True,
        )
        if bool(re.findall(MAGICAL_WORD_REGEX, code)):
            await self.bot.author_obj.send(
                f"There is an request from `{ctx.author}` to create a custom command with the name `{name}` in the guild {ctx.guild.name} (`{ctx.guild.id}`).\n"
                f"Potential breach detected in the code. Please review the code and confirm the request.\n",
                embed=discord.Embed(
                    title="Review needed",
                    description=f"```py\n{code}\n```",
                ),
            )
            await ctx.send(
                f"{ctx.author.mention} your custom command code is under review."
            )
        await ctx.send(f"{ctx.author.mention} Custom command `{name}` created.")

    @cc.command(name="update")
    @commands.has_permissions(manage_guild=True)
    async def cc_create(self, ctx: Context, name: str, *, flags: CCFlag):
        """To create custom commands"""
        payload = {}

        if flags.trigger_type:
            if flags.trigger_type.lower() not in TRIGGER_TYPE:
                raise commands.BadArgument(
                    f"Trigger type must be one of {', '.join(TRIGGER_TYPE)}"
                )
            payload["trigger_type"] = flags.trigger_type.lower()

        if flags.code:
            code = ContentCode(flags.code)
            code = code.source

            if flags.trigger_type.lower() in ("on_message", "on_message_edit"):
                code = indent(code, "MESSAGE")
            elif flags.trigger_type.lower() in (
                "reaction_add_or_remove",
                "reaction_add",
                "reaction_remove",
            ):
                code = indent(code, "REACTION")
            elif flags.trigger_type.lower() in ("member_join", "member_remove"):
                code = indent(code, "MEMBER")
            payload["code"] = code

            review_needed = bool(re.findall(MAGICAL_WORD_REGEX, code))

            if review_needed:
                await self.bot.author_obj.send(
                    f"There is an request from `{ctx.author}` to create a custom command with the name `{flags.name}` in the guild {ctx.guild.name} (`{ctx.guild.id}`).\n"
                    f"Potential breach detected in the code. Please review the code and confirm the request.\n",
                    embed=discord.Embed(
                        title="Review needed",
                        description=f"```py\n{code}\n```",
                    ),
                )
                await ctx.send(
                    f"{ctx.author.mention} your custom command code is under review."
                )
                payload["review_needed"] = review_needed

        if flags.requied_role:
            payload["requied_role"] = flags.requied_role.id

        if flags.ignored_role:
            payload["ignored_role"] = flags.ignored_role.id

        if flags.requied_channel:
            payload["requied_channel"] = flags.requied_channel.id

        if flags.ignored_channel:
            payload["ignored_channel"] = flags.ignored_channel.id

        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id, "commands.name": name},
            {"$set": {"commands.$.name": {**payload}}},
        )
        await ctx.send(f"{ctx.author.mention} Custom command `{name}` updated.")

    @cc.command(name="delete")
    @commands.has_permissions(manage_guild=True)
    async def cc_delete(self, ctx: Context, *, name: str):
        """To delete custom commands"""
        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"commands": {"name": name}}}
        )
        await ctx.send(f"{ctx.author.mention} Custom command of id `{name}` deleted.")

    @cc.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def cc_list(self, ctx: Context):
        """To list custom commands"""
        commands = await self.bot.mongo.cc.commands.find_one({"_id": ctx.guild.id})
        if not commands:
            return await ctx.send(f"{ctx.author.mention} No custom commands found.")
        commands = commands.get("commands", [])
        if not commands:
            return await ctx.send(f"{ctx.author.mention} No custom commands found.")
        embed = discord.Embed(
            title=f"Custom commands in {ctx.guild.name}",
            description="\n".join([f"`{command.get('name')}`" for command in commands]),
        )
        await ctx.send(embed=embed)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "_id": message.guild.id,
                "commands.trigger_type": "on_message",
                "commands.review_needed": False,
            },
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command.get("trigger_type") == "on_message"
                    and not command["review_needed"]
                    and (self.check_requirements(message=message, **command))
                ):

                    CC = CustomCommandsExecutionOnMsg(
                        self.bot,
                        message,
                    )
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        message = after

        if message.author.bot:
            return

        if not message.guild:
            return

        if before.content == after.content:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "_id": message.guild.id,
                "commands.trigger_type": "message_edit",
                "commands.review_needed": False,
            },
        ):

            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] == "on_message"
                    and not command["review_needed"]
                    and (self.check_requirements(message=message, **command))
                ):
                    CC = CustomCommandsExecutionOnMsg(
                        self.bot,
                        message,
                    )
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        message = reaction.message

        if message.author.bot:
            return

        if not message.guild:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "$or": [
                    {
                        "_id": message.guild.id,
                        "commands.trigger_type": "reaction_add",
                        "commands.review_needed": False,
                    },
                    {
                        "_id": message.guild.id,
                        "commands.trigger_type": "reaction_add_or_remove",
                        "commands.review_needed": False,
                    },
                ]
            }
        ):

            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"]
                    in {"reaction_add", "reaction_add_or_remove"}
                    and not command["review_needed"]
                    and (self.check_requirements(message=message, **command))
                ):
                    CC = CustomCommandsExecutionOnReaction(
                        self.bot, message, user, reaction_type="add"
                    )
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        message = reaction.message

        if message.author.bot:
            return
        if not message.guild:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "$or": [
                    {
                        "_id": message.guild.id,
                        "commands.trigger_type": "reaction_remove",
                        "commands.review_needed": False,
                    },
                    {
                        "_id": message.guild.id,
                        "commands.trigger_type": "reaction_add_or_remove",
                        "commands.review_needed": False,
                    },
                ]
            }
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"]
                    in {"reaction_remove", "reaction_add_or_remove"}
                    and not command["review_needed"]
                    and (self.check_requirements(message=message, **command))
                ):
                    CC = CustomCommandsExecutionOnReaction(
                        self.bot, message, user, reaction_type="remove"
                    )
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    @Cog.listener()
    async def on_member_join(self, member):
        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "_id": member.guild.id,
                "commands.trigger_type": "member_join",
                "commands.review_needed": False,
            },
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] == "member_join"
                    and not command["review_needed"]
                ):
                    CC = CustomCommandsExecutionOnJoin(self.bot, member)
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    @Cog.listener()
    async def on_member_remove(self, member):
        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "_id": member.guild.id,
                "commands.trigger_type": "member_remove",
                "commands.review_needed": False,
            },
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] == "member_remove"
                    and not command["review_needed"]
                ):
                    CC = CustomCommandsExecutionOnRemove(self.bot, member)
                    await CC.execute(command.get("code"))
                await asyncio.sleep(0)

    def check_requirements(
        self,
        *,
        message: discord.Message,
        ignored_role: int = None,
        required_role: int = None,
        required_channel: int = None,
        ignored_channel: int = None,
        **kwargs,
    ) -> bool:
        if message.author._roles.has(required_role or 0):
            return True

        if message.author._roles.has(ignored_role or 0):
            return False

        if message.channel.id == (ignored_channel or 0):
            return False

        if message.channel.id == (required_channel or 0):
            return True

        return True
