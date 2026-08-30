from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import discord
from akinator import AsyncAkinator as AkinatorGame, CantGoBackAnyFurther
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, double_wait

if TYPE_CHECKING:
    from core.bot import Parrot


class Options(Enum):
    yes = "\N{WHITE HEAVY CHECK MARK}"
    no = "\N{CROSS MARK}"
    idk = "\N{SHRUG}"
    p = "\N{THINKING FACE}"
    pn = "\N{CONFUSED FACE}"


BACK = "\N{BLACK LEFT-POINTING TRIANGLE}"
STOP = "\N{BLACK SQUARE FOR STOP}"


class Akinator:
    """Akinator game, reaction-based.

    The bot asks yes/no questions and tries to guess
    the character the player is thinking of.
    """

    BAR: ClassVar[str] = "\N{FULL BLOCK}" * 2
    DEFAULT_INSTRUCTIONS: ClassVar[str] = (
        "\N{WHITE HEAVY CHECK MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `yes`\n"
        "\N{CROSS MARK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `no`\n"
        "\N{SHRUG} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `I dont know`\n"
        "\N{THINKING FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably`\n"
        "\N{CONFUSED FACE} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `probably not`\n"
    )

    def __init__(self) -> None:
        self.aki: AkinatorGame = AkinatorGame()

        self.player: Player | None = None
        self.win_at: int | None = None
        self.guess: Any = None
        self.message: discord.Message | None = None

        self.embed_color: DiscordColor | None = None
        self.back_button: bool = False
        self.delete_button: bool = False
        self.instructions: str = self.DEFAULT_INSTRUCTIONS

        self.bar: str = ""

    def build_bar(self) -> str:
        prog = round(self.aki.progression / 8)  # type: ignore[operator]
        self.bar = f"[`{self.BAR * prog}{'  ' * (10 - prog)}`]"
        return self.bar

    def build_embed(self, *, instructions: bool = True) -> discord.Embed:
        embed = discord.Embed(
            title="Guess your character!",
            description=(
                "```swift\n"
                f"Question-Number  : {self.aki.step + 1}\n"  # type: ignore[operator]
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
        await self.aki.win()  # type: ignore[func-call]
        self.guess = self.aki.first_guess  # type: ignore[attr-defined]

        embed = discord.Embed(color=self.embed_color)
        embed.title = "Character Guesser Engine Results"
        embed.description = f"Total Questions: `{self.aki.step + 1}`"  # type: ignore[operator]

        embed.add_field(
            name="Character Guessed",
            value=f"\n**Name:** {self.guess.name}\n{self.guess.description}",
        )

        embed.set_image(url=self.guess.absolute_picture_path)
        embed.set_footer(text="Was I correct?")

        return embed

    async def start(  # noqa: PLR0912, PLR0913, C901
        self,
        ctx: commands.Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        remove_reaction_after: bool = False,
        win_at: int = 80,
        timeout: float | None = None,
        back_button: bool = False,
        delete_button: bool = False,
        aki_theme: Literal["c", "a", "o"] = "c",
        aki_language: str = "en",
        child_mode: bool = True,
    ) -> discord.Message | None:

        self.back_button = back_button
        self.delete_button = delete_button
        self.embed_color = embed_color
        self.player = ctx.author
        self.win_at = win_at

        if self.back_button:
            self.instructions += f"{BACK} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `back`\n"

        if self.delete_button:
            self.instructions += f"{STOP} \N{RIGHTWARDS ARROW WITH SMALL EQUILATERAL ARROWHEAD} `cancel`\n"

        await self.aki.start_game(
            language=aki_language,
            child_mode=child_mode,
            theme=aki_theme,
        )

        embed = self.build_embed()
        self.message = await ctx.reply(embed=embed)

        for button in Options:
            await self.message.add_reaction(button.value)

        if self.back_button:
            await self.message.add_reaction(BACK)

        if self.delete_button:
            await self.message.add_reaction(STOP)

        while self.aki.progression <= self.win_at:  # type: ignore[operator]

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                emoji = str(reaction.emoji)
                if self.message is not None and reaction.message.id == self.message.id and user == ctx.author:
                    try:
                        return bool(Options(emoji))
                    except ValueError:
                        return emoji in (BACK, STOP)
                return False

            try:
                done, _ = await double_wait(
                    ctx.bot.wait_for("reaction_add", timeout=timeout, check=check),
                    ctx.bot.wait_for("reaction_remove", timeout=timeout, check=check),
                )
                reaction, user = done.pop().result()
            except TimeoutError:
                return

            if remove_reaction_after:
                try:
                    await self.message.remove_reaction(reaction, user)
                except discord.DiscordException:
                    pass

            emoji = str(reaction.emoji)

            if emoji == STOP:
                await ctx.reply("**Session ended**")
                return await self.message.delete()

            if emoji == BACK:
                try:
                    await self.aki.back()
                except CantGoBackAnyFurther:
                    await self.message.reply("I cannot go back any further", delete_after=10)
            else:
                await self.aki.answer(Options(emoji).name)

            embed = self.build_embed()
            await self.message.edit(embed=embed)

        embed = await self.win()
        return await self.message.edit(embed=embed)


class AkiButton(discord.ui.Button["AkiView"]):
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        assert self.label is not None
        await self.view.process_input(interaction, self.label.lower())


class AkiView(BaseView):
    OPTIONS: ClassVar[dict[str, discord.ButtonStyle]] = {
        "yes": discord.ButtonStyle.green,
        "no": discord.ButtonStyle.red,
        "idk": discord.ButtonStyle.blurple,
        "probably": discord.ButtonStyle.gray,
        "probably not": discord.ButtonStyle.gray,
    }

    def __init__(self, game: BetaAkinator, *, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.embed_color: DiscordColor | None = None
        self.game = game

        for label, style in self.OPTIONS.items():
            self.add_item(AkiButton(label=label, style=style))

        if self.game.back_button:
            delete = AkiButton(label="back", style=discord.ButtonStyle.red, row=1)
            self.add_item(delete)

        if self.game.delete_button:
            delete = AkiButton(label="Cancel", style=discord.ButtonStyle.red, row=1)
            self.add_item(delete)

    async def process_input(self, interaction: discord.Interaction, answer: str) -> None:
        game = self.game

        if interaction.user != game.player:
            await interaction.response.send_message(content="This isn't your game", ephemeral=True)
            return

        if answer == "cancel":
            assert interaction.message is not None
            await interaction.message.reply("Session ended", mention_author=True)
            self.stop()
            await interaction.message.delete()
            return

        # defer to avoid 3s interaction timeout while waiting for the akinator API
        await interaction.response.defer()

        if answer == "back":
            try:
                await game.aki.back()
                embed = game.build_embed(instructions=False)
            except CantGoBackAnyFurther:
                await interaction.followup.send("I cant go back any further!", ephemeral=True)
                return
        else:
            await game.aki.answer(answer)

            if game.win_at is not None and game.aki.progression >= game.win_at:  # type: ignore[operator]
                self.disable_all()
                embed = await game.win()
                self.stop()
            else:
                embed = game.build_embed(instructions=False)
        try:
            await interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            pass


class BetaAkinator(Akinator):
    """Akinator game, button-based.

    Same as :class:`Akinator` but uses UI buttons
    instead of reactions.
    """

    async def start(  # noqa: PLR0913
        self,
        ctx: commands.Context[Parrot],
        *,
        back_button: bool = False,
        delete_button: bool = False,
        embed_color: DiscordColor = DEFAULT_COLOR,
        win_at: int = 80,
        timeout: float | None = None,
        aki_theme: Literal["c", "a", "o"] = "c",
        aki_language: str = "en",
        child_mode: bool = True,
    ) -> discord.Message:
        self.back_button = back_button
        self.delete_button = delete_button
        self.embed_color = embed_color

        self.player = ctx.author
        self.win_at = win_at
        self.view = AkiView(self, timeout=timeout)

        await self.aki.start_game(
            language=aki_language,
            child_mode=child_mode,
            theme=aki_theme,
        )

        embed = self.build_embed(instructions=False)
        self.message = await ctx.reply(embed=embed, view=self.view)
        self.view.message = self.message

        await self.view.wait()
        return self.message
