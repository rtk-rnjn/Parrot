# AUTHOR: https://github.com/davidetacchini/

from itertools import islice
from typing import Awaitable, Callable, List, NamedTuple, Optional, TypeVar, Union

import discord
from core import Context

PageT = TypeVar("PageT", bound=Union[str, int, discord.File, discord.Embed])
Callback = Callable[[discord.Interaction, discord.ui.Button, PageT], Awaitable[None]]


def get_chunks(iterable, size):
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, size)), ())


class Page(NamedTuple):
    index: int
    content: str


class Pages:
    def __init__(self, pages: list):
        self.pages = pages
        self.cur_page = 1

    @property
    def current_page(self) -> Page:
        return Page(self.cur_page, self.pages[self.cur_page - 1])

    @property
    def next_page(self) -> Optional[Page]:
        if self.cur_page == self.total:
            return None

        self.cur_page += 1
        return self.current_page

    @property
    def previous_page(self) -> Optional[Page]:
        if self.cur_page == 1:
            return None

        self.cur_page -= 1
        return self.current_page

    @property
    def first_page(self) -> Page:
        self.cur_page = 1
        return self.current_page

    @property
    def last_page(self) -> Page:
        self.cur_page = self.total
        return self.current_page

    @property
    def total(self):
        return len(self.pages)


class ParrotPaginator:
    def __init__(
        self,
        ctx,
        *,
        per_page=10,
        timeout=60.0,
        title=None,
        show_page_count=True,
        embed_url: Optional[str] = None,
        check_other_ids: Optional[list] = None,
    ):
        self.ctx = ctx
        self.per_page = per_page
        self.timeout = timeout
        self.title = title
        self.show_page_count = show_page_count
        self.check_other_ids = check_other_ids

        self.lines: List[str] = []
        self.pages = None
        self.embed_url = embed_url

    def add_line(self, line: str, sep="\n"):
        self.lines.append(f"{line}{sep}")

    @property
    def embed(self):
        page = self.pages.current_page

        e = discord.Embed(color=self.ctx.bot.color, timestamp=discord.utils.utcnow())
        if self.title:
            e.title = self.title

        e.description = page.content
        e.set_footer(text=f"Requester: {self.ctx.author}")

        if self.show_page_count:
            e.set_footer(text=f"Page {page.index} of {self.pages.total}")

        if self.embed_url:
            e.set_thumbnail(url=self.embed_url)

        return e

    async def start(self, *, start: bool = True):
        _pages = ["".join(page) for page in get_chunks(self.lines, self.per_page)]
        self.pages = Pages(_pages)
        if self.pages.total <= 1:
            return await self.ctx.send(embed=self.embed)
        view = PaginatorView(
            self.ctx,
            pages=self.pages,
            embed=self.embed,
            timeout=self.timeout,
            check_other_ids=self.check_other_ids,
            show_page_count=self.show_page_count,
        )

        self.view = view
        if start:
            view.message = await self.ctx.send(embed=self.embed, view=view)


