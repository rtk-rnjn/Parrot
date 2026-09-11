from __future__ import annotations

import io
import logging
import time
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core import DeleteMessageButtonView

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.meta")


class Meta(commands.Cog):
    """Meta commands for the bot."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    def _permission_names(self, permissions: discord.Permissions, *, role: bool = False) -> str:
        names = []
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

    @commands.command(
        name="ping",
        aliases=("latency",),
    )
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.user,
    )
    async def ping(
        self,
        ctx: commands.Context[Parrot],
    ) -> discord.Message:
        """
        Display the bot's current latency.

        The following latency values are reported:

        - Gateway latency:
            The bot's current WebSocket latency to Discord.

        - API latency:
            The time taken for Discord to respond to the initial ping message.

        - Database latency:
            The time taken to ping the configured database services. MongoDB
            and Redis latencies are reported individually, along with their
            combined latency.

        This command has a 5-second cooldown per user.
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

        content = f"{ping_pong_emoji} **Pong!** Gateway: `{gateway_latency:.2f}ms` | API: `{api_latency:.2f}ms` | Database: `{database_latency:.2f}ms` (MongoDB: `{mongo_latency:.2f}ms`, Redis: `{redis_latency:.2f}ms`)"

        return await message.edit(content=content)

    @commands.command(
        name="uptime",
        aliases=("up",),
    )
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.user,
    )
    async def uptime(
        self,
        ctx: commands.Context[Parrot],
    ) -> discord.Message:
        """Display how long the bot has been online.

        The uptime is calculated based on the time the bot finished starting
        up and is displayed in a human-readable format. The response also
        includes the exact timestamp of when the bot started, formatted in a
        way that Discord will render as a relative time (e.g., "2 hours ago").

        This command has a 5-second cooldown per user.
        """

        started_at = self.bot.started_at

        if started_at is None:
            return await ctx.reply("The bot has not finished starting up yet.")

        uptime = discord.utils.format_dt(
            started_at,
            style="R",
        )

        started = discord.utils.format_dt(
            started_at,
            style="F",
        )

        UPTIME_EMOJI = "\N{ALARM CLOCK}"
        STARTED_EMOJI = "\N{ROCKET}"

        return await ctx.reply(f"{UPTIME_EMOJI} **Uptime:** {uptime}\n{STARTED_EMOJI} **Started:** {started}")

    @commands.command(
        name="member_count",
        aliases=("member-count", "mc"),
    )
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.user,
    )
    async def member_count(
        self,
        ctx: commands.Context[Parrot],
    ) -> discord.Message:
        """
        Display the member count of the current server.

        The response shows the total number of members, followed by separate
        counts for human users and bot accounts. No embed is used, so the
        information is returned directly as a simple text message.

        This command has a 5-second cooldown per user.
        """

        assert ctx.guild is not None, "This command can only be used in a server."

        humans = sum(not member.bot for member in ctx.guild.members)
        bots = sum(member.bot for member in ctx.guild.members)

        MEMBER_EMOJI = "\N{BUSTS IN SILHOUETTE}"
        HUMAN_EMOJI = "\N{BUST IN SILHOUETTE}"
        BOT_EMOJI = "\N{ROBOT FACE}"

        return await ctx.reply(
            f"{MEMBER_EMOJI} **Members:** `{ctx.guild.member_count:,}`\n{HUMAN_EMOJI} **Humans:** `{humans:,}`\n{BOT_EMOJI} **Bots:** `{bots:,}`",
        )

    @commands.command(
        name="userinfo",
        aliases=("memberinfo", "ui", "mi"),
    )
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def user_info(
        self,
        ctx: commands.Context[Parrot],
        *,
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to display information about.",
            default=lambda ctx: ctx.author,
        ),
    ) -> discord.Message:
        """
        Display detailed information about a server member.

        If no member is specified, information about the command author is
        displayed.

        The embed uses the member's current display colour and avatar, with the
        member ID shown in the footer.

        This command has a 5-second cooldown per member.
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
            .add_field(
                name="Name",
                value=target,
                inline=True,
            )
            .add_field(
                name="Display Name",
                value=target.display_name,
                inline=True,
            )
            .add_field(
                name="Nickname",
                value=target.nick or "N/A",
                inline=True,
            )
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
            .add_field(
                name="Roles",
                value=len(roles) - 1 if len(roles) > 1 else 0,
                inline=True,
            )
            .set_footer(text=f"ID: {target.id}")
        )

        if target.banner:
            embed.set_image(url=target.banner.url)

        return await ctx.reply(
            embed=embed,
            mention_author=False,
        )

    @commands.command(name="avatar", aliases=["pfp", "av"])
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def avatar(
        self,
        ctx: commands.Context[Parrot],
        *,
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to display the avatar of.",
            default=lambda ctx: ctx.author,
        ),
    ) -> discord.Message:
        """
        Display a server member's avatar.

        If no member is specified, the command displays the avatar of the
        command author.

        The avatar is displayed in an embed with the member's current display
        colour. The member ID is included in the embed footer.

        This command has a 5-second cooldown per member.
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

        if target != ctx.author:
            content = f"Requested by: {ctx.author.mention}"
        else:
            content = None

        delete_view = DeleteMessageButtonView(author=ctx.author)
        message = await ctx.reply(content, embed=embed, view=delete_view, file=file, mention_author=False)
        delete_view.message = message

        return message

    def _server_summary_fields(self, guild: discord.Guild) -> list[tuple[str, object, bool]]:
        statuses = [len(list(filter(lambda member: str(member.status) == status, guild.members))) for status in ("online", "idle", "dnd", "offline")]
        return [
            ("Owner", guild.owner, True),
            ("Region", "Deprecated", True),
            ("Created at", f"{discord.utils.format_dt(guild.created_at)}", True),
            (
                "Total Members",
                f"Members: {len(guild.members)}\nHumans: {len([member for member in guild.members if not member.bot])}\nBots: {len([member for member in guild.members if member.bot])}",
                True,
            ),
            ("Total channels", f"Categories: {len(guild.categories)}\nText: {len(guild.text_channels)}\nVoice:{len(guild.voice_channels)}", True),
            ("General", f"Roles: {len(guild.roles)}\nEmojis: {len(guild.emojis)}\nBoost Level: {guild.premium_tier}", True),
            (
                "Statuses",
                f":green_circle: {statuses[0]}\n:yellow_circle: {statuses[1]}\n:red_circle: {statuses[2]}\n:black_circle: {statuses[3]} [Blame Discord]",
                True,
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
        if info := [f":ballot_box_with_check: {label}" for feature, label in features.items() if feature in guild.features]:
            embed.add_field(name="Features", value="\n".join(info))

        boosts = f"Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts"
        if guild.premium_tier != 0:
            last_boost = max(guild.members, key=lambda member: member.premium_since or guild.created_at)
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
            embed.add_field(name="Banned Members", value=f"{len([_ async for _ in guild.bans(limit=1000)])}+", inline=True)
        if guild.me.guild_permissions.manage_guild:
            embed.add_field(name="Invites", value=f"{len(await guild.invites())}", inline=True)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

    @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def server_info(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """
        Display detailed information about the current server.

        The response includes the server owner, creation date, member counts,
        channel counts, roles, emojis, boost level, member statuses, server
        features, boost information, emoji availability, and other available
        server statistics.

        Additional information such as the number of bans and active invites is
        included when the bot has the required server permissions.

        The server icon is shown as the embed thumbnail and the server banner is
        shown as the embed image when available. The server ID is included in the
        embed footer.

        This command has a 5-second cooldown per member.
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
        for name, value, inline in self._server_summary_fields(ctx.guild):
            embed.add_field(name=name, value=value, inline=inline)
        await self._add_server_details(embed, ctx.guild)

        return await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def roleinfo(
        self,
        ctx: commands.Context[Parrot],
        *,
        role: discord.Role = commands.parameter(  # noqa: B008
            description="The role to display information about.",
        ),
    ) -> discord.Message:
        """
        Display detailed information about a server role.

        The response includes the role's creation date, position, hoist status,
        managed status, mentionability, member count, mention string, whether it
        is a premium subscriber role or bot-managed role, and its key permissions.

        The role's icon is displayed when available, with its Unicode emoji used
        as a fallback. The role ID is also included in the embed.

        This command has a 5-second cooldown per member.
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
            embed.set_thumbnail(
                url=f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-twitter-72/{ord(list(role.unicode_emoji)[0]):x}.png",
            )
        if role.icon:
            embed.set_thumbnail(url=role.icon.url)
        return await ctx.reply(embed=embed)

    @commands.command(name="channelinfo")
    async def channel_info(
        self,
        ctx: commands.Context[Parrot],
        *,
        channel: discord.abc.GuildChannel = commands.parameter(  # noqa: B008
            description="The channel to display information about.",
            default=lambda ctx: ctx.channel,
        ),
    ) -> discord.Message:
        """
        Display information about a server channel.

        If no channel is specified, the command displays information about the
        channel in which it was invoked. The response includes the channel name,
        ID, creation date, mention, position, and channel type.

        The channel information is presented in an embed with the server icon
        shown as the thumbnail when available.

        This command has no cooldown.
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


async def setup(bot: Parrot) -> None:
    """Load the Meta cog."""
    await bot.add_cog(Meta(bot))
