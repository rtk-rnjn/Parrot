from __future__ import annotations

from collections import defaultdict
import re
from cogs.cc.method import CustomCommandsExecutionOnJoin, CustomCommandsExecutionOnMsg, CustomCommandsExecutionOnReaction
import importlib

from core import Parrot, Context, Cog

import discord
from discord.ext import commands
from cogs.cc import method
importlib.reload(method)

BUCKET = {
    "channel": commands.BucketType.channel,
    "guild": commands.BucketType.guild,
    "member": commands.BucketType.member,
}

TEST_GUILD = [746337818388987967, 741614680652644382]
MAGICAL_WORD_REGEX = r"(__)([a-z]+)(__)"
TRIGGER_TYPE = [
    "on_message",
    "reaction_add",
    "reaction_remove",
    "reaction_add_or_remove",
    "message_edit",
    "member_join",
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


class CCFlag(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str
    name: str
    help: str
    trigger_type: str = "command"

    requied_role: discord.Role = None
    ignored_role: discord.Role = None

    requied_channel: discord.TextChannel = None
    ignored_channel: discord.TextChannel = None
    

class CustomCommand(Cog):
    def __init__(self, bot: Parrot,):
        self.bot = bot
        def default_value(): return 0
        self.default_dict = defaultdict(default_value)

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    async def cc(self, ctx: Context):
        """
        The feture is in Beta (still in Testing). May get bugs/errors.
        """
        return await self.bot.invoke_help_command(ctx)
    
    @cc.command(name="create")
    @commands.has_permissions(manage_guild=True)
    async def cc_create(self, ctx: Context, *, flags: CCFlag):
        """To create custom commands"""
        if flags.code.startswith('```py') and flags.code.endswith('```'):
            code = flags.code[5:-3]
        elif flags.code.startswith('```') and flags.code.endswith('```'):
            code = flags.code[3:-3]
        else:
            code = flags.code

        if re.findall(MAGICAL_WORD_REGEX, code):
            review_needed = True
        else:
            review_needed = False

        if flags.name.startswith('`') and flags.name.endswith('`'):
            name = flags.name[1:-1]
        else:
            name = flags.name

        if flags.help.startswith('```') and flags.help.endswith('```'):
            help_ = flags.help[3:-3]
        elif flags.help.startswith('`') and flags.help.endswith('`'):
            help_ = flags.help[1:-1]
        else:
            help_ = flags.help

        if flags.trigger_type.lower() not in TRIGGER_TYPE:
            raise commands.BadArgument(f"Trigger type must be one of {', '.join(TRIGGER_TYPE)}")

        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "commands": {
                        "code": code,
                        "name": name,
                        "help": help_,
                        "review_needed": review_needed,
                        "trigger_type": flags.trigger_type.lower(),
                        "requied_role": flags.requied_role.id if flags.requied_role else None,
                        "ignored_role": flags.ignored_role.id if flags.ignored_role else None,
                        "requied_channel": flags.requied_channel.id if flags.requied_channel else None,
                        "ignored_channel": flags.ignored_channel.id if flags.ignored_channel else None,
                    }
                }
            }, upsert=True
        )
        await ctx.send(f"{ctx.author.mention} Custom command `{name}` created.")

    @cc.command(name="delete")
    @commands.has_permissions(manage_guild=True)
    async def cc_delete(self, ctx: Context, *, name: str):
        """To delete custom commands"""
        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id},
            {
                "$pull": {
                    "commands": {
                        "name": name
                    }
                }
            }
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
            description="\n".join([f"`{command.get('name')}`" for command in commands])
        )
        await ctx.send(embed=embed)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        if message.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": message.guild.id, "commands.trigger_type": "on_message", "commands.review_needed": False},
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command.get("trigger_type") == "on_message" and not command["review_needed"] and (
                            self.check_requirements(message=message, **command
                        )
                    )
                ):

                    CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                    await CC.execute(command.get("code"))

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        message = after

        if message.author.bot:
            return

        if not message.guild:
            return

        if before.content == after.content:
            return

        if message.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": message.guild.id, "commands.trigger_type": "message_edit", "commands.review_needed": False},
        ):

            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] == "on_message" and not command["review_needed"] and (
                        self.check_requirements(message=message, **command)
                    )
                ):
                    CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                    await CC.execute(command.get("code"))

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        message = reaction.message

        if message.author.bot:
            return

        if not message.guild:
            return

        if message.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "$or": [
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_add", "commands.review_needed": False},
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_add_or_remove", "commands.review_needed": False}
                ]
            }
        ):

            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] in {"reaction_add", "reaction_add_or_remove"} and not command["review_needed"] and (
                        self.check_requirements(message=message, **command)
                    )
                ):
                    CC = CustomCommandsExecutionOnReaction(self.bot, message, user, reaction_type="add")
                    await CC.execute(command.get("code"))

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        message = reaction.message

        if message.author.bot:
            return
        if not message.guild:
            return

        if message.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "$or": [
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_remove", "commands.review_needed": False},
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_add_or_remove", "commands.review_needed": False}
                ]
            }
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] in {"reaction_remove", "reaction_add_or_remove"} and not command["review_needed"] and (
                        self.check_requirements(message=message, **command)
                    )
                ):
                    CC = CustomCommandsExecutionOnReaction(self.bot, message, user, reaction_type="remove")
                    await CC.execute(command.get("code"))
    
    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": member.guild.id, "commands.trigger_type": "member_join", "commands.review_needed": False},
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"] == "member_join" and not command["review_needed"] and (
                        self.check_requirements(member=member, **command)
                    )
                ):
                    CC = CustomCommandsExecutionOnJoin(self.bot, member)
                    await CC.execute(command.get("code"))
    
    def check_requirements(
        self,
        *,
        message: discord.Message,
        ignored_role: int=None,
        required_role: int=None,
        required_channel: int=None,
        ignored_channel: int=None,
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