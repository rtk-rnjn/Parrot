from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, PageModal

__all__ = ("GeneralPage",)

PREFIX_MAX_LENGTH = 16


class PrefixModal(PageModal):
    def __init__(self, page: GeneralPage, *, current: str) -> None:
        super().__init__(page, title="Change the command prefix")
        self.prefix_input = discord.ui.TextInput(
            placeholder="! or ? or p.",
            default=current,
            min_length=1,
            max_length=PREFIX_MAX_LENGTH,
        )
        self.add_item(
            discord.ui.Label(
                text="Prefix",
                description="Typed before every text command, for example `!help`. Mentioning the bot always works too.",
                component=self.prefix_input,
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        prefix = self.prefix_input.value.strip()
        if not prefix:
            await self.page.commit(interaction, "The prefix cannot be blank.", level=NoticeLevel.ERROR)
            return
        if any(character.isspace() for character in prefix):
            await self.page.commit(interaction, "The prefix cannot contain spaces.", level=NoticeLevel.ERROR)
            return

        await self.page.db.edit_prefix_config(guild_id=self.page.guild.id, command_prefix=prefix)
        await self.page.commit(interaction, f"Prefix changed to `{prefix}`.")


class GeneralPage(Page):
    key = "general"
    label = "General"
    emoji = "\N{GEAR}\N{VARIATION SELECTOR-16}"
    description = "Bot-wide behaviour in this server."
    section = "command_prefix"

    @property
    def prefix(self) -> str:
        return self.config.get("command_prefix") or self.bot.DEFAULT_PREFIX

    def summary(self) -> str:
        return f"prefix `{self.prefix}`"

    def reset_summary(self) -> str:
        return f"the command prefix (back to `{self.bot.DEFAULT_PREFIX}`)"

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status(
                [
                    ("Command prefix", f"`{self.prefix}`"),
                    ("Also accepted", f"{self.bot.user.mention} followed by a command"),
                ]
            ),
            self.text("-# Text-command prefixes are being phased out in favour of slash commands."),
            self.row(
                self.button("Change prefix\N{HORIZONTAL ELLIPSIS}", self.open_prefix_modal, style=discord.ButtonStyle.primary, emoji="\N{PENCIL}"),
                self.reset_button(),
            ),
        ]

    async def open_prefix_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(PrefixModal(self, current=self.prefix))
