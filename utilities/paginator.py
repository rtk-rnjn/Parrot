# AUTHOR: https://github.com/davidetacchini/

from typing import List, Union, Optional, NamedTuple
from itertools import islice

import discord


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
        embed_url: str = None,
        check_other_ids: list = None,
    ):
        self.ctx = ctx
        self.per_page = per_page
        self.timeout = timeout
        self.title = title
        self.show_page_count = show_page_count
        self.check_other_ids = check_other_ids

        self.lines = []
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
        _pages = []
        for page in get_chunks(self.lines, self.per_page):
            _pages.append("".join(page))

        self.pages = Pages(_pages)

        if not self.pages.total > 1:
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
    def __init__(
        self,
        ctx,
        pages: Pages,
        embed,
        timeout,
        show_page_count,
        *,
        check_other_ids: list = None,
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
            self.children[0].disabled = False
            self.children[1].disabled = False

            self.children[2].disabled = False
            self.children[3].disabled = False

        elif self.pages.cur_page == 1:
            self.children[0].disabled = False
            self.children[1].disabled = False

            self.children[2].disabled = False
            self.children[3].disabled = False

        elif 1 < self.pages.cur_page < self.pages.total:
            for b in self.children:
                b.disabled = False

    def update_embed(self, page: Page):
        if self.show_page_count:
            try:
                self.embed.set_footer(text=f"Page {page.index} of {self.pages.total}")
            except Exception:
                pass
        if page:
            self.embed.description = page.content

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.check_other_ids:
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
    async def first(self, button: discord.ui.Button, interaction: discord.Interaction):
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
    async def previous(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
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
    async def _stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="next",
        emoji=discord.PartialEmoji(name="\N{BLACK RIGHT-POINTING TRIANGLE}"),
    )
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        page = self.pages.next_page
        self.update_embed(page)

        self.lock_bro()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="last",
        emoji=discord.PartialEmoji(name="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"),
    )
    async def last(self, button: discord.ui.Button, interaction: discord.Interaction):
        page = self.pages.last_page

        self.update_embed(page)
        self.lock_bro()
        await interaction.response.edit_message(embed=self.embed, view=self)


class PaginationView(discord.ui.View):
    current = 0

    def __init__(self, embed_list: list):
        super().__init__()
        self.embed_list = embed_list
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user == interaction.user:
            return True
        await interaction.response.send_message(
            f"Only **{self.user}** can interact. Run the command if you want to.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="First", style=discord.ButtonStyle.red, disabled=True)
    async def first(self, button: discord.ui.Button, interaction: discord.Interaction):
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

        await interaction.response.edit_message(
            embed=self.embed_list[self.current], view=self
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.green, disabled=True)
    async def previous(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.current = self.current - 1

        if len(self.embed_list) >= 1:  # if list consists of 2 pages, if,
            self._last.disabled = (
                False  # then `last` and `next` need not to be disabled
            )
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

        await interaction.response.edit_message(
            embed=self.embed_list[self.current], view=self
        )

    @discord.ui.button(style=discord.ButtonStyle.blurple)
    async def count(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green, disabled=False)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
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
        await interaction.response.edit_message(
            embed=self.embed_list[self.current], view=self
        )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.red, disabled=False)
    async def _last(self, button: discord.ui.Button, interaction: discord.Interaction):
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

        await interaction.response.edit_message(
            embed=self.embed_list[self.current], view=self
        )

    async def start(self, ctx):
        self.message = await ctx.send(embed=self.embed_list[0], view=self)
        self.user = ctx.author
        return self.message
