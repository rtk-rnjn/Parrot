from __future__ import annotations

import difflib
import os
import random
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from jishaku.functools import executor_function as executor
from PIL import Image, ImageFilter, ImageOps

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player

if TYPE_CHECKING:
    from core.bot import Parrot


class CountryGuesser:
    """Country guessing game, message-based.

    Shows a country's flag and the player guesses the name.
    """

    embed: discord.Embed
    accepted_length: int | None
    country: str

    def __init__(
        self,
        *,
        is_flags: bool = False,
        light_mode: bool = False,
        hard_mode: bool = False,
        guesses: int = 5,
        hints: int = 1,
    ) -> None:
        self.embed_color: DiscordColor | None = None
        self.hints = hints
        self.guesses = guesses

        self.is_flags = is_flags
        self.hard_mode = hard_mode

        self.light_mode = False if self.is_flags else light_mode

        folder = "assets/country-flags" if self.is_flags else "assets/country-data"
        self._countries_path = folder

        self.all_countries = os.listdir(self._countries_path)

    @executor
    def invert_image(self, image_path: BytesIO | os.PathLike | str) -> BytesIO:
        with Image.open(image_path) as image:
            img = image.convert("RGBA")
            r, g, b, a = img.split()
            rgb = Image.merge("RGB", (r, g, b))
            rgb = ImageOps.invert(rgb)
            rgb = rgb.split()
            img = Image.merge("RGBA", rgb + (a,))

            buf = BytesIO()
            img.save(buf, "PNG")
            buf.seek(0)
            return buf

    @executor
    def blur_image(self, image_path: BytesIO | os.PathLike | str) -> BytesIO:
        with Image.open(image_path) as image:
            img = image.convert("RGBA")
            img = img.filter(ImageFilter.GaussianBlur(10))

            buf = BytesIO()
            img.save(buf, "PNG")
            buf.seek(0)
            return buf

    async def get_country(self) -> discord.File:
        country_file = random.choice(self.all_countries)
        self.country = country_file.strip()[:-4].lower()

        file = os.path.join(self._countries_path, country_file)

        if self.hard_mode:
            file = await self.blur_image(file)

        if self.light_mode:
            file = await self.invert_image(file)

        return discord.File(file, "country.png")

    def get_blanks(self) -> str:
        return " ".join("_" if char != " " else " " for char in self.country)

    def get_hint(self) -> str:
        blanks = ["_" if char != " " else " " for char in self.country]
        times = round(len(blanks) / 3)

        for _ in range(times):
            idx = random.choice(range(len(self.country)))
            blanks[idx] = self.country[idx]
        return " ".join(blanks)

    def get_accuracy(self, guess: str) -> int:
        return round(difflib.SequenceMatcher(None, guess, self.country).ratio() * 100)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Guess that country!",
            description=f"```fix\n{self.get_blanks()}\n```",
            color=self.embed_color,
        )
        embed.add_field(
            name="\u200b",
            value=f"```yml\nblurred: {str(self.hard_mode).lower()}\nflag-mode: {str(self.is_flags).lower()}\n```",
            inline=False,
        )
        embed.set_image(url="attachment://country.png")
        return embed

    async def wait_for_response(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        options: tuple[str, ...] = (),
        length: int | None = None,
    ) -> tuple[discord.Message, str] | None:
        def check(m: discord.Message) -> bool:
            if length:
                return m.channel == ctx.channel and m.author == ctx.author and len(m.content) == length
            else:
                return m.channel == ctx.channel and m.author == ctx.author

        message: discord.Message = await ctx.bot.wait_for(
            "message",
            timeout=self.timeout,
            check=check,
        )
        content = message.content.strip().lower()

        if options:
            if content not in options:
                return

        return message, content

    async def start(  # noqa: PLR0912, PLR0913, C901
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
        ignore_diff_len: bool = False,
    ) -> discord.Message:
        file = await self.get_country()

        self.timeout = timeout
        self.embed_color = embed_color
        self.embed = self.get_embed()
        self.embed.set_footer(text="send your guess into the chat now!")

        self.message = await ctx.reply(embed=self.embed, file=file)

        self.accepted_length = len(self.country) if ignore_diff_len else None

        while not ctx.bot.is_closed():
            try:
                result = await self.wait_for_response(ctx, length=self.accepted_length)
            except TimeoutError:
                break

            if result is None:
                continue
            msg, response = result

            if response == self.country:
                await msg.reply(
                    f"That is correct! The country was `{self.country.title()}`",
                )
                break
            else:
                self.guesses -= 1

                if not self.guesses:
                    await msg.reply(
                        f"Game Over! you lost, The country was `{self.country.title()}`",
                    )
                    break

                acc = self.get_accuracy(response)

                if not self.hints:
                    await msg.reply(
                        f"That was incorrect! but you are `{acc}%` of the way there!\nYou have **{self.guesses}** guesses left.",
                        mention_author=False,
                    )
                else:
                    await msg.reply(
                        f"That is incorrect! but you are `{acc}%` of the way there!\nWould you like a hint? type: `(y/n)`",
                        mention_author=False,
                    )

                    try:
                        hint_result = await self.wait_for_response(
                            ctx,
                            options=("y", "n"),
                        )
                    except TimeoutError:
                        break
                    else:
                        if hint_result is None:
                            continue
                        hint_msg, resp = hint_result
                        if resp == "y":
                            hint = self.get_hint()
                            self.hints -= 1
                            await hint_msg.reply(
                                f"Here is your hint: `{hint}`",
                                mention_author=False,
                            )
                        else:
                            await hint_msg.reply(
                                f"Okay continue guessing! You have **{self.guesses}** guesses left.",
                                mention_author=False,
                            )

        return self.message


