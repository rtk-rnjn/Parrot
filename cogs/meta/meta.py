from __future__ import annotations

from discord import __version__ as discord_version
from discord.ext import old_menus as menus
import discord
import typing
import asyncio
from discord.ext import commands

from time import time
from datetime import timedelta

from psutil import Process, virtual_memory
from platform import python_version

from utilities.config import VERSION, PRIVACY_POLICY
from utilities.buttons import Prompt

from core import Parrot, Context, Cog
from collections import Counter
from .robopage import RoboPages

import datetime
import inspect
import itertools
from typing import Any, Dict, List, Optional, Union


def format_dt(dt, style=None):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_relative(dt):
    return format_dt(dt, "R")


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        user_id = ctx.bot.user.id
        if argument.startswith((f"<@{user_id}>", f"<@!{user_id}>")):
            raise commands.BadArgument("That is a reserved prefix already in use.")
        return argument


class GroupHelpPageSource(menus.ListPageSource):
    def __init__(
        self,
        group: Union[commands.Group, Cog],
        commands: List[commands.Command],
        *,
        prefix: str,
    ):
        super().__init__(entries=commands, per_page=6)
        self.group = group
        self.prefix = prefix
        self.title = f"{self.group.qualified_name} Commands"
        self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            colour=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow(),
        )

        for command in commands:
            signature = f"{command.qualified_name} {command.signature}"
            embed.add_field(
                name=command.qualified_name,
                value=f"> `{signature}`\n{command.short_doc or 'No help given for the time being...'}",
                inline=False,
            )
        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_footer(
                text=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)"
            )

        return embed


class HelpSelectMenu(discord.ui.Select["HelpMenu"]):
    def __init__(self, commands: Dict[Cog, List[commands.Command]], bot: Parrot):
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            row=0,
        )
        self.commands = commands
        self.bot = bot
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label="Index",
            emoji="\N{WAVING HAND SIGN}",
            value="__index",
            description="The help page showing how to use the bot.",
        )
        for cog, command_ in self.commands.items():
            if not command_:
                continue
            description = cog.description.split("\n", 1)[0] or None
            emoji = getattr(cog, "display_emoji", None)
            self.add_option(
                label=cog.qualified_name,
                value=cog.qualified_name,
                description=description,
                emoji=emoji,
            )

    async def callback(self, interaction: discord.Interaction):
        if self.view is None:
            raise AssertionError
        value = self.values[0]
        if value == "__index":
            await self.view.rebind(FrontPageSource(self.bot), interaction)
        else:
            cog = self.bot.get_cog(value)
            if cog is None:
                await interaction.response.send_message(
                    "Somehow this category does not exist?", ephemeral=True
                )
                return

            commands = self.commands[cog]
            if not commands:
                await interaction.response.send_message(
                    "This category has no commands for you", ephemeral=True
                )
                return

            source = GroupHelpPageSource(
                cog, commands, prefix=self.view.ctx.clean_prefix
            )
            await self.view.rebind(source, interaction)


