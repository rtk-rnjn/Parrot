# https://github.com/Tom-the-Bomb/Discord-Games/

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Final, Optional, Union, Dict

from akinator import Answer, AsyncAkinator as AkinatorGame, CantGoBackAnyFurther, Language, Theme

import discord
from core import Context, Parrot

BACK = "\N{BLACK LEFT-POINTING TRIANGLE}"
STOP = "\N{BLACK SQUARE FOR STOP}"

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

DiscordColor: TypeAlias = Union[discord.Color, int]
DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)


class Options(Enum):
    yes = "\N{WHITE HEAVY CHECK MARK}"
    no = "\N{CROSS MARK}"
    idk = "\N{SHRUG}"
    p = "\N{THINKING FACE}"
    pn = "\N{CONFUSED FACE}"


class Akinator:
    """
    Akinator Game, utilizes reactions
    """

    BAR: ClassVar[str] = "\N{FULL BLOCK}" * 2
    instructions: ClassVar[str] = (
        "\N{WHITE HEAVY CHECK MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `yes`\n"
        "\N{CROSS MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `no`\n"
        "\N{SHRUG} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `I dont know`\n"
        "\N{THINKING FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably`\n"
        "\N{CONFUSED FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably not`\n"
    )

    def __init__(self) -> None:
        self.aki: AkinatorGame = AkinatorGame()

        self.player: Optional[Union[discord.User, discord.Member]] = None
        self.win_at: Optional[int] = None
        self.guess: Optional[Dict[str, Any]] = None
        self.message: Optional[discord.Message] = None

        self.embed_color: Optional[DiscordColor] = None
        self.back_button: bool = False
        self.delete_button: bool = False

        self.bar: str = ""

    def build_bar(self) -> str:
        prog = round(self.aki.progression / 8)
        self.bar = f"[`{self.BAR * prog}{'  ' * (10 - prog)}`]"
        return self.bar

    def build_embed(self, *, instructions: bool = True) -> discord.Embed:
        embed = discord.Embed(
            title="Guess your character!",
            description=(
                "```swift\n"
                f"Question-Number  : {self.aki.step + 1}\n"
                f"Progression-Level: {self.aki.progression:.2f}\n```\n"
                f"{self.build_bar()}"
            ),
            color=self.embed_color,
        )
        embed.add_field(name="- Question -", value=self.aki.question)

        if instructions:
            embed.add_field(name="\u200b", value=self.instructions, inline=False)

        embed.set_footer(text="Figuring out the next question | This may take a second")
        return embed

    async def win(self) -> discord.Embed:
        await self.aki.win()
        self.guess = self.aki.first_guess

        embed = discord.Embed(color=self.embed_color)
        embed.title = "Character Guesser Engine Results"
        embed.description = f"Total Questions: `{self.aki.step + 1}`"

        embed.add_field(
            name="Character Guessed",
            value=f"\n**Name:** {self.guess.name}\n{self.guess.description}",
        )

        embed.set_image(url=self.guess.absolute_picture_path)
        embed.set_footer(text="Was I correct?")

        await self.bot.game_collections.update_one(
            {
                "_id": self.player.id,
            },
            {
                "$inc": {
                    "game_aki_played": 1,
                }
            },
            upsert=True,
        )
        return embed

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        remove_reaction_after: bool = True,
        win_at: int = 80,
        timeout: Optional[float] = None,
        back_button: bool = False,
        delete_button: bool = False,
        aki_theme: str = "Characters",
        aki_language: str = "English",
        child_mode: bool = False,
    ) -> Optional[discord.Message]:
        self.back_button = back_button
        self.delete_button = delete_button
        self.embed_color = embed_color
        self.player = ctx.author
        self.win_at = win_at
        self.bot = ctx.bot

        if self.back_button:
            self.instructions += f"{BACK} 🠒 `back`\n"

        if self.delete_button:
            self.instructions += f"{STOP} 🠒 `cancel`\n"

        self.aki.theme = Theme.from_str(aki_theme)
        self.aki.language = Language.from_str(aki_language)
        self.aki.child_mode = child_mode
        await self.aki.start_game()

        embed = self.build_embed()
        self.message = await ctx.send(embed=embed)

        assert self.message is not None

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
                return False

            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
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
                    await self.message.reply("I cannot go back any further", delete_after=10)
            else:
                answer = Answer.from_str(Options(emoji).name)
                await self.aki.answer(answer)

            embed = self.build_embed()
            await self.message.edit(embed=embed)

        embed = await self.win()
        return await self.message.edit(embed=embed)