class CountryInput(discord.ui.Modal, title="Input your guess!"):
    def __init__(self, view: CountryView) -> None:
        super().__init__()
        self.view = view

        self.guess = discord.ui.TextInput(
            label="Input your guess",
            style=discord.TextStyle.short,
            required=True,
            max_length=self.view.game.accepted_length,
        )

        self.add_item(self.guess)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        guess = self.guess.value.strip().lower()
        game = self.view.game

        if guess == game.country:
            game.update_guesslog("+ GAME OVER, you won! +")
            await interaction.response.send_message(
                f"That is correct! The country was `{game.country.title()}`",
            )

            self.view.disable_all()
            game.embed.description = f"```fix\n{game.country.title()}\n```"
            assert interaction.message is not None
            await interaction.message.edit(view=self.view, embed=game.embed)
            self.view.stop()
            return
        else:
            game.guesses -= 1

            if not game.guesses:
                self.view.disable_all()
                game.update_guesslog("- GAME OVER, you lost -")

                assert interaction.message is not None
                await interaction.message.edit(embed=game.embed, view=self.view)
                await interaction.response.send_message(
                    f"Game Over! you lost, The country was `{game.country.title()}`",
                )
                self.view.stop()
                return
            else:
                acc = game.get_accuracy(guess)
                game.update_guesslog(
                    f"- [{guess}] was incorrect! but you are ({acc}%) of the way there!\n+ You have {game.guesses} guesses left.\n",
                )

                await interaction.response.edit_message(embed=game.embed)


class CountryView(BaseView):
    def __init__(
        self,
        game: BetaCountryGuesser,
        *,
        user: Player,
        timeout: float | None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(
                "This is not your game!",
                ephemeral=True,
            )
            return False
        else:
            return True

    @discord.ui.button(label="Make a guess!", style=discord.ButtonStyle.blurple)
    async def guess_button(self, interaction: discord.Interaction, _) -> None:
        await interaction.response.send_modal(CountryInput(self))

    @discord.ui.button(label="hint", style=discord.ButtonStyle.green)
    async def hint_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        hint = self.game.get_hint()
        self.game.hints -= 1
        await interaction.response.send_message(
            f"Here is your hint: `{hint}`",
            ephemeral=True,
        )

        if not self.game.hints:
            button.disabled = True
            assert interaction.message is not None
            await interaction.message.edit(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, _) -> None:
        self.disable_all()

        self.game.embed.description = f"```fix\n{self.game.country.title()}\n```"
        self.game.update_guesslog("- GAME OVER, CANCELLED -")

        await interaction.response.send_message(
            f"Game Over! The country was `{self.game.country.title()}`",
        )
        assert interaction.message is not None
        await interaction.message.edit(view=self, embed=self.game.embed)
        self.stop()


class BetaCountryGuesser(CountryGuesser):
    """Country guessing game, button-based.

    Same as :class:`CountryGuesser` but uses a modal for input.
    """

    guesslog: str = ""

    def update_guesslog(self, entry: str) -> None:
        self.guesslog += entry + "\n"
        self.embed.set_field_at(
            1,
            name="Guess Log",
            value=f"```diff\n{self.guesslog}\n```",
        )

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        ignore_diff_len: bool = False,
        timeout: float | None = None,
    ) -> discord.Message:
        self.accepted_length: int | None = len(self.country) if ignore_diff_len else None

        file = await self.get_country()

        self.embed_color = embed_color
        self.embed = self.get_embed()
        self.embed.add_field(
            name="Guess Log",
            value="```diff\n\u200b\n```",
            inline=False,
        )

        self.view = CountryView(self, user=ctx.author, timeout=timeout)
        self.message = await ctx.reply(embed=self.embed, file=file, view=self.view)
        self.view.message = self.message

        await self.view.wait()
        return self.message
