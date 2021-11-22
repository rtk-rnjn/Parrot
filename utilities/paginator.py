#AUTHOR: https://github.com/davidetacchini/

import asyncio
from typing import List, Union, Optional, NamedTuple
from contextlib import suppress
from itertools import islice

import discord


def get_chunks(iterable, size):
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, size)), ())


class Paginator:

    __slots__ = (
        "pages",
        "timeout",
        "compact",
        "has_input",
        "has_lock",
        "_ctx",
        "_bot",
        "_loop",
        "_message",
        "_current",
        "_previous",
        "_end",
        "_reactions",
        "__tasks",
        "__is_running",
        "__is_locked",
        "__mutex",
    )

    def __init__(self,
                 *,
                 pages: Optional[Union[List[discord.Embed],
                                       discord.Embed]] = None,
                 compact: bool = False,
                 timeout: float = 90.0,
                 has_input: bool = True,
                 has_lock: bool = False):
        self.pages = pages
        self.compact = compact
        self.timeout = timeout
        self.has_input = has_input
        self.has_lock = has_lock

        self._ctx = None
        self._bot = None
        self._loop = None
        self._message = None

        self._current = 0
        self._previous = 0
        self._end = 0
        self._reactions = {
            "⏮": 0.0,
            "◀": -1,
            "⏹️": "stop",
            "▶": +1,
            "⏭": None,
        }

        self.__tasks = []
        self.__is_running = True
        self.__is_locked = True
        self.__mutex = asyncio.Lock()

        if self.has_input is True:
            self._reactions["🔢"] = "input"

        if self.has_lock is True:
            self._reactions["🔒"] = "lock"

        if self.pages is not None:
            if len(self.pages) == 2:
                self.compact = True
                self.has_input = False

        if self.compact is True:
            keys = ("⏮", "⏭")
            for key in keys:
                del self._reactions[key]

    def go_to_page(self, number):
        if number > int(self._end):
            page = int(self._end)
        else:
            page = number - 1
        self._current = page

    async def get_input(self):
        to_delete = []
        message = await self._ctx.send("What page do you want to go to?")
        to_delete.append(message)

        def check(m):
            if self.__is_locked:
                if m.author.id != self._ctx.author.id:
                    return False
            if m.channel.id != self._ctx.channel.id:
                return False
            if not m.content.isdigit():
                return False
            return True

        try:
            message = await self._bot.wait_for("message",
                                               check=check,
                                               timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await self._ctx.send(
                f"{self._ctx.author.mention} You took too long to enter a number."
            ))
            await asyncio.sleep(5)
        else:
            to_delete.append(message)
            self.go_to_page(int(message.content))

        with suppress(Exception):
            await self._ctx.channel.delete_messages(to_delete)

    async def lock_or_unlock(self, user_id):
        # only the author can (un)lock the session
        if self._ctx.author.id != user_id:
            return
        self.__is_locked = not self.__is_locked
        if self.__is_locked:
            await self._ctx.send(
                "Session locked. Only you can interact with it.")
        else:
            await self._ctx.send(
                "Session unlocked. Everyone can interact with it.")

    async def controller(self, reaction, user_id):
        if self.__mutex.locked():
            return
        async with self.__mutex:
            if reaction == "stop":
                await self.stop()
            elif reaction == "input":
                await self.get_input()
            elif reaction == "lock":
                await self.lock_or_unlock(user_id)
            elif isinstance(reaction, int):
                self._current += reaction
                if self._current < 0 or self._current > self._end:
                    self._current -= reaction
            else:
                self._current = int(reaction)

    def check(self, payload):
        if self.__is_locked:
            if payload.user_id != self._ctx.author.id:
                return False
        if payload.message_id != self._message.id:
            return False
        return str(payload.emoji) in self._reactions

    async def add_reactions(self):
        for reaction in self._reactions:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self._message.add_reaction(reaction)

    async def paginator(self):
        with suppress(discord.HTTPException, discord.Forbidden, IndexError):
            self._message = await self._ctx.send(embed=self.pages[0])

        if len(self.pages) > 1:
            self.__tasks.append(self._loop.create_task(self.add_reactions()))

        while self.__is_running:
            with suppress(Exception):
                tasks = [
                    asyncio.ensure_future(
                        self._bot.wait_for("raw_reaction_add",
                                           check=self.check)),
                    asyncio.ensure_future(
                        self._bot.wait_for("raw_reaction_remove",
                                           check=self.check)),
                ]

                done, pending = await asyncio.wait(
                    tasks,
                    timeout=self.timeout,
                    return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    # clear the reactions once the timeout has elapsed
                    return await self.stop(timed_out=True)

                payload = done.pop().result()
                reaction = self._reactions.get(str(payload.emoji))

                self._previous = self._current
                await self.controller(reaction, payload.user_id)

                if self._previous == self._current:
                    continue

                with suppress(Exception):
                    await self._message.edit(embed=self.pages[self._current])

    async def stop(self, *, timed_out=False):
        with suppress(discord.Forbidden, discord.HTTPException):
            if timed_out:
                await self._message.clear_reactions()
            else:
                await self._message.delete()

        with suppress(Exception):
            self.__is_running = False
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

    async def start(self, ctx):

        self._ctx = ctx
        self._bot = ctx.bot
        self._loop = ctx.bot.loop

        if isinstance(self.pages, discord.Embed):
            return await self._ctx.send(embed=self.pages)

        if not isinstance(self.pages, (list, discord.Embed)):
            raise TypeError("Can't paginate an instance of <class '%s'>." %
                            self.pages.__class__.__name__)

        if len(self.pages) == 0:
            raise RuntimeError("Can't paginate an empty list.")

        self._end = float(len(self.pages) - 1)
        if self.compact is False:
            self._reactions["⏭"] = self._end
        self.__tasks.append(self._loop.create_task(self.paginator()))


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
    def __init__(self,
                 ctx,
                 *,
                 per_page=10,
                 timeout=60.0,
                 title=None,
                 show_page_count=True):
        self.ctx = ctx
        self.per_page = per_page
        self.timeout = timeout
        self.title = title
        self.show_page_count = show_page_count

        self.lines = []
        self.pages = None

    def add_line(self, line: str, sep="\n"):
        self.lines.append(f"{line}{sep}")

    @property
    def embed(self):
        page = self.pages.current_page

        e = discord.Embed(color=self.ctx.bot.color)
        if self.title:
            e.title = self.title

        e.description = page.content

        if self.show_page_count:
            e.set_footer(text=f"Page {page.index} of {self.pages.total}")

        return e

    async def start(self):
        _pages = []
        for page in get_chunks(self.lines, self.per_page):
            _pages.append("".join(page))

        self.pages = Pages(_pages)

        if not self.pages.total > 1:
            return await self.ctx.send(embed=self.embed)

        view = PaginatorView(self.ctx,
                             pages=self.pages,
                             embed=self.embed,
                             timeout=self.timeout,
                             show_page_count=self.show_page_count)
        view.message = await self.ctx.send(embed=self.embed, view=view)


class PaginatorView(discord.ui.View):
    def __init__(self, ctx, pages: Pages, embed, timeout, show_page_count):

        super().__init__(timeout=timeout)

        self.ctx = ctx
        self.pages = pages
        self.embed = embed
        self.show_page_count = show_page_count

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
            self.embed.set_footer(
                text=f"Page {page.index} of {self.pages.total}")

        self.embed.description = page.content

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Sorry, you can't use this interaction as it is not started by you.",
                ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:

        for b in self.children:
            b.style, b.disabled = discord.ButtonStyle.grey, True

        await self.message.edit(view=self)

    @discord.ui.button(style=discord.ButtonStyle.green,
                       custom_id="first",
                       emoji=discord.PartialEmoji(
                           name="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}"))
    async def first(self, button: discord.ui.Button,
                    interaction: discord.Interaction):
        page = self.pages.first_page

        self.update_embed(page)
        self.lock_bro()
        await interaction.message.edit(embed=self.embed, view=self)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="previous",
        emoji=discord.PartialEmoji(name="\N{BLACK LEFT-POINTING TRIANGLE}"))
    async def previous(self, button: discord.ui.Button,
                       interaction: discord.Interaction):
        page = self.pages.previous_page
        self.update_embed(page)
        self.lock_bro()
        await interaction.message.edit(embed=self.embed, view=self)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="stop",
        emoji=discord.PartialEmoji(name="\N{BLACK SQUARE FOR STOP}"))
    async def stop(self, button: discord.ui.Button,
                   interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        custom_id="next",
        emoji=discord.PartialEmoji(name="\N{BLACK RIGHT-POINTING TRIANGLE}"))
    async def next(self, button: discord.ui.Button,
                   interaction: discord.Interaction):
        page = self.pages.next_page
        self.update_embed(page)

        self.lock_bro()
        await interaction.message.edit(embed=self.embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.green,
                       custom_id="last",
                       emoji=discord.PartialEmoji(
                           name="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"))
    async def last(self, button: discord.ui.Button,
                   interaction: discord.Interaction):
        page = self.pages.last_page

        self.update_embed(page)
        self.lock_bro()
        await interaction.message.edit(embed=self.embed, view=self)



