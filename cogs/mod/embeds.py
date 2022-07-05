from __future__ import annotations

import discord
from discord import Embed

MEMBER_EMBED: discord.Embed = Embed(
    title="Moderator Menu", timestamp=discord.utils.utcnow()
)
MEMBER_EMBED.add_field(name="Ban \N{HAMMER}", value="To ban a member", inline=True)
MEMBER_EMBED.add_field(
    name="Kick \N{WOMANS BOOTS}", value="To kick a member", inline=True
)
MEMBER_EMBED.add_field(
    name="Mute \N{ZIPPER-MOUTH FACE}", value="To mute a member", inline=True
)
MEMBER_EMBED.add_field(
    name="Unmute \N{GRINNING FACE WITH SMILING EYES}",
    value="To unmute a member",
    inline=True,
)
MEMBER_EMBED.add_field(
    name="Block \N{CROSS MARK}", value="To block a member", inline=True
)
MEMBER_EMBED.add_field(
    name="Unblock \N{HEAVY LARGE CIRCLE}", value="To unblock a member", inline=True
)
MEMBER_EMBED.add_field(
    name="Add role \N{UPWARDS BLACK ARROW}",
    value="To add a role to a member",
    inline=True,
)
MEMBER_EMBED.add_field(
    name="Remove role \N{DOWNWARDS BLACK ARROW}",
    value="To remove a role from a member",
    inline=True,
)
MEMBER_EMBED.add_field(
    name="Change Nickname \N{LOWER LEFT FOUNTAIN PEN}",
    value="To change a member's nickname",
    inline=True,
)


TEXT_CHANNEL_EMBED: discord.Embed = Embed(
    title="Moderator Menu", timestamp=discord.utils.utcnow()
)
TEXT_CHANNEL_EMBED.add_field(
    name="Lock \N{LOCK}", value="To lock a channel", inline=True
)
TEXT_CHANNEL_EMBED.add_field(
    name="Unlock \N{OPEN LOCK}", value="To unlock a channel", inline=True
)
TEXT_CHANNEL_EMBED.add_field(
    name="Change Name \N{LOWER LEFT FOUNTAIN PEN}",
    value="To change a channel's Name",
    inline=True,
)


VOICE_CHANNEL_EMBED = TEXT_CHANNEL_EMBED.copy()


ROLE_EMBED: discord.Embed = Embed(
    title="Moderator Menu", timestamp=discord.utils.utcnow()
)
ROLE_EMBED.add_field(
    name="Hoist \N{UPWARDS BLACK ARROW}", value="To hoist a role", inline=True
)
ROLE_EMBED.add_field(
    name="De-Hoist \N{DOWNWARDS BLACK ARROW}", value="To de-hoist a role", inline=True
)
ROLE_EMBED.add_field(
    name="Change Colour \N{RAINBOW}", value="To change a role's colour", inline=True
)
ROLE_EMBED.add_field(
    name="Change Name \N{LOWER LEFT FOUNTAIN PEN}",
    value="To change a role's name",
    inline=True,
)
