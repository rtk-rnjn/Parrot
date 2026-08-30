from __future__ import annotations

import discord
from discord.ext import commands


class PaginationView[PageT: discord.Embed | str](discord.ui.View):
    message: discord.Message
    current: int = 0

    ctx: commands.Context[commands.Bot]

    def __init__(self, pages: list[PageT]) -> None:
        super().__init__(timeout=30)

        self._pages = pages
        self.count.label = f"Page {self.current + 1}/{len(self._pages)}"

        self._str_prefix = ""
        self._str_suffix = ""

    async def interaction_check(self, interaction: discord.Interaction[commands.Bot]) -> bool:
        author = self.ctx.author
        if author == interaction.user:
            return True
        await interaction.response.send_message(f"Only **{author}** can interact. Run the command if you want to.", ephemeral=True)
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
    async def first(self, interaction: discord.Interaction[commands.Bot], button: discord.ui.Button):
        self.current = 0
        self.count.label = f"Page {self.current + 1}/{len(self._pages)}"

        self.previous.disabled = True
        button.disabled = True

        if len(self._pages) >= 1:
            self.next.disabled = False
            self._last.disabled = False
        else:
            self.next.disabled = True
            self._last.disabled = True

        current_entity = self._pages[self.current]
        await self.edit(interaction, current_entity)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.green, disabled=True)
    async def previous(self, interaction: discord.Interaction[commands.Bot], button: discord.ui.Button):
        self.current = self.current - 1

        if len(self._pages) >= 1:  # if list consists of 2 pages, if,
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

        self.count.label = f"Page {self.current + 1}/{len(self._pages)}"

        current_entity = self._pages[self.current]
        await self.edit(interaction, current_entity)

    @discord.ui.button(style=discord.ButtonStyle.blurple)
    async def count(self, interaction: discord.Interaction[commands.Bot], button: discord.ui.Button):
        assert interaction.message is not None

        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green, disabled=False)
    async def next(self, interaction: discord.Interaction[commands.Bot], button: discord.ui.Button):
        self.current += 1

        if self.current >= len(self._pages) - 1:
            self.current = len(self._pages) - 1
            button.disabled = True
            self._last.disabled = True

        if len(self._pages) >= 1:
            self.first.disabled = False
            self.previous.disabled = False
        else:
            self.previous.disabled = True
            self.first.disabled = True

        self.count.label = f"Page {self.current + 1}/{len(self._pages)}"

        current_entity = self._pages[self.current]
        await self.edit(interaction, current_entity)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.red, disabled=False)
    async def _last(self, interaction: discord.Interaction[commands.Bot], button: discord.ui.Button):
        self.current = len(self._pages) - 1
        self.count.label = f"Page {self.current + 1}/{len(self._pages)}"

        button.disabled = True
        self.next.disabled = True

        if len(self._pages) >= 1:
            self.first.disabled = False
            self.previous.disabled = False
        else:
            self.first.disabled = True
            self.previous.disabled = True

        current_entity = self._pages[self.current]
        await self.edit(interaction, current_entity)

    async def edit(self, interaction: discord.Interaction[commands.Bot], current_entity: PageT) -> PageT:
        func = interaction.response.edit_message

        if isinstance(current_entity, discord.Embed):
            await func(embed=current_entity, view=self)
        else:
            await func(content=f"{self._str_prefix}{current_entity}{self._str_suffix}", view=self)
        return current_entity

    async def start(self, ctx: commands.Context):
        self.ctx = ctx
        if not self._pages:
            self.message = await ctx.reply("Loading...")
            return

        if isinstance(self._pages[0], discord.Embed):
            self.message = await ctx.reply(embed=self._pages[0], view=self)
        else:
            self.message = await ctx.reply(f"{self._str_prefix}{self._pages[0]}{self._str_suffix}", view=self)

        return self.message

    async def paginate(self, ctx: commands.Context):
        await self.start(ctx)

    async def add_item_to_embed_list(self, item: PageT) -> PageT:
        self._pages.append(item)
        if hasattr(self, "message"):
            self.count.label = f"Page {self.current + 1}/{len(self._pages)}"
            if len(self._pages) >= 1 and self.current < len(self._pages) - 1:
                self._last.disabled = False
                self.next.disabled = False
        return item

    async def _update_message(self) -> None:
        currnet_entity = self._pages[self.current]

        if isinstance(currnet_entity, discord.Embed):
            await self.message.edit(embed=currnet_entity, view=self)
        else:
            await self.message.edit(content=f"{self._str_prefix}{currnet_entity}{self._str_suffix}", view=self)

    @classmethod
    async def paginate_embed(cls, ctx: commands.Context, embed_list: list[PageT]):
        paginator = cls(embed_list)
        return await paginator.start(ctx)

    async def on_error(self, interaction: discord.Interaction[commands.Bot], exception: Exception, item: discord.ui.Item, /) -> None:
        bot = self.ctx.bot if isinstance(self.ctx, commands.Context) else self.ctx.client

        bot.dispatch("error", interaction, exception)
        if await bot.is_owner(interaction.user):
            await interaction.response.send_message(f"```py\n{str(exception)[:1980]}\n```", ephemeral=True)
