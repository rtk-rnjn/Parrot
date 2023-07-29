from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from .settings import ACTION_SETTINGS, DEFCON_SETTINGS

if TYPE_CHECKING:
    from .events import DefconListeners

log = logging.getLogger("cogs.defcon")


class DefensiveCondition(Cog):
    """Powerful Raid Protection."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        """
        {
            "_id": guild_id,
            ...
            "default_defcon": {
                "enabled": False,
                "level": 0,
                "trustables": {
                    "roles": [],
                    "members": [],
                    "members_with_admin": True,
                },
                "locked_channels": [],
                "hidden_channels": [],
                "broadcast": {
                    "enabled": False,
                    "channel": None,
                },
            },
        }
        """

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{MILITARY HELMET}")

    @commands.group(name="defcon", aliases=["dc"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def defcon(self, ctx: Context) -> None:
        """Manage defcon settings."""
        if ctx.invoked_subcommand is None:
            defcon_help = (
                "**`Def`ensive `Con`dition**"
                "\n\n"
                "Defcon is a system that allows you to lock down your server in case of a raid or other emergency. "
                "It allows you to lock down your server in a variety of ways, such as locking channels, preventing users from joining, and more."
                "\n\n"
                "> :warning: **WARNING** :warning:\n"
                f"> - {self.bot.user.name} is highly tested, but there is always a chance that it may fail to lock down your server.\n"
                "> - Make sure you trust your moderators, as they can bypass defcon.\n"
                f"> - {self.bot.user.name} will work more properly if it has a higher role.\n"
                "> - Bot must also have proper permissions as to lock down channels, delete invites, etc."
                "\n\n"
                "DEFCON is NOT spam protection. It is RAID protection. It is meant to be used in case of an emergency."
            )

            embed = discord.Embed(
                title="Defcon",
                description=defcon_help,
                color=self.bot.color,
            )
            await ctx.reply(embed=embed)

    def view_defcon_settings(self, level: int) -> discord.Embed:
        defcon = DEFCON_SETTINGS[level]
        embed = discord.Embed(
            title=f"Defcon {level}",
            description=defcon["description"],
            color=self.bot.color,
        )
        settings = defcon["SETTINGS"]
        for setting, value in settings.items():
            embed.add_field(
                name=ACTION_SETTINGS[setting]["name"].replace("_", " ").title(),
                value=f"**{value}**",
                inline=False,
            )

        return embed

    async def defcon_set(self, ctx: Context, level: int) -> None:
        # sourcery skip: use-named-expression
        """Set the level of defcon."""
        channel_hidded = []
        settings = DEFCON_SETTINGS[level]["SETTINGS"]
        if settings.get("HIDE_CHANNELS"):
            for channel in ctx.guild.channels:
                if channel.permissions_for(ctx.guild.default_role).read_messages:
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(read_messages=False)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Setting DEFON {level}. Invoked by {ctx.author}",
                        )
                        channel_hidded.append(channel.id)
                    except discord.Forbidden:
                        log.warning("failed to hide channel %s in guild %s", channel.id, ctx.guild.id)

        if channel_hidded:
            await self.bot.guild_configurations.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"default_defcon.hidden_channels": channel_hidded}},
                upsert=True,
            )

        channel_locked = []
        if settings.get("LOCK_VOICE_CHANNELS"):
            for channel in ctx.guild.voice_channels:
                if channel.permissions_for(ctx.guild.default_role).connect:
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(connect=False)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Setting DEFCON {level}. Invoked by {ctx.author}",
                        )
                        channel_locked.append(channel.id)
                    except discord.Forbidden:
                        log.warning("failed to lock channel %s in guild %s", channel.id, ctx.guild.id)

        if settings.get("LOCK_TEXT_CHANNELS"):
            for channel in ctx.guild.text_channels:
                if channel.permissions_for(ctx.guild.default_role).send_messages:
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(send_messages=False)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Setting DEFCON {level}. Invoked by {ctx.author}",
                        )
                        channel_locked.append(channel.id)
                    except discord.Forbidden:
                        log.warning("failed to lock channel %s in guild %s", channel.id, ctx.guild.id)

        if channel_locked:
            await self.bot.guild_configurations.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"default_defcon.locked_channels": channel_locked}},
                upsert=True,
            )

        count = 0
        if settings.get("SLOWMODE") and settings.get("SLOWMODE_TIME"):
            for channel in ctx.guild.text_channels:
                if channel.id not in channel_locked:
                    continue
                try:
                    await channel.edit(
                        slowmode_delay=DEFCON_SETTINGS[level]["SLOWMODE_TIME"],
                        reason=f"Setting DEFCON {level}. Invoked by {ctx.author}",
                    )
                    count += 1
                except discord.Forbidden:
                    log.warning("failed to set slowmode in channel %s in guild %s", channel.id, ctx.guild.id)

        cog: DefconListeners = self.bot.get_cog("DefconListeners")  # type: ignore
        if cog:
            embed = discord.Embed(title=f"DEFCON {level}", color=self.bot.color).set_footer(
                text=f"Invoked by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            embed.description = (
                f"**{ctx.author}** has set the defcon level to {level}.\n\n"
                f"`Total Channels Locked  `: **{len(channel_locked)}**\n"
                f"`Total Channels Hidden  `: **{len(channel_hidded)}**\n"
                f"`Total Channels Affected`: **{len(channel_locked) + len(channel_hidded)}**\n"
                f"`Channels With Slowmode `: **{count}**\n\n"
                f"> **Use `defcon reset` to reset the defcon level.**"
            )
            await cog.defcon_broadcast(embed, guild=ctx.guild, level=level)

    async def defcon_reset(self, ctx: Context, level: int) -> None:
        """Reset the level of defcon."""
        guild_config = await self.bot.guild_configurations.find_one({"_id": ctx.guild.id})
        if not guild_config or not guild_config.get("default_defcon"):
            await ctx.reply("Defcon is not set.")
            return

        settings = DEFCON_SETTINGS[level]["SETTINGS"]
        if settings.get("HIDE_CHANNELS"):
            for channel_id in guild_config["default_defcon"].get("hidden_channels", []):
                if channel := ctx.guild.get_channel(channel_id):
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(read_messages=None)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Resetting DEFCON {level}. Invoked by {ctx.author}",
                        )

                    except discord.Forbidden:
                        log.warning("failed to reset channel %s in guild %s", channel.id, ctx.guild.id)

        count = 0
        if settings.get("LOCK_VOICE_CHANNELS"):
            for channel_id in guild_config["default_defcon"].get("locked_channels", []):
                if channel := ctx.guild.get_channel(channel_id):
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(connect=None)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Resetting DEFCON {level}. Invoked by {ctx.author}",
                        )
                        count += 1
                    except discord.Forbidden:
                        log.warning("failed to reset channel %s in guild %s", channel.id, ctx.guild.id)

        if settings.get("LOCK_TEXT_CHANNELS"):
            for channel_id in guild_config["default_defcon"].get("locked_channels", []):
                if channel := ctx.guild.get_channel(channel_id):
                    try:
                        overwrite = channel.overwrites_for(ctx.guild.default_role)
                        overwrite.update(send_messages=None)
                        await self.bot.wait_until_ready()
                        await channel.set_permissions(
                            ctx.guild.default_role,
                            overwrite=overwrite,
                            reason=f"Resetting DEFCON {level}. Invoked by {ctx.author}",
                        )
                        count += 1
                    except discord.Forbidden:
                        log.warning("failed to reset channel %s in guild %s", channel.id, ctx.guild.id)

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "default_defcon.locked_channels": [],
                    "default_defcon.hidden_channels": [],
                },
            },
            upsert=True,
        )

        slow_mode_count = 0
        if settings.get("SLOWMODE") and settings.get("SLOWMODE_TIME"):
            for channel in ctx.guild.text_channels:
                if channel.id in guild_config["default_defcon"]["locked_channels"]:
                    continue
                try:
                    await channel.edit(
                        slowmode_delay=0,
                        reason=f"Resetting DEFCON {level}. Invoked by {ctx.author}",
                    )
                    slow_mode_count += 1
                except discord.Forbidden:
                    log.warning("failed to reset slowmode in channel %s in guild %s", channel.id, ctx.guild.id)

        if cog := self.bot.get_cog("DefconListeners"):
            embed = discord.Embed(title=f"DEFCON {level}", color=self.bot.color).set_footer(
                text=f"Invoked by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            embed.description = (
                f"**{ctx.author}** has reset the defcon level to {level}.\n\n"
                f"`Total Channels Unlocked`: **{count}**\n"
                f"`Channels With Slowmode `: **{slow_mode_count}**\n\n"
                f"> **Use `defcon set` to set the defcon level.**"
            )
            await cog.defcon_broadcast(embed, guild=ctx.guild, level=level)  # type: ignore

    @defcon.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def _defcon_set(self, ctx: Context, *, level: Literal[1, 2, 3, 4, 5] = 1) -> None:
        """Set the level of defcon."""

        prompt = await ctx.prompt(
            f"**Are you sure you want to set defcon to {level}?**",
            embed=self.view_defcon_settings(level),
            timeout=60,
        )
        if not prompt:
            await ctx.reply("Cancelled.")
            return

        msg = await ctx.reply("Setting defcon...")
        await self.defcon_set(ctx, level)
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.level": level}},
            upsert=True,
        )
        if msg:
            await msg.edit(content="Defcon set.", delete_after=5)

    @defcon.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def _defcon_reset(self, ctx: Context) -> None:
        """Reset the defcon level."""
        default_defcon = self.bot.guild_configurations_cache[ctx.guild.id].get("default_defcon", {})
        level = default_defcon.get("level", -1)
        if level == -1:
            await ctx.reply("Defcon is not set.")
            return

        prompt = await ctx.prompt("**Are you sure you want to reset defcon?**", timeout=60)
        if not prompt:
            await ctx.reply("Cancelled.")
            return

        msg = await ctx.reply("Resetting defcon...")
        await self.defcon_reset(ctx, level)
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$unset": {"default_defcon": ""}},
            upsert=True,
        )
        if msg:
            await msg.edit(content="Defcon reset.", delete_after=5)

    @defcon.command(name="settings")
    @commands.has_permissions(manage_guild=True)
    async def defcon_settings(self, ctx: Context) -> None:
        """View the current defcon settings."""
        guild_config = await self.bot.guild_configurations.find_one(
            {"_id": ctx.guild.id, "default_defcon": {"$exists": True}},
        )
        if not guild_config or "level" not in guild_config["default_defcon"]:
            await ctx.reply("No defcon settings found.")
            return

        await ctx.reply(embed=self.view_defcon_settings(guild_config["default_defcon"]["level"]))

    @defcon.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def defcon_enable(self, ctx: Context) -> None:
        """Enable defcon."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.enabled": True}},
            upsert=True,
        )
        await ctx.reply("Defcon enabled.")

    @defcon.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def defcon_disable(self, ctx: Context) -> None:
        """Disable defcon."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.enabled": False}},
            upsert=True,
        )
        await ctx.reply("Defcon disabled.")

    @defcon.command(name="broadcast")
    @commands.has_permissions(manage_guild=True)
    async def defcon_broadcast(self, ctx: Context, channel: discord.TextChannel = None) -> None:
        """Set the broadcast channel for defcon."""
        if not channel:
            await self.bot.guild_configurations.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"default_defcon.broadcast.enabled": False}},
                upsert=True,
            )
            await ctx.reply("Broadcast disabled.")
            return

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.broadcast.enabled": True, "default_defcon.broadcast.channel": channel.id}},
            upsert=True,
        )
        await ctx.reply(f"Broadcast enabled in {channel.mention}.")

    @defcon.group(name="trustables", aliases=["trustable"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def defcon_trustables(self, ctx: Context) -> None:
        """Manage trustable roles."""
        if ctx.invoked_subcommand is None:
            guild_config = self.bot.guild_configurations_cache[ctx.guild.id]

            if "default_defcon" not in guild_config:
                await ctx.reply("No defcon settings found.")
                return

            trustables = guild_config["default_defcon"].get("trustables", {})
            if not trustables:
                await ctx.reply("No trustable roles found.")
                return

            trustable_roles = []
            for role_id in trustables.get("roles", []):
                if role := ctx.guild.get_role(role_id):
                    trustable_roles.append(role)

            trustable_members = []
            for member_id in trustables.get("members", []):
                if member := ctx.guild.get_member(member_id):
                    trustable_members.append(member)

            if not trustable_members and not trustable_roles:
                await ctx.reply("No trustable roles or members found.")

            embed = discord.Embed(
                title="Trustable Roles",
                description="These roles are allowed to bypass defcon.",
                color=self.bot.color,
            )
            if trustable_members:
                embed.add_field(
                    name="Members",
                    value=", ".join([member.mention for member in trustable_members]),
                    inline=False,
                )
            if trustable_roles:
                embed.add_field(
                    name="Roles",
                    value=", ".join([role.mention for role in trustable_roles]),
                    inline=False,
                )

            await ctx.reply(embed=embed)

    @defcon_trustables.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def defcon_trustables_add(self, ctx: Context, *roles_or_members: discord.Role | discord.Member) -> None:
        """To add trustable roles or members."""
        guild_config = self.bot.guild_configurations_cache[ctx.guild.id]

        if "default_defcon" not in guild_config:
            await ctx.reply("No defcon settings found.")
            return

        trustables = guild_config["default_defcon"].get("trustables", {}) or {"roles": [], "members": []}

        for role_or_member in roles_or_members:
            if isinstance(role_or_member, discord.Role):
                if role_or_member.id in trustables["roles"]:
                    continue

                trustables["roles"].append(role_or_member.id)
            elif isinstance(role_or_member, discord.Member):
                if role_or_member.id in trustables["members"]:
                    continue

                trustables["members"].append(role_or_member.id)

        roles = trustables.get("roles", [])
        members = trustables.get("members", [])

        if roles or members:
            await ctx.reply("Trustable roles and members added.")
        else:
            await ctx.reply("No trustable roles or members added.")
            return

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.trustables": trustables}},
            upsert=True,
        )

    @defcon_trustables.command(name="remove", aliases=["delete", "del", "rm"])
    @commands.has_permissions(manage_guild=True)
    async def defcon_trustables_remove(self, ctx: Context, *roles_or_members: discord.Role | discord.Member) -> None:
        """To remove trustable roles or members."""
        guild_config = self.bot.guild_configurations_cache[ctx.guild.id]

        if "default_defcon" not in guild_config:
            await ctx.reply("No defcon settings found.")
            return

        trustables = guild_config["default_defcon"].get("trustables", {})
        if not trustables:
            await ctx.reply("No trustable roles or members found.")
            return

        for role_or_member in roles_or_members:
            if isinstance(role_or_member, discord.Role):
                if role_or_member.id in trustables["roles"]:
                    trustables["roles"].remove(role_or_member.id)
            elif isinstance(role_or_member, discord.Member):
                if role_or_member.id in trustables["members"]:
                    trustables["members"].remove(role_or_member.id)

        roles = trustables.get("roles", [])
        members = trustables.get("members", [])

        if roles or members:
            await ctx.reply("Trustable roles and members removed.")
        else:
            await ctx.reply("No trustable roles or members removed.")
            return

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.trustables": trustables}},
            upsert=True,
        )

    @defcon_trustables.command(name="admin")
    @commands.has_permissions(manage_guild=True)
    async def defcon_trustables_admin(self, ctx: Context) -> None:
        """To add admin as trustable."""
        guild_config = self.bot.guild_configurations_cache[ctx.guild.id]

        if "default_defcon" not in guild_config:
            await ctx.reply("No defcon settings found.")
            return

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.trustables.members_with_admin": True}},
            upsert=True,
        )

        await ctx.reply("Admin added as trustable.")

    @defcon_trustables.command(name="removeadmin")
    @commands.has_permissions(manage_guild=True)
    async def defcon_trustables_removeadmin(self, ctx: Context) -> None:
        """To remove admin as trustable."""
        guild_config = self.bot.guild_configurations_cache[ctx.guild.id]

        if "default_defcon" not in guild_config:
            await ctx.reply("No defcon settings found.")
            return

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"default_defcon.trustables.members_with_admin": False}},
            upsert=True,
        )

        await ctx.reply("Admin removed as trustable.")

    @Cog.listener()
    async def on_command(self, ctx: Context) -> None:
        if ctx.cog and ctx.cog.qualified_name == "DefensiveCondition":
            self.bot.update_server_config_cache.start(ctx.guild.id)