class PaginationView(discord.ui.View):
    current = 0 

    def __init__(self, embed_list):
        super().__init__()
        self.embed_list = embed_list
        if len(embed_list) == 1:
            self.next.style = discord.ButtonStyle.green
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if self.user == interaction.user:
            return True
        await interaction.response.send_message(f'Only {self.user} can interact. Run the command if you want to.', ephemeral=True)
        return False

    @discord.ui.button(label="First",
                       style=discord.ButtonStyle.green,
                )
    async def first(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current = 0
        button.style = discord.ButtonStyle.green
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"
        await interaction.response.edit_message(embed=self.embed_list[self.current], view=self)
    
    @discord.ui.button(label="Previous",
                       style=discord.ButtonStyle.green,
                )
    async def previous(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current -= 1
        self.next.style = discord.ButtonStyle.green
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"
        if self.current == 0:
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], view=self)
        else:
            await interaction.response.edit_message(
                embed=self.embed_list[self.current], view=self)

    @discord.ui.button(style=discord.ButtonStyle.blurple)
    async def count(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current += 1
        self.previous.style = discord.ButtonStyle.green
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"
        await interaction.response.edit_message(embed=self.embed_list[self.current], view=self)

    @discord.ui.button(label='Last', style=discord.ButtonStyle.green)
    async def _last(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current = len(self.embed_list) - 1
        self.count.label = f"Page {self.current + 1}/{len(self.embed_list)}"
        button.style = discord.ButtonStyle.green
        await interaction.response.edit_message(embed=self.embed_list[self.current], view=self)

    async def start(self, ctx):
        self.message = await ctx.reply(embed=self.embed_list[0], view=self)
        self.user = ctx.author
        return self.message
