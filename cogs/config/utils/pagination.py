from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration


class GotoPageModal(discord.ui.Modal, title="Go to Page"):
    def __init__(self, *, max_page: int, current_page: int) -> None:
        super().__init__()

        self.max_page = max_page

        self.page_input = discord.ui.TextInput(
            label="Page Number",
            placeholder=f"Enter a page number between 1 and {self.max_page}",
            required=True,
            default=str(current_page),
            max_length=len(str(self.max_page)),
            min_length=1,
        )

        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot], /) -> None:
        try:
            page_number = int(self.page_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "Invalid page number. Please enter a valid integer.",
                ephemeral=True,
            )
            return

        if not (1 <= page_number <= self.max_page):
            await interaction.response.send_message(
                f"Page number must be between 1 and {self.max_page}.",
                ephemeral=True,
            )
            return

        self.stop()


class PaginationLayout[I: discord.ui.Item](discord.ui.LayoutView):
    def __init__(
        self,
        author: discord.User | discord.Member,
        *,
        header: I,
        footer: I,
        items: list[list[I]],
        **kwargs: Unpack[GuildConfiguration],
    ) -> None:
        super().__init__()
        self.author = author
        self.header = header
        self.footer = footer
        self.items = items
        self.current_index = 0
        self.kwargs = kwargs

        if not self.items:
            raise ValueError("Items list cannot be empty.")

        # [ < ] [ 1 / 3 ] [ > ]
        next_disabled = len(self.items) <= 1
        style = discord.ButtonStyle.secondary

        self.previous_button = discord.ui.Button(emoji="\N{BLACK LEFT-POINTING TRIANGLE}", style=style, disabled=True)
        self.next_button = discord.ui.Button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", style=style, disabled=next_disabled)
        self.current_button = discord.ui.Button(label=f"{self.current_index + 1} / {len(self.items)}", style=style, disabled=next_disabled)

        self._pagination_buttons = discord.ui.ActionRow(self.previous_button, self.current_button, self.next_button)

        self.container = discord.ui.Container(
            self.header,
            discord.ui.Separator(),
            *self.items[self.current_index],
            discord.ui.Separator(),
            self.footer,
        )
        self.add_item(self.container)
        self.add_item(self._pagination_buttons)

    async def interaction_check(self, interaction: discord.Interaction[Parrot], /) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True

    async def update_page(self, interaction: discord.Interaction[Parrot], /) -> None:
        self.container.clear_items()
        self.container.add_item(self.header)
        self.container.add_item(discord.ui.Separator())
        for item in self.items[self.current_index]:
            self.container.add_item(item)

        self.container.add_item(discord.ui.Separator())
        self.container.add_item(self.footer)

        self.current_button.label = f"{self.current_index + 1} / {len(self.items)}"
        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index == len(self.items) - 1

        await interaction.response.edit_message(view=self)

    async def previous_page_callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            await self.update_page(interaction)

    async def next_page_callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
            await self.update_page(interaction)

    async def goto_page_callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        goto_page_modal = GotoPageModal(max_page=len(self.items), current_page=self.current_index + 1)
        await interaction.response.send_modal(goto_page_modal)
        await goto_page_modal.wait()

        if goto_page_modal.page_input.value is None:
            return

        try:
            page_number = int(goto_page_modal.page_input.value.strip())
        except ValueError:
            await interaction.followup.send("Invalid page number. Please enter a valid integer.", ephemeral=True)
            return

        if not (1 <= page_number <= len(self.items)):
            await interaction.followup.send(f"Page number must be between 1 and {len(self.items)}.", ephemeral=True)
            return

        self.current_index = page_number - 1
        await self.update_page(interaction)
