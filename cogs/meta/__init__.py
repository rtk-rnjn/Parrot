from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.utils import DeleteMessageButtonView

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.meta")


class Meta(commands.Cog):
    """Meta commands for the bot."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

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
        await self.bot.database_manager.ping_mongo_server()
        mongo_latency = (time.perf_counter() - mongo_start_time) * 1000

        redis_start_time = time.perf_counter()
        await self.bot.database_manager.ping_redis_server()
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
    async def user_info(  # noqa: C901
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
        key_permissions: list[str] = []

        if target.guild_permissions.administrator:
            key_permissions.append("Administrator")

        if target.guild_permissions.kick_members and target.guild_permissions.ban_members and target.guild_permissions.manage_messages:
            key_permissions.append("Server Moderator")

        if target.guild_permissions.manage_guild:
            key_permissions.append("Server Manager")

        if target.guild_permissions.manage_roles:
            key_permissions.append("Role Manager")

        if target.guild_permissions.moderate_members:
            key_permissions.append("Can Timeout Members")

        if target.guild_permissions.manage_channels:
            key_permissions.append("Channel Manager")

        if target.guild_permissions.manage_messages:
            key_permissions.append("Message Manager")

        if target.guild_permissions.mention_everyone:
            key_permissions.append("Mention Everyone")

        permissions = ", ".join(key_permissions) if key_permissions else "None"

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

        embed = (
            discord.Embed(
                title=f"{target}'s Avatar",
                colour=target.colour,
                timestamp=discord.utils.utcnow(),
            )
            .set_image(url=target.display_avatar.url)
            .set_footer(text=f"ID: {target.id}")
        )

        if target != ctx.author:
            content = f"Requested by: {ctx.author.mention}"
        else:
            content = None

        delete_view = DeleteMessageButtonView(author=ctx.author)
        message = await ctx.reply(content, embed=embed, view=delete_view)
        delete_view.message = message

        return message

    @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def server_info(self, ctx: commands.Context[Parrot]) -> discord.Message:  # noqa: C901, PLR0912
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
        statuses = [
            len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
            len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members))),
        ]

        fields = [
            ("Owner", ctx.guild.owner, True),
            ("Region", "Deprecated", True),
            ("Created at", f"{discord.utils.format_dt(ctx.guild.created_at)}", True),
            (
                "Total Members",
                (
                    f"Members: {len(ctx.guild.members)}\n"
                    f"Humans: {len(list(filter(lambda m: not m.bot, ctx.guild.members)))}\n"
                    f"Bots: {len(list(filter(lambda m: m.bot, ctx.guild.members)))}"
                ),
                True,
            ),
            (
                "Total channels",
                (f"Categories: {len(ctx.guild.categories)}\nText: {len(ctx.guild.text_channels)}\nVoice:{len(ctx.guild.voice_channels)}"),
                True,
            ),
            (
                "General",
                (f"Roles: {len(ctx.guild.roles)}\nEmojis: {len(ctx.guild.emojis)}\nBoost Level: {ctx.guild.premium_tier}"),
                True,
            ),
            (
                "Statuses",
                (
                    f":green_circle: {statuses[0]}\n"
                    f":yellow_circle: {statuses[1]}\n"
                    f":red_circle: {statuses[2]}\n"
                    f":black_circle: {statuses[3]} [Blame Discord]"
                ),
                True,
            ),
        ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

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

        if info := [f":ballot_box_with_check: {label}" for feature, label in all_features.items() if feature in features]:
            embed.add_field(name="Features", value="\n".join(info))

        if ctx.guild.premium_tier != 0:
            boosts = f"Level {ctx.guild.premium_tier}\n{ctx.guild.premium_subscription_count} boosts"

            def key(m: discord.Member) -> datetime:
                if ctx.guild is None:
                    return discord.utils.utcnow()

                return m.premium_since or ctx.guild.created_at

            last_boost = max(ctx.guild.members, key=key)
            if last_boost.premium_since is not None:
                boosts = f"{boosts}\nLast Boost: {last_boost} ({discord.utils.format_dt(last_boost.premium_since, 'R')})"
            embed.add_field(name="Boosts", value=boosts, inline=True)
        else:
            embed.add_field(name="Boosts", value="Level 0", inline=True)

        emoji_stats = Counter()
        for emoji in ctx.guild.emojis:
            if emoji.animated:
                emoji_stats["animated"] += 1
                emoji_stats["animated_disabled"] += not emoji.available
            else:
                emoji_stats["regular"] += 1
                emoji_stats["disabled"] += not emoji.available

        fmt = f"Regular: {emoji_stats['regular']}/{ctx.guild.emoji_limit}\nAnimated: {emoji_stats['animated']}/{ctx.guild.emoji_limit}\n"
        if emoji_stats["disabled"] or emoji_stats["animated_disabled"]:
            fmt = f"{fmt}Disabled: {emoji_stats['disabled']} regular, {emoji_stats['animated_disabled']} animated\n"

        fmt = f"{fmt}Total Emoji: {len(ctx.guild.emojis)}/{ctx.guild.emoji_limit * 2}"
        embed.add_field(name="Emoji", value=fmt, inline=True)

        if ctx.guild.me.guild_permissions.ban_members:
            embed.add_field(
                name="Banned Members",
                value=f"{len([_ async for _ in ctx.guild.bans(limit=1000)])}+",
                inline=True,
            )
        if ctx.guild.me.guild_permissions.manage_guild:
            embed.add_field(name="Invites", value=f"{len(await ctx.guild.invites())}", inline=True)

        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner.url)

        return await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(
        rate=1,
        per=5.0,
        type=commands.BucketType.member,
    )
    async def roleinfo(  # noqa: C901
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
        perms = []
        if role.permissions.administrator:
            perms.append("Administrator")
        if role.permissions.kick_members and role.permissions.ban_members and role.permissions.manage_messages:
            perms.append("Server Moderator")
        if role.permissions.manage_guild:
            perms.append("Server Manager")
        if role.permissions.manage_roles:
            perms.append("Role Manager")
        if role.permissions.moderate_members:
            perms.append("Can Timeout Members")
        if role.permissions.manage_channels:
            perms.append("Channel Manager")
        if role.permissions.manage_emojis:
            perms.append("Emoji Manager")
        embed.description = f"Key perms: {', '.join(perms or ['N/A'])}"
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
