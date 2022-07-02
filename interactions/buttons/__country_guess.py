from __future__ import annotations
import asyncio
import difflib
from io import BytesIO
import os
import pathlib
import random

from typing import Final, Optional, TypeAlias, Union

import discord
from discord.ext import commands

from utilities.converters import ToAsync
from PIL import Image, ImageFilter, ImageOps

DiscordColor: TypeAlias = Union[discord.Color, int]
DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)


class CountryGuesser:
    """
    CountryGuesser Game
    """
    embed: discord.Embed
    accepted_length: Optional[int]
    country: str

    def __init__(
        self,
        *,
        is_flags: bool = False,
        light_mode: bool = False,
        hard_mode: bool = False,
        guesses: int = 5,
        hints: int = 1
    ) -> None:

        self.embed_color: Optional[DiscordColor] = None
        self.hints = hints
        self.guesses = guesses

        self.is_flags = is_flags
        self.hard_mode = hard_mode

        if self.is_flags:
            self.light_mode: bool = False
        else:
            self.light_mode: bool = light_mode

        folder = 'extra/country-flags' if self.is_flags else 'extra/country-data'
        self._countries_path = folder

        self.all_countries = os.listdir(self._countries_path)

    @ToAsync()
    def invert_image(self, image_path: Union[BytesIO, os.PathLike, str]) -> BytesIO:
        with Image.open(image_path) as img:
            img = img.convert('RGBA')
            r, g, b, a = img.split()
            rgb = Image.merge('RGB', (r, g, b))
            rgb = ImageOps.invert(rgb)
            rgb = rgb.split()
            img = Image.merge('RGBA', rgb + (a,))

            buf = BytesIO()
            img.save(buf, 'PNG')
            buf.seek(0)
            return buf

    @ToAsync()
    def blur_image(self, image_path: Union[BytesIO, os.PathLike, str]) -> BytesIO:
        with Image.open(image_path) as img:
            img = img.convert('RGBA')
            img = img.filter(ImageFilter.GaussianBlur(10))

            buf = BytesIO()
            img.save(buf, 'PNG')
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

        return discord.File(file, 'country.png')

    def get_blanks(self) -> str:
        return ' '.join('_' if char != ' ' else ' ' for char in self.country)

    def get_hint(self) -> str:
        blanks = ['_' if char != ' ' else ' ' for char in self.country]
        times = round(len(blanks) / 3)

        for _ in range(times):
            idx = random.choice(range(len(self.country)))
            blanks[idx] = self.country[idx]
        return ' '.join(blanks)

    def get_accuracy(self, guess: str) -> int:
        return round(difflib.SequenceMatcher(None, guess, self.country).ratio() * 100)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='Guess that country!',
            description=f'```fix\n{self.get_blanks()}\n```',
            color=self.embed_color,
        )
        embed.add_field(
            name='\u200b',
            value=f'```yml\nblurred: {str(self.hard_mode).lower()}\nflag-mode: {str(self.is_flags).lower()}\n```',
            inline=False,
        )
        embed.set_image(url='attachment://country.png')
        return embed

    async def wait_for_response(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        options: tuple[str, ...] = (),
        length: Optional[int] = None,
    ) -> Optional[tuple[discord.Message, str]]:

        def check(m: discord.Message) -> bool:
            if length:
                return m.channel == ctx.channel and m.author == ctx.author and len(m.content) == length
            return m.channel == ctx.channel and m.author == ctx.author

        message: discord.Message = await ctx.bot.wait_for('message', timeout=self.timeout, check=check)
        content = message.content.strip().lower()

        if options:
            if not content in options:
                return

        return message, content

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        timeout: Optional[float] = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
        ignore_diff_len: bool = False
    ) -> discord.Message:
        """
        starts the country-guesser game
        Parameters
        ----------
        ctx : commands.Context
            the context of the invokation command
        timeout : Optional[float], optional
            the timeout for when waiting, by default None
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        ignore_diff_len : bool, optional
            specifies whether or not to ignore guesses that are not of the same length as the correct answer, by default False
        Returns
        -------
        discord.Message
            returns the game message
        """
        file = await self.get_country()

        self.timeout = timeout
        self.embed_color = embed_color
        self.embed = self.get_embed()
        self.embed.set_footer(text='send your guess into the chat now!')

        self.message = await ctx.send(embed=self.embed, file=file)

        self.accepted_length = len(self.country) if ignore_diff_len else None

        while not ctx.bot.is_closed():
            try:
                msg, response = await self.wait_for_response(ctx, length=self.accepted_length)
            except asyncio.TimeoutError:
                break

            if response == self.country:
                await msg.reply(f'That is correct! The country was `{self.country.title()}`')
                break
            else:
                self.guesses -= 1

                if not self.guesses:
                    await msg.reply(f'Game Over! you lost, The country was `{self.country.title()}`')
                    break

                acc = self.get_accuracy(response)

                if not self.hints:
                    await msg.reply(f'That was incorrect! but you are `{acc}%` of the way there!\nYou have **{self.guesses}** guesses left.', mention_author=False)
                else:
                    await msg.reply(f'That is incorrect! but you are `{acc}%` of the way there!\nWould you like a hint? type: `(y/n)`', mention_author=False)

                    try:
                        hint_msg, resp = await self.wait_for_response(ctx, options=('y', 'n'))
                    except asyncio.TimeoutError:
                        break
                    else:
                        if resp == 'y':
                            hint = self.get_hint()
                            self.hints -= 1
                            await hint_msg.reply(f'Here is your hint: `{hint}`', mention_author=False)
                        else:
                            await hint_msg.reply(f'Okay continue guessing! You have **{self.guesses}** guesses left.', mention_author=False)

        return self.message