class FrontPageSource(menus.PageSource):
    def __init__(self, bot: Parrot):
        self.bot = bot

    def is_paginating(self) -> bool:
        # This forces the buttons to appear even in the front page
        return True

    def get_max_pages(self) -> Optional[int]:
        # There's only one actual page in the front page
        # However we need at least 2 to show all the buttons
        return 2

    async def get_page(self, page_number: int) -> Any:
        # The front page is a dummy
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page):
        embed = discord.Embed(
            title="Bot Help",
            colour=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.description = inspect.cleandoc(
            f"""
            Hello! Welcome to the help page.
            Use "`{menu.ctx.clean_prefix}help command`" for more info on a command.
            Use "`{menu.ctx.clean_prefix}help category`" for more info on a category.
            Use the dropdown menu below to select a category.
        """
        )

        embed.add_field(
            name="Support Server",
            value=f"For more help, consider joining the official server over at {self.bot.support_server}",
            inline=False,
        )

        embed.add_field(
            name="Privacy Policy",
            value=f"For the privacy policy of the bot: visit [Privacy Policy]({PRIVACY_POLICY})",
            inline=False,
        )

        created_at = format_dt(menu.ctx.bot.user.created_at, "F")
        if self.index == 0:
            embed.add_field(
                name="Who are you?",
                value=(
                    r"The bot made by !! Ritik Ranjan [\*.*]#9230. Built with love and `discord.py`! Bot been running since "
                    f"{created_at}. Bot have features such as moderation, global-chat, and more. You can get more "
                    "information on my commands by using the dropdown below.\n\n"
                    f"Bot is also open source. You can see the code on [GitHub]({self.bot.github})!"
                ),
                inline=False,
            )
        elif self.index == 1:
            entries = (
                ("<argument>", "This means the argument is __**required**__."),
                ("[argument]", "This means the argument is __**optional**__."),
                ("[A|B]", "This means that it can be __**either A or B**__."),
                (
                    "[argument...]",
                    "This means you can have multiple arguments.\n"
                    "Now that you know the basics, it should be noted that...\n"
                    "__**You do not type in the brackets!**__",
                ),
            )

            embed.add_field(
                name="How do I use this bot?",
                value="Reading the bot signature is pretty simple.",
            )

            for name, value in entries:
                embed.add_field(name=name, value=value, inline=False)

        return embed


class HelpMenu(RoboPages):
    def __init__(self, source: menus.PageSource, ctx: Context):
        super().__init__(source, ctx=ctx, compact=True)

    def add_categories(self, commands: Dict[Cog, List[commands.Command]]) -> None:
        self.clear_items()
        self.add_item(HelpSelectMenu(commands, self.ctx.bot))
        self.fill_items()

    async def rebind(
        self, source: menus.PageSource, interaction: discord.Interaction
    ) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={
                "cooldown": commands.CooldownMapping.from_cooldown(
                    1, 3.0, commands.BucketType.member
                ),
                "help": "Shows help about the bot, a command, or a category",
            }
        )

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            # Ignore missing permission errors
            if (
                isinstance(error.original, discord.HTTPException)
                and error.original.code == 50013
            ):
                return

            await ctx.send(
                f"Well this is embarrassing. Please tell this to developer {error.original}"
            )

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = "|".join(command.aliases)
            fmt = f"[{command.name}|{aliases}]"
            if parent:
                fmt = f"{parent} {fmt}"
            alias = fmt
        else:
            alias = command.name if not parent else f"{parent} {command.name}"
        return f"{alias} {command.signature}"

    async def send_bot_help(self, mapping):
        await self.context.trigger_typing()
        bot = self.context.bot

        def key(command) -> str:
            cog = command.cog
            return cog.qualified_name if cog else "\U0010ffff"

        entries: List[commands.Command] = await self.filter_commands(
            bot.commands, sort=True, key=key
        )

        all_commands: Dict[Cog, List[commands.Command]] = {}
        for name, children in itertools.groupby(entries, key=key):
            if name == "\U0010ffff":
                continue

            cog = bot.get_cog(name)
            all_commands[cog] = sorted(children, key=lambda c: c.qualified_name)

        menu = HelpMenu(FrontPageSource(bot), ctx=self.context)
        menu.add_categories(all_commands)
        await menu.start()

    async def send_cog_help(self, cog):
        await self.context.trigger_typing()
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = HelpMenu(
            GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix),
            ctx=self.context,
        )

        await menu.start()

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f"{command.description}\n\n{command.help}"
        else:
            embed_like.description = command.help or "No help found..."

    async def send_command_help(self, command):
        await self.context.trigger_typing()
        # No pagination necessary for a single command.
        embed = discord.Embed(
            colour=discord.Color.blue(), timestamp=datetime.datetime.utcnow()
        )
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        try:
            await self.context.trigger_typing()
        except Exception:
            await self.context.reply(
                f"{self.context.author.mention} preparing help menu..."
            )
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        self.common_command_formatting(source, group)
        menu = HelpMenu(source, ctx=self.context)

        await menu.start()


