# https://github.com/quotientbot/Quotient-Bot/blob/main/src/cogs/utility/__init__.py#L195-L205
# commit hash: 177ef9f9ee91970a21b28d9c4124c023c34887f7

from __future__ import annotations

import re
import typing as T
from contextlib import suppress

from PIL import ImageColor

import discord
from core import Context
from discord.ext import commands
from utilities.config import SUPPORT_SERVER


class EmbedSend(discord.ui.Button):
    view: EmbedBuilder

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        super().__init__(
            label="Send to #{0}".format(channel.name), style=discord.ButtonStyle.green
        )

    async def callback(self, interaction: discord.Interaction) -> T.Any:
        try:
            m: T.Optional[discord.Message] = await self.channel.send(
                embed=self.view.embed
            )

        except Exception as e:
            await interaction.response.send_message(
                f"An error occured: {e}", ephemeral=True
            )

        else:
            await interaction.response.send_message(
                f"\N{WHITE HEAVY CHECK MARK} | Embed was sent to {self.channel.mention} ([Jump URL](<{m.jump_url}>))",
                ephemeral=True,
            )
            await self.view.on_timeout()


class EmbedCancel(discord.ui.Button):
    view: EmbedBuilder

    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction) -> T.Any:
        await interaction.response.send_message(
            "\N{CROSS MARK} | Embed sending cancelled.", ephemeral=True
        )
        await self.view.on_timeout()


class ParrotColor:
    @classmethod
    async def convert(cls, ctx: Context, arg: str):
        with suppress(AttributeError):
            match = re.match(r"\(?(\d+),?\s*(\d+),?\s*(\d+)\)?", arg)
            check = all(0 <= int(x) <= 255 for x in match.groups())
        if match and check:
            return discord.Color.from_rgb([int(i) for i in match.groups()])
        _converter = commands.ColorConverter()
        result = None
        try:
            result = await _converter.convert(ctx, arg)
        except commands.BadColorArgument:
            with suppress(ValueError):
                color = ImageColor.getrgb(arg)
                result = discord.Color.from_rgb(*color)
        return result or await ctx.error(f"`{arg}` isn't a valid color.", 4)


class Content(discord.ui.Modal, title="Edit Message Content"):
    _content: discord.ui.TextInput = discord.ui.TextInput(
        label="Content",
        placeholder="This text will be displayed over the embed",
        required=False,
        max_length=2000,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()


class ParrotView(discord.ui.View):
    message: discord.Message
    custom_id = None

    def __init__(self, ctx: Context, *, timeout: T.Optional[float] = 30):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.bot = ctx.bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Sorry, you can't use this interaction as it is not started by you.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if hasattr(self, "message"):
            for b in self.children:
                if (
                    isinstance(b, discord.ui.Button)
                    and b.style != discord.ButtonStyle.link
                ):
                    b.style, b.disabled = discord.ButtonStyle.grey, True
                elif isinstance(b, discord.ui.Select):
                    b.disabled = True
            with suppress(discord.HTTPException):
                await self.message.edit(view=self)
                return

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item
    ) -> None:
        print("Parrot View Error:", error)
        self.ctx.bot.dispatch("command_error", self.ctx, error)

    @staticmethod
    def tricky_invite_button():  # yes lmao
        return discord.ui.Button(emoji="\N{INFORMATION SOURCE}", url=SUPPORT_SERVER)


class ParrotInput(discord.ui.Modal):
    def __init__(self, title: str):
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        with suppress(discord.NotFound):
            await interaction.response.defer()