class PaginatorView(discord.ui.View):
    message: discord.Message

    def __init__(
        self,
        ctx: Context,
        pages: Pages,
        embed: discord.Embed,
        timeout,
        show_page_count,
        *,
        check_other_ids: Optional[list] = None,
    ):
        super().__init__(timeout=timeout)

        self.ctx = ctx
        self.pages = pages
        self.embed = embed
        self.show_page_count = show_page_count
        self.check_other_ids = check_other_ids
        if self.pages.cur_page == 1:

            self.children[0].disabled = False
            self.children[1].disabled = False

    def lock_bro(self):
        if self.pages.cur_page == self.pages.total:
            self._extracted_from_lock_bro_4()
        elif self.pages.cur_page == 1:
            self._extracted_from_lock_bro_4()
        elif 1 < self.pages.cur_page < self.pages.total:
            for b in self.children:
                if isinstance(b, discord.ui.Button):
                    b.disabled = False

    # TODO Rename this here and in `lock_bro`
    def _extracted_from_lock_bro_4(self):
        self.children[0].disabled = False  # type: ignore
        self.children[1].disabled = False  # type: ignore
        self.children[2].disabled = False  # type: ignore
        self.children[3].disabled = False  # type: ignore

    def update_embed(self, page: Page):
        if self.show_page_count:
            try:
                self.embed.set_footer(text=f"Page {page.index} of {self.pages.total}")
            except Exception:
                pass
        if page:
            self.embed.description = page.content

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.check_other_ids and interaction.user.id in self.check_other_ids:
            return True
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Sorry, you can't use this interaction as it is not started by you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="first",
        emoji=discord.PartialEmoji(name="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}"),
    )
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        page = self.pages.first_page

        self.update_embed(page)
        self.lock_bro()
        await interaction.response.edit_message(
            embed=self.embed,
            view=self,
        )

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="previous",
        emoji=discord.PartialEmoji(name="\N{BLACK LEFT-POINTING TRIANGLE}"),
    )
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        page = self.pages.previous_page
        self.update_embed(page)
        self.lock_bro()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="stop",
        emoji=discord.PartialEmoji(name="\N{BLACK SQUARE FOR STOP}"),
        disabled=True,
    )
    async def _stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="next",
        emoji=discord.PartialEmoji(name="\N{BLACK RIGHT-POINTING TRIANGLE}"),
    )
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        page = self.pages.next_page
        self.update_embed(page)

        self.lock_bro()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="last",
        emoji=discord.PartialEmoji(name="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"),
    )
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        page = self.pages.last_page

        self.update_embed(page)
        self.lock_bro()
        await interaction.response.edit_message(embed=self.embed, view=self)