class Meta(Cog):
    """Commands for utilities related to Discord or the Bot itself."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = PaginatedHelpCommand()
        bot.help_command.cog = self

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{WHITE QUESTION MARK ORNAMENT}")

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    @commands.command(name="ping")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def ping(self, ctx: Context):
        """
        Get the latency of bot.
        """
        start = time()
        message = await ctx.reply("Pinging...")
        db = await self.bot.db_latency
        end = time()
        await message.edit(
            content=f"Pong! latency: {self.bot.latency*1000:,.0f} ms. Response time: {(end-start)*1000:,.0f} ms. Database: {db*1000:,.0f} ms."
        )

    @commands.command(aliases=["av"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def avatar(self, ctx: Context, *, member: discord.Member = None):
        """
        Get the avatar of the user. Make sure you don't misuse.
        """
        member = member or ctx.author
        embed = discord.Embed(timestamp=datetime.datetime.utcnow())
        embed.add_field(
            name=member.name, value=f"[Download]({member.display_avatar.url})"
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="owner")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def owner(self, ctx: Context):
        """
        Get the freaking bot owner name.
        """
        await ctx.reply(
            embed=discord.Embed(
                title="Owner Info",
                description=r"This bot is being hosted and created by !! Ritik Ranjan [\*.\*]#9230. He is actually a dumb bot developer. He do not know why he made this shit bot. But it\'s cool",
                timestamp=datetime.datetime.utcnow(),
                color=ctx.author.color,
                url="https://discord.com/users/741614468546560092",
            )
        )

    @commands.command(aliases=["guildavatar", "serverlogo", "servericon"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def guildicon(self, ctx: Context, *, server: discord.Guild = None):
        """
        Get the freaking server icon
        """
        guild = server or ctx.guild
        embed = discord.Embed(timestamp=datetime.datetime.utcnow())
        embed.set_image(url=guild.icon.url)
        embed.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=embed)

    @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def server_info(self, ctx: Context):
        """
        Get the basic stats about the server
        """
        guild = ctx.guild
        embed = discord.Embed(
            title=f"Server Info: {ctx.guild.name}",
            colour=ctx.guild.owner.colour,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"ID: {ctx.guild.id}")
        statuses = [
            len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members))),
        ]

        fields = [
            ("Owner", ctx.guild.owner, True),
            ("Region", str(ctx.guild.region).capitalize(), True),
            ("Created at", f"<t:{int(ctx.guild.created_at.timestamp())}>", True),
            (
                "Total Members",
                f"Members: {len(ctx.guild.members)}\nHumans: {len(list(filter(lambda m: not m.bot, ctx.guild.members)))}\nBots: {len(list(filter(lambda m: m.bot, ctx.guild.members)))} ",
                True,
            ),
            (
                "Total channels",
                f"Categories: {len(ctx.guild.categories)}\nText: {len(ctx.guild.text_channels)}\nVoice:{len(ctx.guild.voice_channels)}",
                True,
            ),
            (
                "General",
                f"Roles: {len(ctx.guild.roles)}\nEmojis: {len(ctx.guild.emojis)}\nBoost Level: {ctx.guild.premium_tier}",
                True,
            ),
            (
                "Statuses",
                f":green_circle: {statuses[0]}\n:yellow_circle: {statuses[1]}\n:red_circle: {statuses[2]}\n:black_circle: {statuses[3]} [Blame Discord]",
                True,
            ),
        ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        info = []
        features = set(ctx.guild.features)
        all_features = {
            "PARTNERED": "Partnered",
            "VERIFIED": "Verified",
            "DISCOVERABLE": "Server Discovery",
            "COMMUNITY": "Community Server",
            "FEATURABLE": "Featured",
            "WELCOME_SCREEN_ENABLED": "Welcome Screen",
            "INVITE_SPLASH": "Invite Splash",
            "VIP_REGIONS": "VIP Voice Servers",
            "VANITY_URL": "Vanity Invite",
            "COMMERCE": "Commerce",
            "LURKABLE": "Lurkable",
            "NEWS": "News Channels",
            "ANIMATED_ICON": "Animated Icon",
            "BANNER": "Banner",
        }

        for feature, label in all_features.items():
            if feature in features:
                info.append(f":ballot_box_with_check: {label}")

        if info:
            embed.add_field(name="Features", value="\n".join(info))

        if guild.premium_tier != 0:
            boosts = (
                f"Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts"
            )
            last_boost = max(
                guild.members, key=lambda m: m.premium_since or guild.created_at
            )
            if last_boost.premium_since is not None:
                boosts = f"{boosts}\nLast Boost: {last_boost} ({format_relative(last_boost.premium_since)})"
            embed.add_field(name="Boosts", value=boosts, inline=True)
        else:
            embed.add_field(name="Boosts", value="Level 0", inline=True)

        emoji_stats = Counter()
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_stats["animated"] += 1
                emoji_stats["animated_disabled"] += not emoji.available
            else:
                emoji_stats["regular"] += 1
                emoji_stats["disabled"] += not emoji.available

        fmt = (
            f'Regular: {emoji_stats["regular"]}/{guild.emoji_limit}\n'
            f'Animated: {emoji_stats["animated"]}/{guild.emoji_limit}\n'
        )
        if emoji_stats["disabled"] or emoji_stats["animated_disabled"]:
            fmt = f'{fmt}Disabled: {emoji_stats["disabled"]} regular, {emoji_stats["animated_disabled"]} animated\n'

        fmt = f"{fmt}Total Emoji: {len(guild.emojis)}/{guild.emoji_limit*2}"
        embed.add_field(name="Emoji", value=fmt, inline=True)

        if ctx.guild.me.guild_permissions.ban_members:
            embed.add_field(
                name="Banned Members",
                value=f"{len(await ctx.guild.bans())}",
                inline=True,
            )
        if ctx.guild.me.guild_permissions.manage_guild:
            embed.add_field(
                name="Invites", value=f"{len(await ctx.guild.invites())}", inline=True
            )

        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner.url)

        await ctx.reply(embed=embed)

    @commands.command(name="stats")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def show_bot_stats(self, ctx: Context):
        """
        Get the bot stats
        """
        embed = discord.Embed(
            title="Bot stats",
            colour=ctx.author.colour,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_thumbnail(url=f"{ctx.guild.me.avatar.url}")
        proc = Process()
        with proc.oneshot():
            uptime = timedelta(seconds=time() - proc.create_time())
            cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
            mem_total = virtual_memory().total / (1024 ** 2)
            mem_of_total = proc.memory_percent()
            mem_usage = mem_total * (mem_of_total / 100)

        fields = [
            ("Bot version", f"`{VERSION}`", True),
            ("Python version", f"`{str(python_version())}`", True),
            ("discord.py version", f"`{str(discord_version)}`", True),
            ("Uptime", f"`{str(uptime)}`", True),
            ("CPU time", f"`{(cpu_time)}`", True),
            (
                "Memory usage",
                f"`{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)`",
                True,
            ),
            ("Total users on count", f"`{len(self.bot.users)}`", True),
            ("Owner", f"`{self.bot.author_name}`", True),
            ("Total guild on count", f"`{len(self.bot.guilds)}`", True),
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        await ctx.reply(embed=embed)

    @commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def user_info(self, ctx: Context, *, member: discord.Member = None):
        """
        Get the basic stats about the user
        """
        target = member or ctx.author
        roles = list(target.roles)
        embed = discord.Embed(
            title="User information",
            colour=target.colour,
            timestamp=datetime.datetime.utcnow(),
        )

        embed.set_thumbnail(url=target.avatar.url)
        embed.set_footer(text=f"ID: {target.id}")
        fields = [
            ("Name", str(target), True),
            ("Created at", f"<t:{int(target.created_at.timestamp())}>", True),
            ("Status", f"{str(target.status).title()} [Blame Discord]", True),
            (
                "Activity",
                f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''} [Blame Discord]",
                True,
            ),
            ("Joined at", f"<t:{int(target.joined_at.timestamp())}>", True),
            ("Boosted", bool(target.premium_since), True),
            ("Bot?", target.bot, True),
            ("Nickname", target.display_name, True),
            (f"Top Role [{len(roles)}]", target.top_role.mention, True),
        ]
        perms = []
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        if target.guild_permissions.administrator:
            perms.append("Administrator")
        if (
            target.guild_permissions.kick_members
            and target.guild_permissions.ban_members
            and target.guild_permissions.manage_messages
        ):
            perms.append("Server Moderator")
        if target.guild_permissions.manage_guild:
            perms.append("Server Manager")
        if target.guild_permissions.manage_roles:
            perms.append("Role Manager")
        if target.guild_permissions.moderate_members:
            perms.append("Can Timeout Members")
        embed.description = f"Key perms: {', '.join(perms if perms else ['NA'])}"
        if target.banner:
            embed.set_image(url=target.banner.url)
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def invite(self, ctx: Context):
        """
        Get the invite of the bot! Thanks for seeing this command
        """
        url = self.bot.invite
        em = discord.Embed(
            title="Click here to add",
            description=f"```ini\n[Default Prefix: `@{self.bot.user}`]\n```\n**Bot Owned and created by `{self.bot.author_name}`**",
            url=url,
            timestamp=datetime.datetime.utcnow(),
        )

        em.set_footer(text=f"{ctx.author}")
        em.set_thumbnail(url=ctx.guild.me.avatar.url)
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def roleinfo(self, ctx: Context, *, role: discord.Role):
        """To get the info regarding the server role"""
        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            description=f"ID: `{role.id}`",
            color=role.color,
            timestamp=datetime.datetime.utcnow(),
        )
        data = [
            ("Created At", f"<t:{int(role.created_at.timestamp())}>", True),
            ("Is Hoisted?", role.hoist, True),
            ("Position", role.position, True),
            ("Managed", role.managed, True),
            ("Mentionalble?", role.mentionable, True),
            ("Members", len(role.members), True),
            ("Mention", role.mention, True),
            ("Is Boost role?", role.is_premium_subscriber(), True),
            ("Is Bot role?", role.is_bot_managed(), True),
        ]
        for name, value, inline in data:
            embed.add_field(name=name, value=value, inline=inline)
        perms = []
        if role.permissions.administrator:
            perms.append("Administrator")
        if (
            role.permissions.kick_members
            and role.permissions.ban_members
            and role.permissions.manage_messages
        ):
            perms.append("Server Moderator")
        if role.permissions.manage_guild:
            perms.append("Server Manager")
        if role.permissions.manage_roles:
            perms.append("Role Manager")
        if role.permissions.moderate_members:
            perms.append("Can Timeout Members")
        embed.description = f"Key perms: {', '.join(perms if perms else ['NA'])}"
        embed.set_footer(text=f"ID: {role.id}")
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def emojiinfo(self, ctx: Context, *, emoji: discord.Emoji):
        """To get the info regarding the server emoji"""
        em = discord.Embed(
            title="Emoji Info",
            description=f"• [Download the emoji]({emoji.url})\n• Emoji ID: `{emoji.id}`",
            timestamp=datetime.datetime.utcnow(),
            color=ctx.author.color,
        )
        data = [
            ("Name", emoji.name, True),
            ("Is Animated?", emoji.animated, True),
            ("Created At", f"<t:{int(emoji.created_at.timestamp())}>", True),
            ("Server Owned", emoji.guild.name, True),
            ("Server ID", emoji.guild_id, True),
            ("Created By", emoji.user if emoji.user else "User Not Found", True),
            ("Available?", emoji.available, True),
            ("Managed by Twitch?", emoji.managed, True),
            ("Require Colons?", emoji.require_colons, True),
        ]
        em.set_footer(text=f"{ctx.author}")
        em.set_thumbnail(url=emoji.url)
        for name, value, inline in data:
            em.add_field(name=name, value=f"{value}", inline=inline)
        await ctx.reply(embed=em)

    @commands.command(name="channelinfo")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def channel_info(
        self,
        ctx: Context,
        *,
        channel: typing.Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.CategoryChannel,
            discord.StageChannel,
        ] = None,
    ):
        channel = channel or ctx.channel
        id_ = channel.id
        created_at = f"<t:{int(channel.created_at.timestamp())}>"
        mention = channel.mention
        position = channel.position
        type_ = str(channel.type).capitalize()
        embed = discord.Embed(
            title="Channel Info",
            color=ctx.author.color,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Name", value=channel.name)
        embed.add_field(name="ID", value=f"{id_}")
        embed.add_field(name="Created At", value=created_at)
        embed.add_field(name="Mention", value=mention)
        embed.add_field(name="Position", value=position)
        embed.add_field(name="Type", value=type_)
        embed.set_footer(text=f"{ctx.author}")
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["suggest"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def request(self, ctx: Context, *, text: str):
        """To request directly from the owner"""
        view = Prompt(ctx.author.id)
        msg = await ctx.reply(
            f"{ctx.author.mention} are you sure want to request for the same. Abuse of this feature may result in ban from using Parrot bot. Press `YES` to continue",
            view=view,
        )
        await view.wait()
        if view.value is None:
            await msg.reply(
                f"{ctx.author.mention} you did not responds on time. No request is being sent!"
            )
        elif view.value:
            if self.bot.author_obj:
                await self.bot.author_obj.send(text[:1800:])
            else:
                from utilities.config import SUPER_USER

                await self.bot.get_user(SUPER_USER).send(text[:1800:])
            await msg.reply(f"{ctx.author.mention} your message is being delivered!")
        else:
            await msg.reply(f"{ctx.author.mention} nvm, reverting the process")

    @commands.command(hidden=True)
    async def hello(self, ctx: Context):
        """Displays my intro message."""
        await ctx.reply(
            f"Hello! {self.bot.user} is a robot. `{self.bot.author_name}` made me."
        )

    @commands.command(rest_is_raw=True, hidden=True)
    @commands.is_owner()
    async def echo(self, ctx: Context, *, content):
        await ctx.send(content)

    @commands.command(hidden=True)
    async def cud(self, ctx: Context):
        """pls no spam"""
        for i in range(3):
            await ctx.send(3 - i)
            await asyncio.sleep(1)

        await ctx.send("go")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def announcement(self, ctx: Context):
        """To get the latest news from the support server | Change Log"""
        embed = discord.Embed(
            title="Announcement",
            timestamp=datetime.datetime.utcnow(),
            color=ctx.author.color,
        )
        embed.set_footer(text=f"{ctx.author}")
        change_log = await self.bot.change_log
        embed.description = f"Message at: <t:{int(change_log.created_at.timestamp())}>\n\n{change_log.content}"
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def vote(self, ctx: Context):
        """Vote the bot for better discovery on top.gg"""
        embed = discord.Embed(
            title="Click here to vote!",
            url=f"https://top.gg/bot/{self.bot.user.id}/vote",
            description=f"**{ctx.author}** thank you for using this command!\n\nYou can vote in every 12h",
            timestamp=datetime.datetime.utcnow(),
            color=ctx.author.color,
        )
        embed.set_footer(text=f"{ctx.author}")
        embed.set_thumbnail(url=ctx.guild.me.avatar.url)
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def inviteinfo(self, ctx: Context, code: str):
        """Get the info regarding the Invite Link"""
        invite = await self.bot.fetch_invite(f"https://discord.gg/{code}")
        if (not invite.guild) or (not invite):
            return await ctx.send(
                f"{ctx.author.mention} invalid invite or invite link is not of server"
            )
        embed = discord.Embed(
            title=invite.url, timestamp=datetime.datetime.utcnow(), url=invite.url
        )
        embed.description = f"""`Member Count?  :` **{invite.approximate_member_count}**
`Presence Count?:` **{invite.approximate_presence_count}**
`Channel     :` **<#{invite.channel.id}>**
`Created At  :` **{'Can not determinded' if invite.created_at is None else discord.utils.format_dt(invite.created_at)}**
`Expires At  :` **{'Invite' if invite.expires_at is None else discord.utils.format_dt(invite.expires_at)}**
`Temporary?  :` **{bool(invite.temporary)}**
`Max Uses    :` **{invite.max_uses if invite.max_uses else 'Infinte'}**
`Link        :` **{invite.url}**
`Inviter?    :` **{invite.inviter}**
"""
        await ctx.send(embed=embed)
