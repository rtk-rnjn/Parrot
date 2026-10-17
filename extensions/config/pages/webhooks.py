from __future__ import annotations

import contextlib
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Bot

__all__ = ("can_manage_webhooks", "create_webhook", "delete_webhook", "resolve_webhook_channels", "webhook_id_from_uri")

_WEBHOOK_ID_RE = re.compile(r"/webhooks/(\d+)/")


def webhook_id_from_uri(uri: str) -> int | None:
    match = _WEBHOOK_ID_RE.search(uri)
    return int(match[1]) if match else None


def can_manage_webhooks(channel: discord.TextChannel) -> bool:
    me = channel.guild.me
    return me is not None and channel.permissions_for(me).manage_webhooks


async def resolve_webhook_channels(guild: discord.Guild, uris: Iterable[str]) -> dict[str, int | None] | None:
    """Map each webhook URI to the channel it posts in.

    A URI maps to ``None`` when its webhook has been deleted. The whole result is ``None``
    when the bot cannot list the server's webhooks, so callers can tell "unknown" from "gone".
    """
    wanted = {uri: webhook_id_from_uri(uri) for uri in uris}
    if not wanted:
        return {}

    me = guild.me
    if me is None or not me.guild_permissions.manage_webhooks:
        return None

    try:
        webhooks = await guild.webhooks()
    except discord.HTTPException:
        return None

    channels = {webhook.id: webhook.channel_id for webhook in webhooks}
    return {uri: channels.get(webhook_id) for uri, webhook_id in wanted.items() if webhook_id is not None}


async def create_webhook(bot: Bot, channel: discord.TextChannel, *, name: str) -> discord.Webhook:
    """Create a webhook in ``channel`` wearing the bot's avatar. Raises :class:`discord.HTTPException`."""
    avatar: bytes | None = None
    with contextlib.suppress(discord.HTTPException):
        avatar = await bot.user.display_avatar.read()
    return await channel.create_webhook(name=name, avatar=avatar, reason="Configured through the settings dashboard")


async def delete_webhook(bot: Bot, uri: str) -> None:
    """Delete a webhook by URI, ignoring ones that are already gone or malformed."""
    with contextlib.suppress(ValueError, discord.HTTPException):
        webhook = discord.Webhook.from_url(uri, client=bot)
        await webhook.delete(reason="Removed through the settings dashboard", prefer_auth=False)
