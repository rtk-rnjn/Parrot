from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands

from core.utils import BaseLayoutView

from .automod import Rule

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration

VALID_RULE_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)


class AutomodListModal(discord.ui.Modal):
    def __init__(self, *, title: str, data: list[str] | None = None):
        super().__init__(title=title)
        self.data = data or []

        self.list_input = discord.ui.TextInput(
            label="Items (one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Enter one item per line.",
            default="\n".join(self.data),
            required=False,
        )
        self.add_item(self.list_input)


class AutomodEditListButton(discord.ui.Button):
    def __init__(self, *, title: str, list_name: str) -> None:
        super().__init__(style=discord.ButtonStyle.secondary, emoji="\N{PENCIL}")
        self.title = title
        self.list_name = list_name

    def modal_submit_callback(self, modal: AutomodListModal, config: GuildConfiguration):
        async def callback(interaction: discord.Interaction[Parrot]) -> None:
            new_data = [item.strip() for item in modal.list_input.value.splitlines() if item.strip()]
            try:
                config["automod"][self.list_name] = new_data
            except KeyError:
                config["automod"]["custom_lists"][self.list_name] = new_data

            await interaction.response.send_message(f"Updated {self.title}.", ephemeral=True)

        return callback

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        config: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild_id)  # type: ignore
        try:
            data = config["automod"][self.list_name]
        except KeyError:
            data = config["automod"]["custom_lists"].get(self.list_name, [])

        modal = AutomodListModal(title=self.title, data=data)
        modal.on_submit = self.modal_submit_callback(modal, config)
        await interaction.response.send_modal(modal)
        await modal.wait()


class AutomodLayoutView(BaseLayoutView):
    def __init__(self, *, author: discord.User | discord.Member):
        super().__init__(author=author)

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## Automod Rule Management\n"
                "An advanced automoderation system designed to support complex, highly configurable rules beyond the capabilities of a basic automoderator.\n"
                "It provides greater flexibility and supports more complex configurations, at the cost of requiring some initial setup."
                "The Advanced Automoderator is driven by user-defined rules, where specific actions and conditions act as triggers to execute the configured effects.",
            ),
            discord.ui.Separator(),
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### Lists\n"
                    "Lists store words or domains that can be referenced as blacklist or whitelist triggers in your rules.\n"
                    "For word lists, entries must be single words with no spaces. Multiple entries can be separated by newlines or spaces. To match complete phrases, use a regex trigger instead.\n"
                    "For website/link lists, provide only the domain name without the protocol or URL path. Subdomains are matched automatically. If you want to restrict matching to a specific subdomain and its nested subdomains, specify that subdomain directly.",
                ),
                accessory=discord.ui.Button(
                    emoji="\N{PENCIL}",
                    style=discord.ButtonStyle.secondary,
                ),
            ),
            discord.ui.Separator(),
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### Rules\n"
                    "Rules are the core building blocks of your automoderator configuration. Each rule is composed of triggers, conditions, and effects, collectively referred to as rule parts."
                    "A rule can contain multiple triggers, conditions, and effects. Each component is optional, but a rule without at least one trigger and effect has nothing to execute."
                    "When evaluating a rule, triggers use OR logic, while conditions and effects use AND logic. In other words, a rule is considered applicable when at least one trigger matches and all conditions are satisfied. Once matched, all effects defined by the rule are executed.",
                ),
                accessory=discord.ui.Button(
                    emoji="\N{PENCIL}",
                    style=discord.ButtonStyle.secondary,
                ),
            ),
        )
        self.add_item(container)


class Automod(commands.Cog):
    """Automod rule management."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod feature."""
        view = AutomodLayoutView(author=ctx.author)
        await ctx.reply(view=view)

    @automod.command(name="logs", aliases=["log"])
    @commands.has_permissions(administrator=True)
    async def automod_logs(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod logging feature."""
        await ctx.reply("Logs")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Automod(bot))