class CountryInput(discord.ui.Modal, title='Input your guess!'):
    
    def __init__(self, view: CountryView) -> None:
        super().__init__()
        self.view = view

        self.guess = discord.ui.TextInput(
            label='Input your guess',
            style=discord.TextStyle.short,
            required=True,
            max_length=self.view.game.accepted_length,
        )

        self.add_item(self.guess)
        
    async def on_submit(self, interaction: discord.Interaction) -> None:
        guess = self.guess.value.strip().lower()
        game = self.view.game

        if guess == game.country:
            game.update_guesslog('+ GAME OVER, you won! +')
            await interaction.response.send_message(f'That is correct! The country was `{game.country.title()}`')

            self.view.disable_all()
            game.embed.description = f'```fix\n{game.country.title()}\n```'
            await interaction.message.edit(view=self.view, embed=game.embed)
            return self.view.stop()
        else:
            game.guesses -= 1

            if not game.guesses:
                self.view.disable_all()
                game.update_guesslog('- GAME OVER, you lost -')

                await interaction.message.edit(embed=game.embed, view=self.view)
                await interaction.response.send_message(f'Game Over! you lost, The country was `{game.country.title()}`')
                return self.view.stop()
            else:
                acc = game.get_accuracy(guess)
                game.update_guesslog(
                    f'- [{guess}] was incorrect! but you are ({acc}%) of the way there!\n'
                    f'+ You have {game.guesses} guesses left.\n'
                )

                await interaction.response.edit_message(embed=game.embed)


class CountryView(discord.ui.View):
    
    def __init__(self, game: BetaCountryGuesser, *, user: discord.User, timeout: float) -> None:
        super().__init__(timeout=timeout)

        self.game = game
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(f'This is not your game!', ephemeral=True)
            return False
        else:
            return True

    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        return self.stop()

    @discord.ui.button(label='Make a guess!', style=discord.ButtonStyle.blurple)
    async def guess_button(self, interaction: discord.Interaction, _) -> None:
        return await interaction.response.send_modal(CountryInput(self))

    @discord.ui.button(label='hint', style=discord.ButtonStyle.green)
    async def hint_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        hint = self.game.get_hint()
        self.game.hints -= 1
        await interaction.response.send_message(f'Here is your hint: `{hint}`', ephemeral=True)

        if not self.game.hints:
            button.disabled = True
            await interaction.message.edit(view=self)
            
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, _) -> None:
        self.disable_all()

        self.game.embed.description = f'```fix\n{self.game.country.title()}\n```'
        self.game.update_guesslog('- GAME OVER, CANCELLED -')

        await interaction.response.send_message(f'Game Over! The country was `{self.game.country.title()}`')
        await interaction.message.edit(view=self, embed=self.game.embed)
        return self.stop()


class BetaCountryGuesser(CountryGuesser):
    """
    Country Guesser(buttons) Game
    """
    guesslog: str = ''

    def update_guesslog(self, entry: str) -> None:
        self.guesslog += entry + '\n'
        self.embed.set_field_at(1, name='Guess Log', value=f'```diff\n{self.guesslog}\n```')

    async def start(
        self, 
        ctx: commands.Context[commands.Bot], 
        *, 
        embed_color: DiscordColor = DEFAULT_COLOR,
        ignore_diff_len: bool = False,
        timeout: Optional[float] = 120,
    ) -> discord.Message:  
        """
        starts the Country Guesser(buttons) Game
        Parameters
        ----------
        ctx : commands.Context
            the context of the invokation command
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        ignore_diff_len : bool, optional
            specifies whether or not to ignore guesses that are not of the same length as the correct answer, by default False
        timeout : Optional[float], optional
            the timeout for the view, by default None
        Returns
        -------
        discord.Message
            returns the game message
        """
        self.accepted_length = len(self.country) if ignore_diff_len else None

        file = await self.get_country()

        self.embed_color = embed_color
        self.embed = self.get_embed()
        self.embed.add_field(name='Guess Log', value='```diff\n\u200b\n```', inline=False)

        self.view = CountryView(self, user=ctx.author, timeout=timeout)
        self.message = await ctx.send(embed=self.embed, file=file, view=self.view)

        await self.view.wait()
        return self.message