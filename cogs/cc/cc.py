from __future__ import annotations
from cogs.cc.method import CustomCommandsExecutionOnMsg

from core import Parrot, Context, Cog

import discord
from discord.ext import commands


BUCKET = {
    "channel": commands.BucketType.channel,
    "guild": commands.BucketType.guild,
    "member": commands.BucketType.member,
}

class CCFlag(commands.FlagConverter):
    code: str
    name: str
    help: str
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
        if flags.code.startswith('```') and flags.code.endswith('```'):
            code = flags.code[3:-3]
        elif flags.code.startswith('```py') and flags.code.endswith('```'):
            code = flags.code[5:-3]
        else:
            code = flags.code

        if flags.name.startswith('`') and flags.name.endswith('`'):
            name = flags.name[1:-1]
        else:
            name = flags.name

        if flags.help.startswith('```') and flags.help.endswith('```'):
            help = flags.help[3:-3]
        elif flags.help.startswith('`') and flags.help.endswith('`'):
            help = flags.help[1:-1]
        else:
            help = flags.help
        
        await self.bot.mongo.cc.commands.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "commands": {
                        "code": code,
                        "name": name,
                        "help": help,
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
        CCExec = CustomCommandsExecutionOnMsg(self.bot, message)
