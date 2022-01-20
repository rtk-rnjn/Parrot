from __future__ import annotations

import discord
import traceback
import math
import random
import aiohttp
from discord.ext import commands

from utilities.exceptions import ParrotCheckFaliure
from utilities.database import cmd_increment, parrot_db
from core import Parrot, Context, Cog

with open("extra/quote.txt") as f:
    quote = f.read()

quote = quote.split("\n")
QUESTION_MARK = "\N{BLACK QUESTION MARK ORNAMENT}"


class ErrorView(discord.ui.View):
    def __init__(self, author_id, *, ctx: Context = None, error=None):
        super().__init__(timeout=300.0)
        self.author_id = author_id
        self.ctx = ctx
        self.error = error

    async def paste(self, text):
        """Return an online bin of given text"""
        async with aiohttp.ClientSession() as aioclient:
            post = await aioclient.post("https://hastebin.com/documents", data=text)
            if post.status == 200:
                response = await post.text()
                return f"https://hastebin.com/{response[8:-2]}"

            # Rollback bin
            post = await aioclient.post(
                "https://bin.readthedocs.fr/new", data={"code": text, "lang": "txt"}
            )
            if post.status == 200:
                return str(post.url)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message(
            "You can't interact with this button", ephemeral=True
        )
        return False

    @discord.ui.button(label="Show full error", style=discord.ButtonStyle.green)
    async def show_full_traceback(
        self, button: discord.ui.button, interaction: discord.Interaction
    ):
        tb = traceback.format_exception(
            type(self.error), self.error, self.error.__traceback__
        )
        tbe = "".join(tb) + ""
        er = f"```py\nIgnoring exception in command {self.ctx.command.name}: {tbe}\n```"
        text = await self.paste(er)
        if len(er) < 1950:
            await interaction.response.send_message(er, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


class Cmd(Cog, command_attrs=dict(hidden=True)):
    """This category is of no use for you, ignore it."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["logging"]

    async def paste(self, text: str):
        """Return an online bin of given text"""
        async with aiohttp.ClientSession() as aioclient:
            post = await aioclient.post("https://hastebin.com/documents", data=text)
            if post.status == 200:
                response = await post.text()
                return f"https://hastebin.com/{response[8:-2]}"

            # Rollback bin
            post = await aioclient.post(
                "https://bin.readthedocs.fr/new", data={"code": text, "lang": "txt"}
            )
            if post.status == 200:
                return str(post.url)

    @Cog.listener()
    async def on_command(self, ctx: Context):
        """This event will be triggered when the command is being completed; triggered by [discord.User]!"""
        if ctx.author.bot:
            return
        await cmd_increment(ctx.command.qualified_name)

    @Cog.listener()
    async def on_command_completion(self, ctx: Context):
        """Only for logging"""
        if ctx.cog is None:
            return
        if ctx.cog.qualified_name.lower() == "mod":
            if data := await self.collection.find_one(
                {"_id": ctx.guild.id, "on_mod_command": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_mod_command"], session=self.bot.session
                )
                if webhook:
                    main_content = f"""**On Moderator Command**

`Mod    `: **{ctx.author}**
`Command`: **{ctx.command.qualified_name}**
`Content`: **{ctx.message.content}**
"""
                    await webhook.send(
                        content=main_content,
                        avatar_url=self.bot.user.avatar.url,
                        username=self.bot.user.name,
                    )

        if ctx.cog.qualified_name.lower() == "botconfig":
            if data := await self.collection.find_one(
                {"_id": ctx.guild.id, "on_config_command": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_config_command"], session=self.bot.session
                )
                if webhook:
                    main_content = f"""**On Config Command**

`Admin  `: **{ctx.author}**
`Command`: **{ctx.command.qualified_name}**
`Content`: **{ctx.message.content}**
"""
                    await webhook.send(
                        content=main_content,
                        avatar_url=self.bot.user.avatar.url,
                        username=self.bot.user.name,
                    )

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        # if command has local error handler, return
        if hasattr(ctx.command, "on_error"):
            return

        # get the original exception
        error = getattr(error, "original", error)

        ignore = (commands.CommandNotFound, discord.NotFound, discord.Forbidden)

        if isinstance(error, ignore):
            return

        ERROR_EMBED = discord.Embed()
        if isinstance(error, commands.BotMissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 2:
                fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            ERROR_EMBED.description = (
                f"Please provide the following permission(s) to the bot.```\n{fmt}```"
            )
            ERROR_EMBED.title = (
                f"{QUESTION_MARK} Bot Missing permissions {QUESTION_MARK}"
            )
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        # if isinstance(error, commands.DisabledCommand):
        #     ERROR_EMBED.description = f"This command has been disabled. Consider asking your Server Manager to fix this out"
        #     ERROR_EMBED.title = f"{QUESTION_MARK} Command Disabled {QUESTION_MARK}"
        #     return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.CommandOnCooldown):
            ERROR_EMBED.description = f"You are on command cooldown, please retry in **{math.ceil(error.retry_after)}**s"
            ERROR_EMBED.title = f"{QUESTION_MARK} Command On Cooldown {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.MissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            ERROR_EMBED.description = f"You need the following permission(s) to the run the command.```\n{fmt}```"
            ERROR_EMBED.title = f"{QUESTION_MARK} Missing permissions {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.MissingRole):
            missing = list(error.missing_role)
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            ERROR_EMBED.description = (
                f"You need the the following role(s) to use the command```\n{fmt}```"
            )
            ERROR_EMBED.title = f"{QUESTION_MARK} Missing Role {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.MissingAnyRole):
            missing = list(error.missing_roles)
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            ERROR_EMBED.description = (
                f"You need the the following role(s) to use the command```\n{fmt}```"
            )
            ERROR_EMBED.title = f"{QUESTION_MARK} Missing Role {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        # if isinstance(error, commands.NoPrivateMessage):
        #     ERROR_EMBED.description = f"This command cannot be used in direct messages. It can only be used in server"
        #     ERROR_EMBED.title = f"{QUESTION_MARK} No Private Message {QUESTION_MARK}"
        #     try:
        #         return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)
        #     except discord.Forbidden:
        #         pass
        #     return

        if isinstance(error, commands.NSFWChannelRequired):
            ERROR_EMBED.description = "This command will only run in NSFW marked channel. https://i.imgur.com/oe4iK5i.gif"
            ERROR_EMBED.title = f"{QUESTION_MARK} NSFW Channel Required {QUESTION_MARK}"
            ERROR_EMBED.set_image(url="https://i.imgur.com/oe4iK5i.gif")
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        # if isinstance(error, commands.NotOwner):
        #     ERROR_EMBED.description = f"You must have ownership of the bot to run `{ctx.command.qualified_name}`"
        #     ERROR_EMBED.title = f"{QUESTION_MARK} Not Owner {QUESTION_MARK}"
        #     return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.PrivateMessageOnly):
            ERROR_EMBED.description = "This comamnd will only work in DM messages"
            ERROR_EMBED.title = f"{QUESTION_MARK} Private Message Only {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.BadArgument):
            if isinstance(error, commands.MessageNotFound):
                ERROR_EMBED.description = (
                    "Message ID/Link you provied is either invalid or deleted"
                )
                ERROR_EMBED.title = f"{QUESTION_MARK} Message Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            if isinstance(error, commands.MemberNotFound):
                ERROR_EMBED.description = "Member ID/Mention/Name you provided is invalid or bot can not see that Member"
                ERROR_EMBED.title = f"{QUESTION_MARK} Member Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            if isinstance(error, commands.UserNotFound):
                ERROR_EMBED.description = "User ID/Mention/Name you provided is invalid or bot can not see that User"
                ERROR_EMBED.title = f"{QUESTION_MARK} User Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            if isinstance(error, commands.ChannelNotFound):
                ERROR_EMBED.description = "Channel ID/Mention/Name you provided is invalid or bot can not see that Channel"
                ERROR_EMBED.title = f"{QUESTION_MARK} Channel Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            if isinstance(error, commands.RoleNotFound):
                ERROR_EMBED.description = "Role ID/Mention/Name you provided is invalid or bot can not see that Role"
                ERROR_EMBED.title = f"{QUESTION_MARK} Role Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            if isinstance(error, commands.EmojiNotFound):
                ERROR_EMBED.description = "Emoji ID/Name you provided is invalid or bot can not see that Emoji"
                ERROR_EMBED.title = f"{QUESTION_MARK} Emoji Not Found {QUESTION_MARK}"
                return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

            ERROR_EMBED.description = f"{error}"
            ERROR_EMBED.title = f"{QUESTION_MARK} Bad Argument {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.MissingRequiredArgument):
            command = ctx.command
            ERROR_EMBED.description = f"Please use proper syntax.```\n{ctx.clean_prefix}{command.qualified_name}{'|' if command.aliases else ''}{'|'.join(command.aliases if command.aliases else '')} {command.signature}```"
            ERROR_EMBED.title = (
                f"{QUESTION_MARK} Missing Required Argument {QUESTION_MARK}"
            )
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.MaxConcurrencyReached):
            ERROR_EMBED.description = "This command is already running in this server/channel by you. You have wait for it to finish"
            ERROR_EMBED.title = (
                f"{QUESTION_MARK} Max Concurrenry Reached {QUESTION_MARK}"
            )
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, (commands.BadUnionArgument, commands.BadLiteralArgument)):
            ERROR_EMBED.description = f"`@Parrot {ctx.command}` for help"
            ERROR_EMBED.title = f"{QUESTION_MARK} Bad Argument {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, ParrotCheckFaliure):
            ERROR_EMBED.description = f"{error.__str__().format(ctx=ctx)}"
            ERROR_EMBED.title = f"{QUESTION_MARK} Unexpected Error {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        if isinstance(error, commands.CheckAnyFailure):
            ERROR_EMBED.description = " or ".join(
                [error.__str__().format(ctx=ctx) for error in error.errors]
            )
            ERROR_EMBED.title = f"{QUESTION_MARK} Unexpected Error {QUESTION_MARK}"
            return await ctx.reply(random.choice(quote), embed=ERROR_EMBED)

        ERROR_EMBED.description = f"For some reason **{ctx.command.qualified_name}** is not working. If possible report this error."
        ERROR_EMBED.title = (
            f"{QUESTION_MARK} Well this is embarrassing! {QUESTION_MARK}"
        )
        return await ctx.reply(
            random.choice(quote),
            embed=ERROR_EMBED,
            view=ErrorView(ctx.author.id, ctx=ctx, error=error),
        )


def setup(bot):
    bot.add_cog(Cmd(bot))
