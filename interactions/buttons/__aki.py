from __future__ import annotations

from typing import Optional, ClassVar, Any, Final, TypeAlias, Union

import discord
from discord.ext import commands
from akinator import CantGoBackAnyFurther
from akinator.async_aki import Akinator as AkinatorGame

from enum import Enum
import asyncio

BACK = "\N{BLACK LEFT-POINTING TRIANGLE}"
STOP = "\N{BLACK SQUARE FOR STOP}"


DiscordColor: TypeAlias = Union[discord.Color, int]
DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)


class Options(Enum):
    yes = "\N{WHITE HEAVY CHECK MARK}"
    no = "\N{CROSS MARK}"
    idk = "\N{SHRUG}"
    p = "\N{THINKING FACE}"
    pn  = "\N{CONFUSED FACE}"


class BaseView(discord.ui.View):
    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        return self.stop()


class Akinator:
    """
    Akinator Game, utilizes reactions
    """
    BAR: ClassVar[str] = "\N{FULL BLOCK}"*2
    instructions: ClassVar[str] = (
        '\N{WHITE HEAVY CHECK MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `yes`\n'
        '\N{CROSS MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `no`\n'
        '\N{SHRUG} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `I dont know`\n'
        '\N{THINKING FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably`\n'
        '\N{CONFUSED FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably not`\n'
    )

    def __init__(self) -> None:
        self.aki: AkinatorGame = AkinatorGame()

        self.player: Optional[discord.User] = None
        self.win_at: Optional[int] = None
        self.guess: Optional[dict[str, Any]] = None
        self.message: Optional[discord.Message] = None

        self.embed_color: Optional[DiscordColor] = None
        self.back_button: bool = False
        self.delete_button: bool = False

        self.bar: str = ''
        self.questions: int = 0

    def build_bar(self) -> str:
        prog = round(self.aki.progression / 8)
        self.bar = f"[`{self.BAR * prog}{'  ' * (10 - prog)}`]"
        return self.bar

    def build_embed(self, *, instructions: bool = True) -> discord.Embed:

        embed = discord.Embed(
            title = "Guess your character!",
            description = (
                "```swift\n"
                f"Question-Number  : {self.questions}\n"
                f"Progression-Level: {self.aki.progression:.2f}\n```\n"
                f"{self.build_bar()}"
            ),
            color = self.embed_color,
        )
        embed.add_field(name="- Question -", value=self.aki.question)

        if instructions:
            embed.add_field(name="\u200b", value=self.instructions, inline=False)

        embed.set_footer(text= "Figuring out the next question | This may take a second")
        return embed

    async def win(self) -> discord.Embed:

        await self.aki.win()
        self.guess = self.aki.first_guess

        embed = discord.Embed(color=self.embed_color)
        embed.title = "Character Guesser Engine Results"
        embed.description = f"Total Questions: `{self.questions}`"

        embed.add_field(name="Character Guessed", value=f"\n**Name:** {self.guess['name']}\n{self.guess['description']}")

        embed.set_image(url=self.guess['absolute_picture_path'])
        embed.set_footer(text="Was I correct?")

        return embed

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        remove_reaction_after: bool = False,
        win_at: int = 80,
        timeout: Optional[float] = None,
        back_button: bool = False,
        delete_button: bool = False,
        child_mode: bool = True,
    ) -> Optional[discord.Message]:
        """
        starts the akinator game
        Parameters
        ----------
        ctx : commands.Context
            the context of the invokation command
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        remove_reaction_after : bool, optional
            indicates whether to remove the user's reaction after or not, by default False
        win_at : int, optional
            indicates when to tell the akinator to make it's guess, by default 80
        timeout : Optional[float], optional
            indicates the timeout for when waiting, by default None
        back_button : bool, optional
            indicates whether to add a back button, by default False
        delete_button : bool, optional
            indicates whether to add a stop button to stop the game, by default False
        child_mode : bool, optional
            indicates to filter out NSFW content or not, by default True
        Returns
        -------
        Optional[discord.Message]
            returns the game message
        """

        self.back_button = back_button
        self.delete_button = delete_button
        self.embed_color = embed_color
        self.player = ctx.author
        self.win_at = win_at

        if self.back_button:
            self.instructions += f'{BACK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `back`\n'

        if self.delete_button:
            self.instructions += f'{STOP} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `cancel`\n'

        await self.aki.start_game(child_mode=child_mode)

        embed = self.build_embed()
        self.message = await ctx.send(embed=embed)

        for button in Options:
            await self.message.add_reaction(button.value)

        if self.back_button:
            await self.message.add_reaction(BACK)

        if self.delete_button:
            await self.message.add_reaction(STOP)

        while self.aki.progression <= self.win_at:

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                emoji = str(reaction.emoji)
                if reaction.message == self.message and user == ctx.author:
                    try:
                        return bool(Options(emoji))
                    except ValueError:
                        return emoji in (BACK, STOP)

            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
            except asyncio.TimeoutError:
                return

            if remove_reaction_after:
                try:
                    await self.message.remove_reaction(reaction, user)
                except discord.DiscordException:
                    pass

            emoji = str(reaction.emoji)

            if emoji == STOP:
                await ctx.send("**Session ended**")
                return await self.message.delete()

            if emoji == BACK:
                try:
                    await self.aki.back()
                except CantGoBackAnyFurther:
                    await self.message.reply('I cannot go back any further', delete_after=10)
            else:
                self.questions += 1

                await self.aki.answer(Options(emoji).name)

            embed = self.build_embed()
            await self.message.edit(embed=embed)

        embed = await self.win()
        return await self.message.edit(embed=embed)


