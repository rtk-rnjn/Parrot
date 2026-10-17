from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, channel_text, status_text
from .webhooks import can_manage_webhooks, create_webhook, delete_webhook

__all__ = ("GlobalChatPage",)

WEBHOOK_NAME = "Parrot Global Chat"


class GlobalChatPage(Page):
    key = "global_chat"
    label = "Global Chat"
    emoji = "\N{GLOBE WITH MERIDIANS}"
    description = "Relay one channel to the global chat shared by every server that opts in. Messages are delivered through a webhook."
    section = "global_chat_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["global_chat_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["global_chat_config"].get("channel_id")

    @property
    def webhook_uri(self) -> str | None:
        return self.config["global_chat_config"].get("webhook_uri")

    def summary(self) -> str:
        text = status_text(self.enabled)
        if self.channel_id:
            text += f" \N{MIDDLE DOT} relayed from {channel_text(self.guild, self.channel_id)}"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "the global chat toggle, channel and its webhook (the webhook is deleted)"

    def build(self) -> list[discord.ui.Item]:
        webhook = "\N{WHITE HEAVY CHECK MARK} Ready" if self.webhook_uri else "*Not created* \N{MIDDLE DOT} pick a channel below"
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Global chat channel", channel_text(self.guild, self.channel_id)),
                    ("Webhook", webhook),
                ]
            ),
            self.text("-# Bot needs the **Manage Webhooks** permission in the channel you pick."),
            self.row(self.toggle(self.enabled, self.set_enabled), self.reset_button()),
            self.row(self.channel_select("Global chat channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        if enabled and (self.channel_id is None or self.webhook_uri is None):
            await self.commit(interaction, "Pick a global chat channel first, then enable it.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_global_chat_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Global chat enabled. Messages in the channel are now relayed." if enabled else "Global chat disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        await self.dashboard.acknowledge(interaction)
        previous_uri = self.webhook_uri

        channel_id = channel_ids[0] if channel_ids else None
        if channel_id is None:
            await self.db.edit_global_chat_config(guild_id=self.guild.id, enabled=False, channel_id=None, webhook_uri=None)
            if previous_uri:
                await delete_webhook(self.bot, previous_uri)
            await self.commit(interaction, "Global chat channel cleared and global chat disabled.")
            return

        if channel_id == self.channel_id and previous_uri:
            await self.commit(interaction, f"Global chat already uses {channel_text(self.guild, channel_id)}.", level=NoticeLevel.INFO)
            return

        channel = self.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await self.commit(interaction, "Global chat needs a regular text channel.", level=NoticeLevel.ERROR)
            return
        if not can_manage_webhooks(channel):
            await self.commit(interaction, f"Bot needs **Manage Webhooks** in {channel.mention} to set that up.", level=NoticeLevel.ERROR)
            return

        try:
            webhook = await create_webhook(self.bot, channel, name=WEBHOOK_NAME)
        except discord.HTTPException as error:
            await self.commit(
                interaction, f"Discord refused to create a webhook in {channel.mention}: {error.text or error.status}", level=NoticeLevel.ERROR
            )
            return

        await self.db.edit_global_chat_config(guild_id=self.guild.id, channel_id=channel.id, webhook_uri=webhook.url)
        if previous_uri and previous_uri != webhook.url:
            await delete_webhook(self.bot, previous_uri)

        hint = "" if self.enabled else " Press Enable to start relaying."
        await self.commit(interaction, f"Global chat will use {channel.mention}.{hint}")

    async def reset(self) -> None:
        previous_uri = self.webhook_uri
        await super().reset()
        if previous_uri:
            await delete_webhook(self.bot, previous_uri)
