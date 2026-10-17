from __future__ import annotations

import asyncio
import io
import itertools
import logging
import os
import platform
import time
import urllib.parse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import discord
import psutil
import pygit2
from discord.ext import commands
from dotenv import load_dotenv

from core.utils import DeleteMessageButtonView

from .announcement import Announcements

if TYPE_CHECKING:
    from core import Bot

load_dotenv()

_log = logging.getLogger(__name__)

OWNER_ID = int(os.environ["OWNER_ID"])
OWNER_UPI_ID = os.getenv("UPI_ID")
REPO_SLUG = os.getenv("GITHUB_REPO", "rtk-rnjn/Parrot").removeprefix("https://github.com/").strip("/")
REPO_URL = f"https://github.com/{REPO_SLUG}"

COMMIT_COUNT = 3
COMMIT_SUMMARY_LIMIT = 50
SUGGESTION_MIN = 50
SUGGESTION_MAX = 1500
EMOJI_URI = "https://raw.githubusercontent.com/iamcal/emoji-data/master/img-twitter-72/{emoji}.png"
QR_URL = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={data}&ecc=H&margin=19"


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "\N{HORIZONTAL ELLIPSIS}"


def _recent_commits() -> tuple[str | None, str | None]:
    """Return (branch, formatted commit lines). Blocking, so call it through ``asyncio.to_thread``."""
    if not Path(".git").is_dir():
        return None, None
    try:
        repo = pygit2.Repository(".git")
        lines = []
        for commit in itertools.islice(repo.walk(repo.head.target), COMMIT_COUNT):
            when = datetime.fromtimestamp(commit.commit_time, tz=UTC)
            summary = _short(commit.message.partition("\n")[0], COMMIT_SUMMARY_LIMIT)
            lines.append(f"[`{str(commit.id)[:7]}`]({REPO_URL}/commit/{commit.id}) {summary} ({discord.utils.format_dt(when, 'R')})")
        return repo.head.shorthand, "\n".join(lines) or None
    except pygit2.GitError, KeyError:
        return None, None


def donate_embed(bot_name: str) -> discord.Embed | None:
    """An embed with the UPI ID in a copyable block plus a scannable QR code."""
    if not OWNER_UPI_ID:
        return None
    link = "upi://pay?" + urllib.parse.urlencode({"pa": OWNER_UPI_ID, "pn": bot_name, "cu": "INR"})
    embed = discord.Embed(
        title="\N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16} Support the bot",
        description=(
            "Hosting costs money and updates cost time. If you enjoy the bot, a small tip helps a lot, "
            "but it is **never** required.\n\n"
            f"**UPI ID**\n```{OWNER_UPI_ID}```\n"
            "Scan the QR code with any UPI app, or copy the ID above."
        ),
        colour=discord.Colour.pink(),
    )
    embed.set_image(url=QR_URL.format(data=urllib.parse.quote(link, safe="")))
    embed.set_footer(text="Built with \N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16} and wine \N{WINE GLASS}")
    return embed


