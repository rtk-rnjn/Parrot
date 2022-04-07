from __future__ import annotations
from collections import defaultdict
import re
from cogs.cc.method import CustomCommandsExecutionOnJoin, CustomCommandsExecutionOnMsg

from core import Parrot, Context, Cog

import discord
from discord.ext import commands


BUCKET = {
    "channel": commands.BucketType.channel,
    "guild": commands.BucketType.guild,
    "member": commands.BucketType.member,
}

TEST_GUILD = [746337818388987967, 741614680652644382]
MAGICAL_WORD_REGEX = r"(__)([a-z]+)(__)"
TRIGGER_TYPE = [
    "command",
    "on_message",
    "regex",
    "bot_mention",
    "reaction_add",
    "reaction_remove",
    "reaction_add_or_remove",
    "message_edit",
    "member_join",
]


class CCFlag(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str
    name: str
    help: str
    trigger_type: str = "command"

    cd_per: int = 0
    cd_time: int = 0
    cd_bucket: str = None

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
                        "cd_per": flags.cd_per,
                        "cd_time": flags.cd_time,
                        "cd_bucket": flags.cd_bucket,
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
        await ctx.send(f"{ctx.author.mention} Custom command `{name}` deleted.")


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

        PREFIX = await self.bot.get_guild_prefixes(message.guild)

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": message.guild.id, "commands.trigger_type": "command", "commands.review_needed": False},
        ):
            if self.default_dict[message.guild.id] > 3:
                return
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command.get("trigger_type") == "command"
                ) and (
                    f'{PREFIX}{command.get("name")}'.split(' ')[0].casefold() == message.content.split(' ')[0].casefold()
                ):
                    CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                    self.default_dict[message.guild.id] += 1
                    await CC.execute(command.get("code"))
                    self.default_dict[message.guild.id] -= 1

                elif (
                    command.get("trigger_type") == "regex"
                ) and (
                    re.fullmatch(command.get("name"), message.content)
                ):
                    CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                    self.default_dict[message.guild.id] += 1
                    await CC.execute(command.get("code"))
                    self.default_dict[message.guild.id] -= 1

                elif (
                    command.get("trigger_type") == "on_message"
                ) and (
                    message.content.casefold() == command.get("name").casefold()
                ):
                    CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                    self.default_dict[message.guild.id] += 1
                    await CC.execute(command.get("code"))
                    self.default_dict[message.guild.id] -= 1

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
            if self.default_dict[message.guild.id] > 3:
                return
            commands = data.get("commands", [])
            for command in commands:
                CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                self.default_dict[message.guild.id] += 1
                await CC.execute(command.get("code"))
                self.default_dict[message.guild.id] -= 1

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
            if self.default_dict[message.guild.id] > 3:
                return

            commands = data.get("commands", [])
            for command in commands:
                CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                self.default_dict[message.guild.id] += 1
                await CC.execute(command.get("code"))
                self.default_dict[message.guild.id] -= 1

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
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_remove", "commands.review_needed": False},
                    {"_id": message.guild.id, "commands.trigger_type": "reaction_add_or_remove", "commands.review_needed": False}
                ]
            }
        ):
            if self.default_dict[message.guild.id] > 3:
                return
            commands = data.get("commands", [])
            for command in commands:
                CC = CustomCommandsExecutionOnMsg(self.bot, message,)
                self.default_dict[message.guild.id] += 1
                await CC.execute(command.get("code"))
                self.default_dict[message.guild.id] -= 1
    
    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id not in TEST_GUILD:
            return

        if data := await self.bot.mongo.cc.commands.find_one(
            {"_id": member.guild.id, "commands.trigger_type": "member_join", "commands.review_needed": False},
        ):
            if self.default_dict[member.guild.id] > 3:
                return
            commands = data.get("commands", [])
            for command in commands:
                CC = CustomCommandsExecutionOnJoin(self.bot, member,)
                self.default_dict[member.guild.id] += 1
                await CC.execute(command.get("code"))
                self.default_dict[member.guild.id] -= 1