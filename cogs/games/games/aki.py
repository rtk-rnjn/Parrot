from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Literal

import discord
from akinator import AsyncAkinator as AkinatorGame, CantGoBackAnyFurther
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, double_wait

if TYPE_CHECKING:
    from core import Parrot


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
        self.message: discord.Message | None = None

        self.embed_color: DiscordColor | None = None
        self.back_button: bool = False
        self.delete_button: bool = False
        self.instructions: str = self.DEFAULT_INSTRUCTIONS

        self.bar: str = ""

    def build_bar(self) -> str:
        prog = round(self.aki.progression or 0 / 8)
        self.bar = f"[`{self.BAR * prog}{'  ' * (10 - prog)}`]"
        return self.bar

    def build_embed(self, *, instructions: bool = True) -> discord.Embed:
        embed = discord.Embed(
            title="Guess your character!",
            description=(
                f"```swift\nQuestion-Number  : {self.aki.step or 0 + 1}\nProgression-Level: {self.aki.progression:.2f}\n```\n{self.build_bar()}"
            ),
            color=self.embed_color,
        )
        embed.add_field(name="- Question -", value=self.aki.question)

        if instructions:
            embed.add_field(name="\N{ZERO WIDTH SPACE}", value=self.instructions, inline=False)

        embed.set_footer(text="Figuring out the next question | This may take a second")
        return embed

    def win(self) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        embed.title = "Character Guesser Engine Results"
        embed.description = f"Total Questions: `{self.aki.step or 0 + 1}`"

        embed.add_field(
            name="Character Guessed",
            value=f"\n**Name:** {self.aki.name_proposition} - {self.aki.description_proposition}",
        )
        embed.set_image(url=self.aki.photo)
        embed.set_footer(text="Was I correct?")

        return embed

    async def _wait_for_reaction(
        self,
        ctx: commands.Context[Parrot],
        timeout: float | None,
    ) -> tuple[discord.Reaction, discord.User] | None:
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            emoji = str(reaction.emoji)
            if self.message is None or reaction.message.id != self.message.id or user != ctx.author:
                return False
            try:
                Options(emoji)
                return True
            except ValueError:
                return emoji in (BACK, STOP)

        try:
            done, _ = await double_wait(
                ctx.bot.wait_for("reaction_add", timeout=timeout, check=check),
                ctx.bot.wait_for("reaction_remove", timeout=timeout, check=check),
            )
        except TimeoutError:
            return None
        return done.pop().result()

    async def _process_reaction(
        self,
        ctx: commands.Context[Parrot],
        reaction: discord.Reaction,
        user: discord.User,
        remove_reaction_after: bool,
    ) -> bool:
        if remove_reaction_after and self.message is not None:
            try:
                await self.message.remove_reaction(reaction, user)
            except discord.DiscordException:
                pass

        emoji = str(reaction.emoji)
        if emoji == STOP:
            await ctx.reply("**Session ended**")
            if self.message is not None:
                await self.message.delete()
            return True

        if emoji == BACK:
            try:
                await self.aki.back()
            except CantGoBackAnyFurther:
                if self.message is not None:
                    await self.message.reply("I cannot go back any further", delete_after=10)
        else:
            await self.aki.answer(Options(emoji).name)
        return False

    async def start(  # noqa: PLR0913
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

        while (self.aki.progression or 0) <= self.win_at:
            reaction_result = await self._wait_for_reaction(ctx, timeout)
            if reaction_result is None:
                return
            reaction, user = reaction_result

            if await self._process_reaction(ctx, reaction, user, remove_reaction_after):
                return

            embed = self.build_embed()
            await self.message.edit(embed=embed)

        embed = self.win()
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
        await interaction.response.defer(thinking=True)

        if answer == "back":
            try:
                await game.aki.back()
                embed = game.build_embed(instructions=False)
            except CantGoBackAnyFurther:
                await interaction.followup.send("I cant go back any further!", ephemeral=True)
                return
        else:
            await game.aki.answer(answer)

            if game.win_at is not None and (game.aki.progression or 0) >= game.win_at:
                self.disable_all()
                embed = game.win()
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