class PaginationView(discord.ui.View):
    message: discord.Message
    current: int = 0

    def __init__(
        self,
        embed_list: Optional[List[Union[str, discord.File, discord.Embed]]] = None,
        *,
        first_function: Optional[Callback] = None,
        next_function: Optional[Callback] = None,
        previous_function: Optional[Callback] = None,
        last_function: Optional[Callback] = None,
    ) -> None:
        super().__init__(timeout=30)
        if embed_list is None:
            embed_list = []

        self.embed_list = embed_list
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

        self.first_function = first_function
        self.next_function = next_function
        self.previous_function = previous_function
        self.last_function = last_function

        self._str_prefix = ""
        self._str_suffix = ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.ctx.author == interaction.user:
            return True
        await interaction.response.send_message(
            f"Only **{self.ctx.author}** can interact. Run the command if you want to.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self):
        self.stop()
        assert self.message is not None

        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
                button.style = discord.ButtonStyle.grey
        await self.message.edit(view=self)

    @discord.ui.button(label="First", style=discord.ButtonStyle.red, disabled=True)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = 0
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

        self.previous.disabled = True
        button.disabled = True

        if len(self.embed_list) >= 1:
            self.next.disabled = False
            self._last.disabled = False
        else:
            self.next.disabled = True
            self._last.disabled = True

        if self.first_function:
            await discord.utils.maybe_coroutine(self.first_function, interaction, button, self.embed_list)
            return

        if isinstance(self.embed_list[self.current], discord.Embed):
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], content=None, attachments=[], view=self  # type: ignore
            )
        elif isinstance(self.embed_list[self.current], discord.File):
            await interaction.response.edit_message(
                attachments=[self.embed_list[self.current]], content=None, embed=None, view=self  # type: ignore
            )
        else:
            await interaction.response.edit_message(
                content=f"{self._str_prefix}{self.embed_list[self.current]}{self._str_suffix}",
                embed=None,
                attachments=[],
                view=self,
            )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.green, disabled=True)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = self.current - 1

        if len(self.embed_list) >= 1:  # if list consists of 2 pages, if,
            self._last.disabled = False  # then `last` and `next` need not to be disabled
            self.next.disabled = False
        else:
            self._last.disabled = True  # else it should be disabled
            self.next.disabled = True  # because why not

        if self.current <= 0:  # if we are on first page,
            self.current = 0  # we disabled `first` and `previous`
            self.first.disabled = True
            button.disabled = True
        else:
            self.first.disabled = False
            button.disabled = False

        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

        if self.previous_function:
            await discord.utils.maybe_coroutine(self.previous_function, interaction, button, self.embed_list)
            return

        if isinstance(self.embed_list[self.current], discord.Embed):
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], content=None, attachments=[], view=self  # type: ignore
            )
        elif isinstance(self.embed_list[self.current], discord.File):
            await interaction.response.edit_message(
                attachments=[self.embed_list[self.current]], content=None, embed=None, view=self  # type: ignore
            )
        else:
            await interaction.response.edit_message(
                content=f"{self._str_prefix}{self.embed_list[self.current]}{self._str_suffix}",
                embed=None,
                attachments=[],
                view=self,
            )

    @discord.ui.button(style=discord.ButtonStyle.blurple)
    async def count(self, interaction: discord.Interaction, button: discord.ui.Button):
        assert interaction.message is not None

        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green, disabled=False)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1

        if self.current >= len(self.embed_list) - 1:
            self.current = len(self.embed_list) - 1
            button.disabled = True
            self._last.disabled = True

        if len(self.embed_list) >= 1:
            self.first.disabled = False
            self.previous.disabled = False
        else:
            self.previous.disabled = True
            self.first.disabled = True

        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

        if self.next_function:
            await discord.utils.maybe_coroutine(self.next_function, interaction, button, self.embed_list)
            return

        if isinstance(self.embed_list[self.current], discord.Embed):
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], content=None, attachments=[], view=self  # type: ignore
            )
        elif isinstance(self.embed_list[self.current], discord.File):
            await interaction.response.edit_message(
                attachments=[self.embed_list[self.current]], content=None, embed=None, view=self  # type: ignore
            )
        else:
            await interaction.response.edit_message(
                content=f"{self._str_prefix}{self.embed_list[self.current]}{self._str_suffix}",
                embed=None,
                attachments=[],
                view=self,
            )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.red, disabled=False)
    async def _last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = len(self.embed_list) - 1
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

        button.disabled = True
        self.next.disabled = True

        if len(self.embed_list) >= 1:
            self.first.disabled = False
            self.previous.disabled = False
        else:
            self.first.disabled = True
            self.previous.disabled = True

        if self.last_function:
            await discord.utils.maybe_coroutine(self.last_function, interaction, button, self.embed_list)
            return

        if isinstance(self.embed_list[self.current], discord.Embed):
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], content=None, attachments=[], view=self  # type: ignore
            )
        elif isinstance(self.embed_list[self.current], discord.File):
            await interaction.response.edit_message(
                attachments=[self.embed_list[self.current]], content=None, embed=None, view=self  # type: ignore
            )
        else:
            await interaction.response.edit_message(
                content=f"{self._str_prefix}{self.embed_list[self.current]}{self._str_suffix}",
                embed=None,
                attachments=[],
                view=self,
            )

    async def start(self, ctx: Context):
        self.ctx = ctx
        if not self.embed_list:
            self.message = await ctx.send("Loading...")  # type: ignore
            return

        if isinstance(self.embed_list[0], discord.Embed):
            self.message = await ctx.send(embed=self.embed_list[0], view=self)  # type: ignore
        elif isinstance(self.embed_list[0], discord.File):
            self.message = await ctx.send(file=self.embed_list[0], view=self)  # type: ignore
        else:
            self.message = await ctx.send(f"{self._str_prefix}{self.embed_list[0]}{self._str_suffix}", view=self)  # type: ignore

        return self.message

    async def paginate(self, ctx: Context):
        self.ctx = ctx
        await self.start(ctx)

    async def add_item_to_embed_list(self, item: Union[str, discord.Embed, discord.File]):
        self.embed_list.append(item)
        if hasattr(self, "message"):
            self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"
            if len(self.embed_list) >= 1 and self.current < len(self.embed_list) - 1:
                self._last.disabled = False
                self.next.disabled = False

    async def _update_message(self) -> None:
        if isinstance(self.embed_list[self.current], discord.Embed):
            await self.message.edit(
                embed=self.embed_list[self.current], content=None, attachments=[], view=self  # type: ignore
            )
        elif isinstance(self.embed_list[self.current], discord.File):
            await self.message.edit(
                attachments=[self.embed_list[self.current]], content=None, embed=None, view=self  # type: ignore
            )
        else:
            await self.message.edit(
                content=f"{self._str_prefix}{self.embed_list[self.current]}{self._str_suffix}",
                embed=None,
                attachments=[],
                view=self,
            )
