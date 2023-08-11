from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .ipc import IPCRoutes


def channel_to_json(self: IPCRoutes, channel: discord.abc.GuildChannel) -> dict:
    return {
        "id": channel.id,
        "name": channel.name,
        "type": channel.type.value,
        "position": channel.position,
        "category_id": channel.category_id,
        "guild_id": channel.guild.id,
        "nsfw": getattr(channel, "nsfw", None),
        "sync_permissions": channel.permissions_synced,
        "topic": getattr(channel, "topic", None),
        "slowmode_delay": getattr(channel, "slowmode_delay", None),
        "overwrites": self._overwrite_to_json(channel.overwrites),
    }


def role_to_json(role: discord.Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions.value,
        "position": role.position,
        "color": role.color.value,
        "hoist": role.hoist,
        "managed": role.managed,
        "mentionable": role.mentionable,
        "guild_id": role.guild.id,
        "unicode_emoji": getattr(role, "unicode_emoji", None),
    }


def member_to_json(member: discord.Member) -> dict:
    return {
        "id": member.id,
        "name": member.name,
        "display_name": member.display_name,
        "global_name": member.global_name,
        "discriminator": member.discriminator,
        "nick": member.nick,
        "avatar_url": getattr(member.avatar, "url", None),
        "display_avatar_url": member.display_avatar.url,
        "guild_id": member.guild.id,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        "created_at": member.created_at.isoformat(),
        "premium_since": member.premium_since.isoformat() if member.premium_since else None,
        "roles": [role.id for role in member.roles],
        "color": member.color.value,
        "bot": member.bot,
    }


def emoji_to_json(emoji: discord.Emoji) -> dict:
    return {
        "id": emoji.id,
        "name": emoji.name,
        "animated": emoji.animated,
        "url": emoji.url,
        "roles": [role.id for role in emoji.roles],
        "available": emoji.available,
        "managed": emoji.managed,
    }


def thread_to_json(thread: discord.Thread) -> dict:
    return {
        "id": thread.id,
        "name": thread.name,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "owner_id": thread.owner_id,
        "parent_id": thread.parent_id,
        "slowmod_delay": thread.slowmode_delay,
        "archived": thread.archived,
        "locked": thread.locked,
    }


def user_to_json(user: discord.User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "display_name": user.display_name,
        "discriminator": user.discriminator,
        "avatar_url": getattr(user.avatar, "url", None),
        "display_avatar_url": user.display_avatar.url,
        "bot": user.bot,
        "system": user.system,
        "created_at": user.created_at.isoformat(),
    }