class EmbedOptions(discord.ui.Select):
    view: EmbedBuilder

    def __init__(self, ctx: Context):
        self.ctx = ctx
        super().__init__(
            placeholder="Select an option to design the message.",
            options=[
                discord.SelectOption(
                    label="Edit Message (Title, Description, Footer)",
                    value="main",
                    description="Edit your embed title, description, and footer.",
                ),
                discord.SelectOption(
                    label="Edit Thumbnail Image",
                    description="Small Image on the right side of embed",
                    value="thumb",
                ),
                discord.SelectOption(
                    label="Edit Main Image",
                    description="Edit your embed Image",
                    value="image",
                ),
                discord.SelectOption(
                    label="Edit Footer Icon",
                    description="Small icon near footer message",
                    value="footer_icon",
                ),
                discord.SelectOption(
                    label="Edit Embed Color",
                    description="Change the color of the embed",
                    value="color",
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        # sourcery skip: low-code-quality

        assert self.view is not None

        if (selected := self.values[0]) == "content":
            modal = Content()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.view.content = modal._content.value or ""

            await self.view.refresh_view()

        elif selected == "main":
            modal = ParrotInput("Set Embed Message")
            modal.add_item(
                discord.ui.TextInput(
                    label="Title",
                    placeholder="Enter text for title of embed here...",
                    max_length=256,
                    required=False,
                    style=discord.TextStyle.short,
                    default=self.view.embed.title,
                )
            )
            modal.add_item(
                discord.ui.TextInput(
                    label="Description",
                    placeholder="Enter text for description of embed here...",
                    max_length=4000,
                    required=False,
                    style=discord.TextStyle.long,
                    default=self.view.embed.description,
                )
            )
            modal.add_item(
                discord.ui.TextInput(
                    label="Footer Text",
                    placeholder="Enter text for footer of embed here...",
                    style=discord.TextStyle.long,
                    max_length=2048,
                    required=False,
                    default=self.view.embed.footer.text,
                )
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            t, d, f = (
                str(modal.children[0]),
                str(modal.children[1]),
                str(modal.children[2]),
            )

            self.view.embed.title = t or None
            self.view.embed.description = d or None
            self.view.embed.set_footer(
                text=f or None, icon_url=self.view.embed.footer.icon_url
            )

            await self.view.refresh_view()

        elif selected == "thumb":
            modal = ParrotInput("Edit Thumbnail Image")
            modal.add_item(
                discord.ui.TextInput(
                    label="Enter Image URL (Optional)",
                    placeholder="Leave empty to remove Image.",
                    required=False,
                    default=getattr(self.view.embed.thumbnail, "url", None),
                )
            )
            await interaction.response.send_modal(modal)
            await modal.wait()
            url = str(modal.children[0]) or None

            if not url or not url.startswith("https"):
                self.view.embed.set_thumbnail(url=None)

            else:
                self.view.embed.set_thumbnail(url=url)
            await self.view.refresh_view()

        elif selected == "image":
            modal = ParrotInput("Edit Main Image")
            modal.add_item(
                discord.ui.TextInput(
                    label="Enter Image URL (Optional)",
                    placeholder="Leave empty to remove Image.",
                    required=False,
                    default=getattr(self.view.embed.image, "url", None),
                )
            )
            await interaction.response.send_modal(modal)
            await modal.wait()
            url = str(modal.children[0]) or None

            if not url or not url.startswith("https"):
                self.view.embed.set_image(url=None)

            else:
                self.view.embed.set_image(url=url)

            await self.view.refresh_view()

        elif selected == "footer_icon":
            modal = ParrotInput("Edit Footer Icon")
            modal.add_item(
                discord.ui.TextInput(
                    label="Enter Image URL (Optional)",
                    placeholder="Leave empty to remove Icon.",
                    required=False,
                    default=getattr(self.view.embed.footer, "icon_url", None),
                )
            )
            await interaction.response.send_modal(modal)
            await modal.wait()
            url = str(modal.children[0]) or None

            if not url or not url.startswith("https"):
                self.view.embed.set_footer(
                    icon_url=None, text=self.view.embed.footer.text
                )

            else:
                self.view.embed.set_footer(
                    icon_url=url, text=self.view.embed.footer.text
                )

            await self.view.refresh_view()

        elif selected == "color":
            modal = ParrotInput("Set Embed Color")
            modal.add_item(
                discord.ui.TextInput(
                    label="Enter a valid Color",
                    placeholder="Examples: red, yellow, #00ffb3, etc.",
                    required=False,
                    max_length=7,
                )
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            color = 0x36393E

            with suppress(ValueError):
                if c := str(modal.children[0]):
                    color = int(
                        str(await ParrotColor.convert(self.ctx, c)).replace("#", ""), 16
                    )

            self.view.embed.color = color

            await self.view.refresh_view()


class EmbedBuilder(ParrotView):
    def __init__(self, ctx: Context, **kwargs: T.Any):
        super().__init__(ctx, timeout=100)

        self.ctx = ctx
        self.add_item(EmbedOptions(self.ctx))

        for _ in kwargs.get(
            "items", []
        ):  # to add extra buttons and handle this view externally
            self.add_item(_)

    @property
    def formatted(self):
        return self.embed.to_dict()

    async def refresh_view(self, to_del: T.Optional[discord.Message] = None):
        if to_del is not None:
            await self.ctx.safe_delete(to_del)

        with suppress(discord.HTTPException):
            self.message = await self.message.edit(
                content=self.content, embed=self.embed, view=self
            )

    async def rendor(self, **kwargs: T.Any):
        self.message: discord.Message = await self.ctx.send(
            kwargs.get("content", "\u200b"),
            embed=kwargs.get("embed", self.help_embed),
            view=self,
        )

        self.content = self.message.content
        self.embed = self.message.embeds[0]

    @property
    def help_embed(self):
        return (
            discord.Embed(
                color=self.bot.color, title="Title", description="Description"
            )
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/853174868551532564/860464565338898472/embed_thumbnail.png"
            )
            .set_image(
                url="https://cdn.discordapp.com/attachments/853174868551532564/860462053063393280/embed_image.png"
            )
            .set_footer(
                text="Footer Message",
                icon_url="https://media.discordapp.net/attachments/853174868551532564/860464989164535828/embed_footer.png",
            )
        )