class AboutView(discord.ui.View):
    def __init__(self, bot: Bot, *, author_id: int) -> None:
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.message: discord.Message | None = None

        self.add_item(discord.ui.Button(label="Source", emoji="\N{PERSONAL COMPUTER}", url=REPO_URL))
        if not OWNER_UPI_ID:
            self.donate.disabled = True
            self.remove_item(self.donate)

    @discord.ui.button(label="Donate", emoji="\N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.success)
    async def donate(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        embed = donate_embed(self.bot.user.name if self.bot.user else "Bot")
        if embed is None:
            await interaction.response.send_message("Donations are not set up.", ephemeral=True)
            return

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.url is None:
                item.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)


class Meta(commands.Cog):
    """Meta commands for the bot."""

    help_emoji = "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.process = psutil.Process()

        self.process.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None)
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    def _permission_names(self, permissions: discord.Permissions, *, role: bool = False) -> str:
        names: list[str] = []
        if permissions.administrator:
            names.append("Administrator")
        if permissions.kick_members and permissions.ban_members and permissions.manage_messages:
            names.append("Server Moderator")
        if permissions.manage_guild:
            names.append("Server Manager")
        if permissions.manage_roles:
            names.append("Role Manager")
        if permissions.moderate_members:
            names.append("Can Timeout Members")
        if permissions.manage_channels:
            names.append("Channel Manager")
        if role and permissions.manage_emojis:
            names.append("Emoji Manager")
        if not role and permissions.manage_messages:
            names.append("Message Manager")
        if not role and permissions.mention_everyone:
            names.append("Mention Everyone")
        return ", ".join(names) if names else "None"

    def _counts(self) -> dict[str, int]:
        channels: Counter[str] = Counter()
        members = 0
        for guild in self.bot.guilds:
            members += guild.member_count or 0
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    channels["text"] += 1
                elif isinstance(channel, discord.VoiceChannel):
                    channels["voice"] += 1
                elif isinstance(channel, discord.StageChannel):
                    channels["stage"] += 1
                elif isinstance(channel, discord.ForumChannel):
                    channels["forum"] += 1
                elif isinstance(channel, discord.CategoryChannel):
                    channels["category"] += 1
        return {"members": members, **channels}

    @commands.command(name="about", aliases=["info", "botinfo", "hello", "hi"])
    async def about_bot(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display information about the bot."""
        owner = await self.bot.get_or_fetch(self.bot.get_user, self.bot.fetch_user, OWNER_ID)

        bot = self.bot
        counts = self._counts()
        branch, commits = await asyncio.to_thread(_recent_commits)

        with self.process.oneshot():
            memory = self.process.memory_info().rss / 1024**2
            process_cpu = self.process.cpu_percent(interval=None)
            threads = self.process.num_threads()
            created = datetime.fromtimestamp(self.process.create_time(), tz=UTC)
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=None)

        started = getattr(bot, "_started_at", None) or created
        total_channels = sum(counts.get(kind, 0) for kind in ("text", "voice", "stage", "forum"))

        embed = (
            discord.Embed(
                title=f"About {bot.user}",
                colour=discord.Colour.blurple(),
            )
            .add_field(
                name="Stats",
                value=(
                    f"**Servers:** {len(bot.guilds):,}\n"
                    f"**Members:** {counts['members']:,}\n"
                    f"**Cached users:** {len(bot.users):,}\n"
                    f"**Commands:** {sum(1 for _ in bot.walk_commands()):,}"
                ),
            )
            .add_field(
                name="Channels",
                value=(
                    f"**Total:** {total_channels:,}\n"
                    f"**Text:** {counts.get('text', 0):,}\n"
                    f"**Voice:** {counts.get('voice', 0) + counts.get('stage', 0):,}\n"
                    f"**Categories:** {counts.get('category', 0):,}"
                ),
            )
            .add_field(
                name="Process",
                value=(
                    f"**Memory:** {memory:.1f} MiB\n**CPU:** {process_cpu:.1f}%\n**Threads:** {threads}\n**Latency:** {bot.latency * 1000:.0f} ms"
                ),
            )
            .add_field(
                name="System",
                value=(
                    f"**CPU:** {system_cpu:.1f}% ({psutil.cpu_count()} cores)\n"
                    f"**RAM:** {system_memory.percent:.1f}% of {system_memory.total / 1024**3:.1f} GiB\n"
                    f"**OS:** {platform.system()} {platform.release()}"
                ),
            )
            .add_field(
                name="Versions",
                value=f"**Python:** {platform.python_version()}\n**discord.py:** {discord.__version__}\nBot: {bot.VERSION}",
            )
            .add_field(name="Uptime", value=f"Online since {discord.utils.format_dt(started, 'R')}")
        )

        if commits:
            embed.description = f"Recent commits on branch `{branch}`:\n{commits}"

        footer = f"-# Made by {owner.mention} (@{owner} - {owner.id})" if owner is not None else f"Made by <@{OWNER_ID}> ({OWNER_ID})"
        feedback_command = self.feedback.name
        embed.add_field(
            name="\N{ZERO WIDTH SPACE}", value=f"{footer}\n-# Have an idea? Use `{ctx.clean_prefix}{feedback_command} <idea>`.", inline=False
        )
        if bot.user is not None:
            embed.set_thumbnail(url=bot.user.display_avatar.url)

        disclaimer = (
            "This bot is open source and free to use. It is not affiliated with Discord, Inc. in any way.\n"
            "The bot owner reserves the right to remove the bot from the server without notice if the bot is being misused or causing issues."
        )
        embed.set_footer(text=disclaimer)

        view = AboutView(bot, author_id=ctx.author.id)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message
        return message

    @commands.command(name="feedback")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def feedback(
        self,
        ctx: commands.Context[Bot],
        *,
        suggestion: Annotated[str, commands.Range[str, SUGGESTION_MIN, SUGGESTION_MAX]] = commands.parameter(
            description="Your suggestion or feedback."
        ),
    ) -> None:
        """Send a suggestion or feedback straight to the bot owner."""
        embed = (
            discord.Embed(
                title="New suggestion",
                description=suggestion,
                colour=discord.Colour.green(),
                timestamp=discord.utils.utcnow(),
                url=ctx.message.jump_url,
            )
            .set_author(name=f"{ctx.author} ({ctx.author.id})", icon_url=ctx.author.display_avatar.url)
            .set_footer(text=f"From server: {ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "From a DM")
        )

        if ctx.message.attachments:
            first = ctx.message.attachments[0]
            if first.content_type and first.content_type.startswith("image/"):
                embed.set_image(url=first.url)
            embed.add_field(name="Attachments", value="\n".join(a.url for a in ctx.message.attachments)[:1024], inline=False)

        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            await owner.send(embed=embed)
        except discord.HTTPException:
            _log.exception("Could not deliver suggestion from %s", ctx.author.id)
            ctx.command.reset_cooldown(ctx) if ctx.command else None
            await ctx.reply("Bot could not deliver your suggestion right now. Please try again later.")
            return

        await ctx.reply("\N{WHITE HEAVY CHECK MARK} Thanks! Your suggestion was sent to the bot owner.")

    @commands.command(name="donate", aliases=["support", "tip"])
    async def donate_command(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show how to support the bot with a UPI donation."""
        embed = donate_embed(self.bot.user.name if self.bot.user else "Bot")
        if embed is None:
            return await ctx.reply("Donations are not set up right now.")
        return await ctx.reply(embed=embed)

    @commands.command(name="ping", aliases=["latency"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def ping(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display the bot's current latency.

        The following latency values are reported:

        - Gateway latency:
            The bot's current WebSocket latency to Discord.

        - API latency:
            The time taken for Discord to respond to the initial ping message.

        - Database latency:
            The time taken to ping the configured database services. MongoDB
            and Redis latencies are reported individually, along with their
            combined latency.
        """
        start_time = time.perf_counter()

        message = await ctx.reply("Pinging...")

        mongo_start_time = time.perf_counter()
        await self.bot.database.ping_mongo_server()
        mongo_latency = (time.perf_counter() - mongo_start_time) * 1000

        redis_start_time = time.perf_counter()
        await self.bot.database.ping_redis_server()
        redis_latency = (time.perf_counter() - redis_start_time) * 1000

        api_latency = (time.perf_counter() - start_time) * 1000
        database_latency = mongo_latency + redis_latency
        gateway_latency = self.bot.latency * 1000

        ping_pong_emoji = "\N{TABLE TENNIS PADDLE AND BALL}"

        content = (
            f"{ping_pong_emoji} **Pong!** Gateway: `{gateway_latency:.2f}ms` | API: `{api_latency:.2f}ms` | Database: `{database_latency:.2f}ms`"
        )
        return await message.edit(content=content)

    @commands.command(name="uptime", aliases=["up"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def uptime(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display how long the bot has been online.

        The uptime is calculated based on the time the bot finished starting
        up and is displayed in a human-readable format. The response also
        includes the exact timestamp of when the bot started, formatted in a
        way that Discord will render as a relative time (e.g., "2 hours ago").
        """

        started_at = self.bot.started_at

        if started_at is None:
            return await ctx.reply("The bot has not finished starting up yet.")

        uptime = discord.utils.format_dt(started_at, style="R")

        started = discord.utils.format_dt(started_at, style="F")

        UPTIME_EMOJI = "\N{ALARM CLOCK}"
        STARTED_EMOJI = "\N{ROCKET}"

        return await ctx.reply(f"{UPTIME_EMOJI} **Uptime:** {uptime}\n{STARTED_EMOJI} **Started:** {started}")

    @commands.command(name="member_count", aliases=["member-count", "mc"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def member_count(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display the member count of the current server.

        The response shows the total number of members, followed by separate
        counts for human users and bot accounts. No embed is used, so the
        information is returned directly as a simple text message.
        """

        assert ctx.guild is not None, "This command can only be used in a server."

        humans = sum(not member.bot for member in ctx.guild.members)
        bots = sum(member.bot for member in ctx.guild.members)

        MEMBER_EMOJI = "\N{BUSTS IN SILHOUETTE}"
        HUMAN_EMOJI = "\N{BUST IN SILHOUETTE}"
        BOT_EMOJI = "\N{ROBOT FACE}"

        return await ctx.reply(
            f"{MEMBER_EMOJI} **Members:** `{ctx.guild.member_count:,}`\n{HUMAN_EMOJI} **Humans:** `{humans:,}`\n{BOT_EMOJI} **Bots:** `{bots:,}`"
        )

    @commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.member)
    async def user_info(
        self,
        ctx: commands.Context[Bot],
        *,
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to display information about.",
            default=lambda ctx: ctx.author,
        ),
    ) -> discord.Message:
        """Display detailed information about a server member.

        If no member is specified, information about the command author is
        displayed.

        The embed uses the member's current display colour and avatar, with the
        member ID shown in the footer.
        """

        if TYPE_CHECKING:
            assert isinstance(ctx.author, discord.Member), "This command can only be used in a server."
            assert ctx.guild is not None, "This command can only be used in a server."

        target: discord.Member = member or ctx.author

        roles = target.roles
        permissions = self._permission_names(target.guild_permissions)

        embed = (
            discord.Embed(
                title=f"User Information {'[Bot]' if target.bot else ''}".strip(),
                colour=target.colour,
                timestamp=discord.utils.utcnow(),
                description=f"**Permissions:** {permissions}",
            )
            .set_thumbnail(url=target.display_avatar.url)
            .add_field(name="Name", value=target, inline=True)
            .add_field(name="Display Name", value=target.display_name, inline=True)
            .add_field(name="Nickname", value=target.nick or "N/A", inline=True)
            .add_field(
                name="Created At",
                value=(discord.utils.format_dt(target.created_at, style="R")),
                inline=True,
            )
            .add_field(
                name="Joined At",
                value=(discord.utils.format_dt(target.joined_at, style="R") if target.joined_at else "N/A"),
                inline=True,
            )
            .add_field(name="Roles", value=len(roles) - 1 if len(roles) > 1 else 0, inline=True)
            .set_footer(text=f"ID: {target.id}")
        )

        if target.banner:
            embed.set_image(url=target.banner.url)

        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="avatar", aliases=["pfp", "av"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.member)
    async def avatar(
        self,
        ctx: commands.Context[Bot],
        *,
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to display the avatar of.",
            default=lambda ctx: ctx.author,
        ),
    ) -> discord.Message:
        """Display a server member's avatar.

        If no member is specified, the command displays the avatar of the
        command author.

        The avatar is displayed in an embed with the member's current display
        colour. The member ID is included in the embed footer.
        """
        target: discord.Member = member or ctx.author

        avatar_bytes = await target.display_avatar.read()
        file = discord.File(io.BytesIO(avatar_bytes), filename="avatar.gif")

        embed = (
            discord.Embed(
                title=f"{target}'s Avatar",
                colour=target.colour,
                timestamp=discord.utils.utcnow(),
            )
            .set_image(url="attachment://avatar.gif")
            .set_footer(text=f"ID: {target.id}")
        )

        content = f"Requested by: {ctx.author.mention}" if target != ctx.author else None

        delete_view = DeleteMessageButtonView(author=ctx.author)
        message = await ctx.reply(content, embed=embed, view=delete_view, file=file, mention_author=False)
        delete_view.message = message

        return message

    def _server_summary_fields(self, guild: discord.Guild) -> list[tuple[str, object]]:
        statuses = [len(list(filter(lambda member: str(member.status) == status, guild.members))) for status in ("online", "idle", "dnd", "offline")]
        total_humans = len([member for member in guild.members if not member.bot])
        total_bots = len(guild.members) - total_humans
        return [
            ("Owner", guild.owner),
            ("Region", "Deprecated"),
            ("Created at", f"{discord.utils.format_dt(guild.created_at)}"),
            ("Total Members", f"Members: {len(guild.members)}\nHumans: {total_humans}\nBots: {total_bots}"),
            ("Total channels", f"Categories: {len(guild.categories)}\nText: {len(guild.text_channels)}\nVoice:{len(guild.voice_channels)}"),
            ("General", f"Roles: {len(guild.roles)}\nEmojis: {len(guild.emojis)}\nBoost Level: {guild.premium_tier}"),
            (
                "Statuses",
                f":green_circle: {statuses[0]}\n:yellow_circle: {statuses[1]}\n:red_circle: {statuses[2]}\n:black_circle: {statuses[3]}",
            ),
        ]

    async def _add_server_details(self, embed: discord.Embed, guild: discord.Guild) -> None:
        features = {
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
        info = [f":ballot_box_with_check: {label}" for feature, label in features.items() if feature in guild.features]
        if info:
            embed.add_field(name="Features", value="\n".join(info))

        boosts = f"Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts"
        if guild.premium_tier != 0:
            last_boost = max(
                guild.members,
                key=lambda member: member.premium_since or guild.created_at,
            )
            if last_boost.premium_since is not None:
                boosts = f"{boosts}\nLast Boost: {last_boost} ({discord.utils.format_dt(last_boost.premium_since, 'R')})"
        else:
            boosts = "Level 0"
        embed.add_field(name="Boosts", value=boosts, inline=True)

        emoji_stats = Counter()
        for emoji in guild.emojis:
            category = "animated" if emoji.animated else "regular"
            emoji_stats[category] += 1
            if not emoji.available:
                emoji_stats[f"{category}_disabled"] += 1
        emoji_text = f"Regular: {emoji_stats['regular']}/{guild.emoji_limit}\nAnimated: {emoji_stats['animated']}/{guild.emoji_limit}\n"
        if emoji_stats["disabled"] or emoji_stats["animated_disabled"]:
            emoji_text += f"Disabled: {emoji_stats['disabled']} regular, {emoji_stats['animated_disabled']} animated\n"
        emoji_text += f"Total Emoji: {len(guild.emojis)}/{guild.emoji_limit * 2}"
        embed.add_field(name="Emoji", value=emoji_text, inline=True)

        if guild.me.guild_permissions.ban_members:
            embed.add_field(
                name="Banned Members",
                value=f"{len([_ async for _ in guild.bans(limit=1000)])}+",
                inline=True,
            )

        if guild.me.guild_permissions.manage_guild:
            embed.add_field(name="Invites", value=f"{len(await guild.invites())}", inline=True)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

    @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.member)
    async def server_info(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display detailed information about the current server.

        The response includes the server owner, creation date, member counts,
        channel counts, roles, emojis, boost level, member statuses, server
        features, boost information, emoji availability, and other available
        server statistics.

        Additional information such as the number of bans and active invites is
        included when the bot has the required server permissions.

        The server icon is shown as the embed thumbnail and the server banner is
        shown as the embed image when available. The server ID is included in the
        embed footer.
        """
        if TYPE_CHECKING:
            assert isinstance(ctx.author, discord.Member), "This command can only be used in a server."
            assert ctx.guild is not None, "This command can only be used in a server."

        embed: discord.Embed = discord.Embed(
            title=f"Server Info: {ctx.guild.name}",
            colour=(ctx.guild.owner.colour if ctx.guild.owner else discord.Colour.blurple()),
            timestamp=discord.utils.utcnow(),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"ID: {ctx.guild.id}")
        for name, value in self._server_summary_fields(ctx.guild):
            embed.add_field(name=name, value=value)
        await self._add_server_details(embed, ctx.guild)

        return await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.member)
    async def roleinfo(
        self,
        ctx: commands.Context[Bot],
        *,
        role: discord.Role = commands.parameter(description="The role to display information about."),  # noqa: B008
    ) -> discord.Message:
        """Display detailed information about a server role.

        The response includes the role's creation date, position, hoist status,
        managed status, mentionability, member count, mention string, whether it
        is a premium subscriber role or bot-managed role, and its key permissions.

        The role's icon is displayed when available, with its Unicode emoji used
        as a fallback. The role ID is also included in the embed.
        """
        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            description=f"ID: `{role.id}`",
            color=role.color,
            timestamp=discord.utils.utcnow(),
        )
        data = [
            ("Created At", f"{discord.utils.format_dt(role.created_at)}", True),
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
        permissions = self._permission_names(role.permissions, role=True)
        embed.description = f"Key perms: {permissions if permissions != 'None' else 'N/A'}"
        embed.set_footer(text=f"ID: {role.id}")
        if role.unicode_emoji:
            embed.set_thumbnail(url=EMOJI_URI.format(emoji=f"{ord(next(iter(role.unicode_emoji))):x}"))
        if role.icon:
            embed.set_thumbnail(url=role.icon.url)
        return await ctx.reply(embed=embed)

    @commands.command(name="channelinfo")
    async def channel_info(
        self,
        ctx: commands.Context[Bot],
        *,
        channel: discord.abc.GuildChannel = commands.parameter(  # noqa: B008
            description="The channel to display information about.",
            default=lambda ctx: ctx.channel,
        ),
    ) -> discord.Message:
        """Display information about a server channel.

        If no channel is specified, the command displays information about the
        channel in which it was invoked. The response includes the channel name,
        ID, creation date, mention, position, and channel type.

        The channel information is presented in an embed with the server icon
        shown as the thumbnail when available.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None, "This command can only be used in a server."

        channel = channel or ctx.channel
        channel_id = channel.id

        assert isinstance(
            channel,
            discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel | discord.StageChannel,
        )

        created_at = f"{discord.utils.format_dt(channel.created_at)}"
        mention = channel.mention
        position = channel.position
        channel_type = str(channel.type).capitalize()
        embed = (
            discord.Embed(
                title="Channel Info",
                color=ctx.author.color,
                timestamp=discord.utils.utcnow(),
            )
            .add_field(name="Name", value=channel.name)
            .add_field(name="ID", value=f"{channel_id}")
            .add_field(name="Created At", value=created_at)
            .add_field(name="Mention", value=mention)
            .add_field(name="Position", value=position)
            .add_field(name="Type", value=channel_type)
            .set_footer(text=f"{ctx.author}")
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        return await ctx.reply(embed=embed)

    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Display an invite link for the bot.

        The invite link allows users to add the bot to their own servers with
        the necessary permissions. The response includes a clickable link that
        opens the Discord authorization page for the bot.
        """
        invite_url = discord.utils.oauth_url(self.bot.user.id, scopes=("bot", "applications.commands"))
        return await ctx.reply(f"Invite Bot to your server: [Click Here](<{invite_url}>)")


async def setup(bot: Bot) -> None:
    """Load the Meta cog."""
    await bot.add_cog(Meta(bot))
    await bot.add_cog(Announcements(bot))
