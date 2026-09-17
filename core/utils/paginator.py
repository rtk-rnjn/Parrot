from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot


class GotoPageModal(discord.ui.Modal, title="Go to Page"):
    def __init__(self, *, max_page: int, current_page: int) -> None:
        super().__init__()

        self.page_input = discord.ui.TextInput(
            label="Page Number",
            placeholder=f"Enter a page number between 1 and {max_page} (inclusive)",
            required=True,
            default=str(current_page),
            max_length=len(str(max_page)),
            min_length=1,
        )
        self.add_item(self.page_input)


class PaginationMixin[PageT: discord.Embed | list[discord.ui.Item]]:
    """Shared pagination behaviour for pagination views."""

    message: discord.Message | None = None
    author: discord.User | discord.Member
    hide_quit_button: bool
    hide_skip_button: bool

    current_index: int
    items: list[PageT]

    def _setup_pagination_buttons(self) -> None:
        muted = discord.ButtonStyle.secondary
        clickable = discord.ButtonStyle.primary
        disabled = len(self.items) <= 1

        self.first_button = discord.ui.Button(emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", style=muted, disabled=True)
        self.previous_button = discord.ui.Button(label="...", style=clickable, disabled=True)
        self.current_button = discord.ui.Button(label=self.current_page_label, style=muted, disabled=True)
        self.next_button = discord.ui.Button(label="..." if disabled else str(self.current_index + 2), style=clickable, disabled=disabled)
        self.last_button = discord.ui.Button(emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", style=muted, disabled=disabled)

        self.previous_button.callback = self.previous_page_callback
        self.next_button.callback = self.next_page_callback
        self.first_button.callback = self.first_page_callback
        self.last_button.callback = self.last_page_callback

        if not self.hide_quit_button:
            self.skip_button = discord.ui.Button(label="Go to Page", style=clickable, disabled=disabled)
            self.skip_button.callback = self.goto_page_callback
        else:
            self.skip_button = None

        if not self.hide_quit_button:
            self.quit_pagination_button = discord.ui.Button(label="Quit Pagination", style=discord.ButtonStyle.danger)
            self.quit_pagination_button.callback = self.quit_pagination_callback
        else:
            self.quit_pagination_button = None

    @property
    def current_page_label(self) -> str:
        return f"{self.current_index + 1} / {len(self.items)}"

    @property
    def previous_page_label(self) -> str:
        return f"{self.current_index}" if self.current_index > 0 else "..."

    @property
    def next_page_label(self) -> str:
        return f"{self.current_index + 2}" if self.current_index < len(self.items) - 1 else "..."

    @property
    def _is_first_page(self) -> bool:
        return self.current_index == 0

    @property
    def _is_last_page(self) -> bool:
        return self.current_index == len(self.items) - 1

    def _update_pagination_buttons(self) -> None:
        self.current_button.label = self.current_page_label
        self.previous_button.label = self.previous_page_label
        self.next_button.label = self.next_page_label

        self.first_button.disabled = self._is_first_page
        self.previous_button.disabled = self._is_first_page
        self.next_button.disabled = self._is_last_page
        self.last_button.disabled = self._is_last_page

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:
        if interaction.user.id == self.author.id:
            return True

        await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
        return False

    async def _change_page(self, interaction: discord.Interaction[Parrot], index: int) -> None:
        if index == self.current_index:
            return

        self.current_index = index
        await self.update_page(interaction)

    async def previous_page_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self._is_first_page:
            await self._change_page(interaction, self.current_index - 1)

    async def next_page_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self._is_last_page:
            await self._change_page(interaction, self.current_index + 1)

    async def first_page_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self._is_first_page:
            await self._change_page(interaction, 0)

    async def last_page_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self._is_last_page:
            await self._change_page(interaction, len(self.items) - 1)

    async def goto_page_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        modal = GotoPageModal(max_page=len(self.items), current_page=self.current_index + 1)
        modal.on_submit = self.goto_page_modal_callback(modal)

        await interaction.response.send_modal(modal)
        await modal.wait()

    def goto_page_modal_callback(self, modal: GotoPageModal):
        async def callback(interaction: discord.Interaction[Parrot]) -> None:
            value = modal.page_input.value

            if value is None:
                return

            try:
                page_number = int(value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid page number. Please enter a valid integer.", ephemeral=True)
                return

            if not 1 <= page_number <= len(self.items):
                await interaction.response.send_message(f"Page number must be between 1 and {len(self.items)}.", ephemeral=True)
                return

            await self._change_page(interaction, page_number - 1)

        return callback

    async def quit_pagination_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        assert isinstance(self, discord.ui.View | discord.ui.LayoutView), "PaginationMixin must be used with a View or LayoutView."

        self.stop()
        await interaction.message.delete() if interaction.message else None

    async def update_page(self, interaction: discord.Interaction[Parrot]) -> None:
        raise NotImplementedError

    async def append_page(self, item: PageT) -> None:
        assert isinstance(self, discord.ui.View | discord.ui.LayoutView), "PaginationMixin must be used with a View or LayoutView."

        self.items.append(item)
        self._update_pagination_buttons()

        if hasattr(self, "message") and self.message is not None:
            await self.message.edit(view=self)

    async def pop_page(self, index: int | None) -> None:
        assert isinstance(self, discord.ui.View | discord.ui.LayoutView), "PaginationMixin must be used with a View or LayoutView."

        if index is None:
            index = self.current_index

        if not 0 <= index < len(self.items):
            raise IndexError("Page index out of range.")

        self.items.pop(index)

        if self.current_index >= len(self.items):
            self.current_index = max(0, len(self.items) - 1)

        self._update_pagination_buttons()

        if hasattr(self, "message") and self.message is not None:
            await self.message.edit(view=self)

    async def start(self, ctx: commands.Context[Parrot], **kwargs) -> discord.Message:
        current_page = self.items[self.current_index]

        if isinstance(current_page, discord.Embed) and isinstance(self, discord.ui.View):
            self.message = await ctx.reply(embed=current_page, view=self, **kwargs)

        elif isinstance(self, discord.ui.LayoutView):
            self.message = await ctx.reply(view=self, **kwargs)

        else:
            error_message = f"{type(self).__name__} must be used with a discord.ui.View for embeds or a discord.ui.LayoutView for items."
            raise TypeError(error_message)

        return self.message


class PaginationView(PaginationMixin[discord.Embed], discord.ui.View):
    def __init__(
        self,
        *,
        author: discord.User | discord.Member,
        items: list[discord.Embed],
        hide_skip_button: bool = False,
        hide_quit_button: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.items = items
        self.author = author
        self.current_index = 0

        self.hide_quit_button = hide_quit_button
        self.hide_skip_button = hide_skip_button

        self._setup_pagination_buttons()

        for button in (
            self.first_button,
            self.previous_button,
            self.current_button,
            self.next_button,
            self.last_button,
        ):
            self.add_item(button)

        if not self.hide_skip_button and self.skip_button is not None:
            self.add_item(self.skip_button)

        if not self.hide_quit_button and self.quit_pagination_button is not None:
            self.add_item(self.quit_pagination_button)

    async def update_page(self, interaction: discord.Interaction[Parrot]) -> None:
        self._update_pagination_buttons()

        await interaction.response.edit_message(embed=self.items[self.current_index], view=self)


class PaginationLayout(PaginationMixin[list[discord.ui.Item]], discord.ui.LayoutView):
    def __init__(  # noqa: PLR0913
        self,
        author: discord.User | discord.Member,
        *,
        header: discord.ui.Item,
        footer: discord.ui.Item,
        items: list[list[discord.ui.Item]],
        hide_skip_button: bool = False,
        hide_quit_button: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        if not items:
            raise ValueError("Items list cannot be empty.")

        self.author = author
        self.hide_skip_button = hide_skip_button
        self.hide_quit_button = hide_quit_button

        self.header = header
        self.footer = footer
        self.items = items
        self.current_index = 0

        self._setup_pagination_buttons()

        self._pagination_buttons = discord.ui.ActionRow(
            self.first_button,
            self.previous_button,
            self.current_button,
            self.next_button,
            self.last_button,
        )

        self.container = discord.ui.Container()
        self._update_container()

        self.add_item(self.container)
        self.add_item(self._pagination_buttons)

        additional_buttons = []
        if not self.hide_skip_button and self.skip_button is not None:
            additional_buttons.append(self.skip_button)
        if not self.hide_quit_button and self.quit_pagination_button is not None:
            additional_buttons.append(self.quit_pagination_button)
        if additional_buttons:
            self.add_item(discord.ui.ActionRow(*additional_buttons))

    def _update_container(self) -> None:
        self.container.clear_items()
        self.container.add_item(self.header)
        self.container.add_item(discord.ui.Separator())

        for item in self.items[self.current_index]:
            self.container.add_item(item)

        self.container.add_item(discord.ui.Separator())
        self.container.add_item(self.footer)

    async def update_page(self, interaction: discord.Interaction[Parrot]) -> None:
        self._update_container()
        self._update_pagination_buttons()

        await interaction.response.edit_message(view=self)