class AkiButton(discord.ui.Button['AkiView']):

    async def callback(self, interaction: discord.Interaction) -> None:
        return await self.view.process_input(interaction, self.label.lower())


class AkiView(BaseView):
    OPTIONS: ClassVar[dict[str, discord.ButtonStyle]] = {
        'yes': discord.ButtonStyle.green,
        'no': discord.ButtonStyle.red,
        'idk': discord.ButtonStyle.blurple,
        'probably': discord.ButtonStyle.gray,
        'probably not': discord.ButtonStyle.gray,
    }

    def __init__(self, game: BetaAkinator, *, timeout: float) -> None:
        super().__init__(timeout=timeout)

        self.embed_color: Optional[DiscordColor] = None
        self.game = game

        for label, style in self.OPTIONS.items():
            self.add_item(AkiButton(label=label, style=style))

        if self.game.back_button:
            delete = AkiButton(
                label='back', 
                style=discord.ButtonStyle.red, 
                row=1
            )
            self.add_item(delete)

        if self.game.delete_button:
            delete = AkiButton(
                label='Cancel', 
                style=discord.ButtonStyle.red, 
                row=1
            )
            self.add_item(delete)

    async def process_input(self, interaction: discord.Interaction, answer: str) -> None:

        game = self.game

        if interaction.user != game.player:
            return await interaction.response.send_message(content="This isn't your game", ephemeral=True)
        
        if answer == "cancel":
            await interaction.message.reply("Session ended", mention_author=True)
            self.stop()
            return await interaction.message.delete()

        if answer == "back":
            try:
                await game.aki.back()
                embed = game.build_embed(instructions=False)
            except CantGoBackAnyFurther:
                return await interaction.response.send_message('I cant go back any further!', ephemeral=True)
        else:
            game.questions += 1
            await game.aki.answer(answer)
            
            if game.aki.progression >= game.win_at:
                self.disable_all()
                embed = await game.win()
                self.stop()
            else:
                embed = game.build_embed(instructions=False)

        return await interaction.response.edit_message(embed=embed, view=self)


class BetaAkinator(Akinator):
    """
    Akinator(buttons) Game
    """
    async def start(
        self, 
        ctx: commands.Context[commands.Bot],
        *,
        back_button: bool = False,
        delete_button: bool = False,
        embed_color: DiscordColor = DEFAULT_COLOR,
        win_at: int = 80, 
        timeout: Optional[float] = None,
        child_mode: bool = True,
    ) -> discord.Message:
        """
        starts the Akinator(buttons) game
        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            the context of the invokation command
        back_button : bool, optional
            indicates whether or not to add a back button, by default False
        delete_button : bool, optional
            indicates whether to add a stop button to stop the game, by default False
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        win_at : int, optional
            indicates when to tell the akinator to make it's guess, by default 80
        timeout : Optional[float], optional
            the timeout for the view, by default None
        child_mode : bool, optional
            indicates to filter out NSFW content or not, by default True
        Returns
        -------
        discord.Message
            returns the game message
        """
        self.back_button = back_button
        self.delete_button = delete_button
        self.embed_color = embed_color

        self.player = ctx.author
        self.win_at = win_at
        self.view = AkiView(self, timeout=timeout)

        await self.aki.start_game(child_mode=child_mode)

        embed = self.build_embed(instructions=False)
        self.message = await ctx.send(embed=embed, view=self.view)

        await self.view.wait()
        return self.message