from __future__ import annotations

import asyncio
import colorsys
import datetime
import difflib
import functools
import html
import io
import itertools
import json
import logging
import math
import random
import re
import string
from collections import defaultdict
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict, cast

import discord
from colorama import Fore
from discord.ext import commands
from discord.ext.commands import Context
from PIL import Image, ImageColor
from rapidfuzz.process import extractOne as rf_extract_one

from core.utils import PaginationView

from .pour_puzzle import PourView

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.fun")

THUMBNAIL_SIZE = (80, 80)
SECTION_SEPERATOR = "\N{WHITE RIGHT POINTING BACKHAND INDEX}\N{WHITE LEFT POINTING BACKHAND INDEX}"

# fmt: off
CHARACTER_VALUES = {
    200: "\N{PEOPLE HUGGING}",
    50 : "\N{SPARKLING HEART}",
    10 : "\N{SPARKLES}",
    5  : "\N{FACE WITH PLEADING EYES}",
    1  : ",",
    0  : "\N{HEAVY BLACK HEART}",
}
# fmt: on

with open("assets/color_names.json", encoding="utf-8") as file:
    color_names: dict[str, str] = json.load(file)


class QuizData(TypedDict):
    category: str
    type: Literal["multiple", "boolean"]
    difficulty: Literal["easy", "medium", "hard"]
    question: str
    correct_answer: str
    incorrect_answers: list[str]


def to_bottom(text: str) -> str:
    out = bytearray()

    for char in text.encode():
        temp_char = char
        while temp_char != 0:
            for value, emoji in CHARACTER_VALUES.items():
                if temp_char >= value:
                    temp_char -= value
                    out += emoji.encode()
                    break

        out += SECTION_SEPERATOR.encode()

    return out.decode("utf-8")


def from_bottom(text: str) -> str:
    out = bytearray()
    text = text.strip().removesuffix(SECTION_SEPERATOR)

    if any(c not in CHARACTER_VALUES.values() for c in text.replace(SECTION_SEPERATOR, "")):
        msg = f"Invalid bottom text: {text}"
        raise TypeError(msg)

    for char in text.split(SECTION_SEPERATOR):
        rev_mapping = {v: k for k, v in CHARACTER_VALUES.items()}

        sub = sum(rev_mapping[emoji] for emoji in char)
        out += sub.to_bytes(1, "big")

    return out.decode()


def replace_many(
    sentence: str,
    replacements: dict[str, str],
    *,
    ignore_case: bool = False,
    match_case: bool = False,
) -> str:
    if ignore_case:
        replacements = {word.lower(): replacement for word, replacement in replacements.items()}

    words_to_replace = sorted(replacements, key=lambda s: (-len(s), s))

    # Join and compile words to replace into a regex
    pattern = "|".join(re.escape(word) for word in words_to_replace)
    regex = re.compile(pattern, re.I if ignore_case else 0)

    def _repl(match: re.Match) -> str:
        """Returns replacement depending on `ignore_case` and `match_case`."""
        word: str = match[0]
        replacement = replacements[word.lower() if ignore_case else word]

        if not match_case:
            return replacement

        # Clean punctuation from word so string methods work
        cleaned_word = word.translate(str.maketrans("", "", string.punctuation))
        if cleaned_word.isupper():
            return replacement.upper()
        if cleaned_word[0].isupper():
            return replacement.capitalize()
        return replacement.lower()

    return regex.sub(_repl, sentence)


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


UWU_WORDS = {
    "fi": "fwi",
    "l": "w",
    "r": "w",
    "some": "sum",
    "th": "d",
    "thing": "fing",
    "tho": "fo",
    "you're": "yuw'we",
    "your": "yur",
    "you": "yuw",
}


class QuizConfigLayout(discord.ui.LayoutView):
    def __init__(self, *, author: discord.User | discord.Member):
        super().__init__()
        self.url: str | None = None

        self.author = author

        header = discord.ui.TextDisplay(
            "# Quiz Configuration\n"
            "-# This quiz is provided by the Open Trivia Database.\n"
            "-# Creative Commons Attribution-ShareAlike 4.0 International License",
        )
        self.category_select = discord.ui.Select(
            placeholder="Any Category",
            options=[
                discord.SelectOption(label=label, value=value)
                for label, value in [
                    ("General Knowledge", "9"),
                    ("Entertainment: Books", "10"),
                    ("Entertainment: Film", "11"),
                    ("Entertainment: Music", "12"),
                    ("Entertainment: Musicals & Theatres", "13"),
                    ("Entertainment: Television", "14"),
                    ("Entertainment: Video Games", "15"),
                    ("Entertainment: Board Games", "16"),
                    ("Science & Nature", "17"),
                    ("Science: Computers", "18"),
                    ("Mythology", "20"),
                    ("Sports", "21"),
                    ("Geography", "22"),
                    ("History", "23"),
                    ("Politics", "24"),
                    ("Art", "25"),
                    ("Celebrities", "26"),
                    ("Animals", "27"),
                    ("Vehicles", "28"),
                    ("Entertainment: Comics", "29"),
                    ("Science: Gadgets", "30"),
                    ("Entertainment: Japanese Anime & Manga", "31"),
                    ("Entertainment: Cartoon & Animations", "32"),
                ]
            ],
        )
        self.category_select.callback = self.category_select_callback

        self.difficulty_select = discord.ui.Select(
            placeholder="Any Difficulty",
            options=[
                discord.SelectOption(label=label, value=value)
                for label, value in [
                    ("Easy", "easy"),
                    ("Medium", "medium"),
                    ("Hard", "hard"),
                ]
            ],
        )
        self.difficulty_select.callback = self.difficulty_select_callback

        self.type_select = discord.ui.Select(
            placeholder="Any Type",
            options=[
                discord.SelectOption(label=label, value=value)
                for label, value in [
                    ("Multiple Choice", "multiple"),
                    ("True / False", "boolean"),
                ]
            ],
        )
        self.type_select.callback = self.type_select_callback

        self.start_button = discord.ui.Button(
            label="Start Quiz",
            style=discord.ButtonStyle.green,
        )
        self.start_button.callback = self.start_quiz

        self.cancel_button = discord.ui.Button(
            label="Cancel Quiz",
            style=discord.ButtonStyle.red,
        )
        self.cancel_button.callback = self.cancel_quiz

        container = discord.ui.Container(
            header,
            discord.ui.Separator(),
            discord.ui.TextDisplay("Select a category for the quiz below:"),
            discord.ui.ActionRow(self.category_select),
            discord.ui.Separator(),
            discord.ui.TextDisplay("Select difficulty for the quiz below:"),
            discord.ui.ActionRow(self.difficulty_select),
            discord.ui.Separator(),
            discord.ui.TextDisplay("Select type for the quiz below:"),
            discord.ui.ActionRow(self.type_select),
            discord.ui.Separator(),
            discord.ui.ActionRow(self.start_button, self.cancel_button),
        )

        self.add_item(container)

    async def start_quiz(self, interaction: discord.Interaction):
        category = self.category_select.values[0] if self.category_select.values else ""
        difficulty = self.difficulty_select.values[0] if self.difficulty_select.values else ""
        q_type = self.type_select.values[0] if self.type_select.values else ""

        self.url = f"https://opentdb.com/api.php?amount=10&category={category}&difficulty={difficulty}&type={q_type}"
        content = f"Starting quiz with the following configuration:\nCategory: {category or 'Any'}\nDifficulty: {difficulty or 'Any'}\nType: {q_type or 'Any'}"
        await interaction.response.send_message(content, ephemeral=True)
        self.stop()

    async def category_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    async def difficulty_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    async def type_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    async def cancel_quiz(self, interaction: discord.Interaction):
        await interaction.response.send_message("Quiz cancelled.", ephemeral=True)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:

        if interaction.user != self.author:
            await interaction.response.send_message("You can not interact with this view", ephemeral=True)
            return False

        return True


class ColorHandler:
    bot: Parrot

    async def send_colour_response(self, ctx: Context[Parrot], rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> None:
        """Create and send embed from user given colour information."""
        name = self._rgb_to_name(rgb)
        try:
            colour_or_color = ctx.invoked_parents[0]
        except IndexError:
            colour_or_color = "colour"

        colour_mode = ctx.invoked_with
        if colour_mode == "random":
            colour_mode = colour_or_color
            input_colour = name
        elif colour_mode in ("colour", "color"):
            input_colour = ctx.kwargs["colour_input"]
        elif colour_mode == "name":
            input_colour = ctx.kwargs["user_colour_name"]
        elif colour_mode == "hex":
            input_colour = ctx.args[2:][0]
            if len(input_colour) > 7:
                input_colour = input_colour[:-2]
        else:
            input_colour = tuple(ctx.args[2:])

        if colour_mode is not None:
            if colour_mode not in ("name", "hex", "random", "color", "colour"):
                colour_mode = colour_mode.upper()
            else:
                colour_mode = colour_mode.title()

        colour_embed = discord.Embed(
            title=f"{name or input_colour}",
            description=f"{colour_or_color.title()} information for {colour_mode} `{input_colour or name}`.",
            colour=discord.Color.from_rgb(*rgb),
        )
        colour_conversions = self.get_colour_conversions(rgb)
        for colour_space, value in colour_conversions.items():
            colour_embed.add_field(name=colour_space, value=f"`{value}`", inline=True)

        thumbnail = Image.new("RGB", THUMBNAIL_SIZE, color=rgb)
        buffer = io.BytesIO()

        await asyncio.to_thread(thumbnail.save, buffer, "PNG")
        await asyncio.to_thread(buffer.seek, 0)
        thumbnail_file = discord.File(buffer, filename="colour.png")

        colour_embed.set_thumbnail(url="attachment://colour.png")

        await ctx.reply(file=thumbnail_file, embed=colour_embed)

    def get_colour_conversions(self, rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> dict[str, Any]:
        """Create a dictionary mapping of colour types and their values."""
        colour_name = self._rgb_to_name(rgb)
        if colour_name is None:
            colour_name = "No match found"
        return {
            "RGB": rgb,
            "HSV": self._rgb_to_hsv(rgb),
            "HSL": self._rgb_to_hsl(rgb),
            "CMYK": self._rgb_to_cmyk(rgb),
            "Hex": self._rgb_to_hex(rgb),
            "Name": colour_name,
        }

    @staticmethod
    def _rgb_to_hsv(rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> tuple[int, int, int]:
        """Convert RGB values to HSV values."""
        rgb_list = [val / 255 for val in rgb]
        h, s, v = colorsys.rgb_to_hsv(*rgb_list)
        return round(h * 360), round(s * 100), round(v * 100)

    @staticmethod
    def _rgb_to_hsl(rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> tuple[int, int, int]:
        """Convert RGB values to HSL values."""
        rgb_list = [val / 255.0 for val in rgb]
        h, l, s = colorsys.rgb_to_hls(*rgb_list)  # noqa: E741
        return round(h * 360), round(s * 100), round(l * 100)

    @staticmethod
    def _rgb_to_cmyk(rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Convert RGB values to CMYK values."""
        rgb_list = [val / 255.0 for val in rgb]
        if not any(rgb_list):
            return 0, 0, 0, 100
        k = 1 - max(rgb_list)
        c = round((1 - rgb_list[0] - k) * 100 / (1 - k))
        m = round((1 - rgb_list[1] - k) * 100 / (1 - k))
        y = round((1 - rgb_list[2] - k) * 100 / (1 - k))
        return c, m, y, round(k * 100)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> str:
        """Convert RGB values to HEX code."""
        hex_ = "".join([hex(val)[2:].zfill(2) for val in rgb])
        return f"#{hex_}".upper()

    def _rgb_to_name(self, rgb: tuple[int, int, int] | tuple[int, int, int, int]) -> str | None:
        """Convert RGB values to a fuzzy matched name."""
        input_hex_colour = self._rgb_to_hex(rgb)
        try:
            maybe_none = rf_extract_one(query=input_hex_colour, choices=color_names.values(), score_cutoff=80)
            if maybe_none is None:
                raise TypeError
            match, _, _ = maybe_none
            colour_name = [name for name, hex_code in color_names.items() if hex_code == match][0]
        except TypeError:
            colour_name = None
        return colour_name

    def match_colour_name(self, input_colour_name: str) -> str | None:
        """Convert a colour name to HEX code."""
        try:
            maybe_none = rf_extract_one(query=input_colour_name, choices=color_names.keys(), score_cutoff=80)
            if maybe_none is None:
                raise TypeError
            match, _, _ = maybe_none
        except ValueError, TypeError:
            return None
        return f"#{color_names[match]}"


class Fun(commands.Cog, ColorHandler):
    """Fun commands for the bot."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="guess-the-number", aliases=["gtn"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def guess_the_number(
        self,
        ctx: Context[Parrot],
        upper: int = commands.parameter(converter=int, default=10, description="The upper bound of the guessing range."),
        lower: int = commands.parameter(converter=int, default=1, description="The lower bound of the guessing range."),
    ):
        """Guess the number game"""
        upper, lower = max(upper, lower), min(upper, lower)
        number = random.randint(lower, upper)

        number_of_chances = math.log(upper - lower + 1, 2)
        number_of_chances = round(number_of_chances)
        await ctx.reply(f"{ctx.author.mention} Guess a number between **{lower}** and **{upper}** in **{number_of_chances}** chances. Goodluck")
        count = 0

        def check(m: discord.Message) -> bool:
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.isdigit()

        while count < number_of_chances:
            count += 1

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except TimeoutError:
                return await ctx.reply("You took too long to respond. Game Over")

            guess = int(msg.content)

            if guess == number:
                await ctx.reply(f"{ctx.author.mention} Congratulation, you guessed the number in **{count}** attempts :tada:.")
                return

            if guess < number:
                await ctx.reply(f"{ctx.author.mention} Your guess is **too low**. Try again", delete_after=4)

            else:
                await ctx.reply(f"{ctx.author.mention} Your guess is **too high**. Try again", delete_after=4)

        if count >= number_of_chances:
            await ctx.reply(f"{ctx.author.mention} The number is **{number}**. Better luck next time")

    @commands.command(name="cathi")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_cathi(
        self,
        ctx: Context[Parrot],
        text: str = commands.parameter(description="The text for the cat to say.", default="Hi..."),
    ):
        """Make a cat say something."""
        # please dont DM to ask what is this, I forget
        m: discord.Message = await ctx.reply("starting")

        FWLL = "\N{FULLWIDTH LOW LINE}"
        LL = "\N{LOW LINE}"
        IGS = "\N{IDEOGRAPHIC SPACE}"
        FWS = "\N{FULLWIDTH SOLIDUS}"
        FWRS = "\N{FULLWIDTH REVERSE SOLIDUS}"
        FM = "\N{FULLWIDTH MACRON}"
        LA = "\N{LOGICAL AND}"

        FACE = "\N{ACUTE ACCENT}\N{HALFWIDTH KATAKANA MIDDLE DOT}\N{GREEK SMALL LETTER OMEGA}\N{HALFWIDTH KATAKANA MIDDLE DOT}\N{GRAVE ACCENT}"
        ls = [
            f". {IGS}{IGS}{IGS}{FWLL}{FWLL}{LL}{FWLL}{FWLL}\n"
            f"{IGS}{IGS}{FWS}{IGS}{FWS}{IGS}  {FWS}|\n"
            f"{IGS}{IGS}|{FM}{FM}{FM}{FM}|{IGS}|\n"
            f"{IGS}{IGS}|{IGS}{IGS}{IGS}{IGS}|{FWS}\n"
            f"{IGS}{IGS}{FM}{FM}{FM}{FM}",
            f". {IGS}{IGS}{IGS}{text}\n"
            f"{IGS}   {IGS} {LA}{FWLL}{LA}{FWLL}_\n"
            f"{IGS}{IGS}{FWS}({FACE})  {FWS}{FWRS}\n"
            f"{IGS}{FWS}|{FM}{FM}{FM}{FM}|{FWRS}{FWS}\n"
            f"{IGS}{IGS}|{IGS}{IGS}{IGS}{IGS}|{FWS}\n"
            f"{IGS}{IGS}{FM}{FM}{FM}{FM}",
        ]
        for _, cat in itertools.product(range(3), ls):
            await m.edit(content=cat)
            await asyncio.sleep(1.5)

    @commands.command(name="flop")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_flop(self, ctx: Context[Parrot]):
        """Flop."""
        m = await ctx.reply("Starting...")
        DEGREE_SIGN = "\N{DEGREE SIGN}"
        WHITE_SQUARE = "\N{WHITE SQUARE}"
        EM_DASH = "\N{EM DASH}"
        HAND_UP = "\N{BOX DRAWINGS LIGHT ARC UP AND LEFT}"
        CURVE_DOWN = "\N{PRESENTATION FORM FOR VERTICAL LEFT PARENTHESIS}"

        ls = (
            rf"(   {DEGREE_SIGN} - {DEGREE_SIGN}) (' - '   )",
            rf"(\{DEGREE_SIGN} - {DEGREE_SIGN})\ (' - '   )",
            rf"({EM_DASH}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){EM_DASH} (' - '   )",
            rf"({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}(' - '   )",
            rf"({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}{CURVE_DOWN}(\\ .o.)\\",
        )
        for i in ls:
            await m.edit(content=i)
            await asyncio.sleep(1.5)

    @commands.command(name="poof", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_poof(self, ctx: Context[Parrot]):
        """Poof."""
        m: discord.Message = await ctx.reply("...")
        ls = ("(   ' - ')", r"' \- ')", r"\- ')", "')", ")", "*poofness*")
        for i in ls:
            await m.edit(content=discord.utils.escape_markdown(i))
            await asyncio.sleep(1.5)

    @commands.command(name="virus", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_virus(
        self,
        ctx: Context[Parrot],
        user: discord.Member = commands.parameter(description="The user to infect.", default=commands.parameters.Author),  # noqa: B008
        virus: str = commands.parameter(description="The name of the virus to insert.", default="trojan"),
    ):
        """Insert a virus to yourself or someone else."""
        m = await ctx.reply("...")
        user = user or ctx.author
        DARK_SHADE = "\N{DARK SHADE}"

        PREFIX = "```ansi\n"
        SUFFIX = "\n```"

        SHIFTER = 24

        def D(n: int) -> str:
            return DARK_SHADE * n + " " * (SHIFTER - n)

        rotator = itertools.cycle(["/", "-", "\\", "|"])
        dot_rotator = itertools.cycle([".", "..", "..."])

        ls = [
            f"{Fore.WHITE}[{Fore.GREEN}{D(i)}{Fore.WHITE}] {Fore.YELLOW}{next(rotator)} {Fore.BLUE}{virus}-virus.exe Packing files{next(dot_rotator)}"
            for i in range(3, SHIFTER, 3)
        ]
        ls.append(f"{Fore.WHITE}[{Fore.GREEN}{'Successfully downloaded':<24}{Fore.WHITE}] {Fore.YELLOW}{next(rotator)} {Fore.BLUE}{virus}-virus.exe")
        for _ in range(3):
            ls.append(
                f"{Fore.WHITE}[{Fore.RED}{f'Injecting virus{next(dot_rotator)}':<24}{Fore.WHITE}] {Fore.YELLOW}{next(rotator)} {Fore.BLUE}{virus}-virus.exe",
            )
        ls.append(f"{Fore.GREEN}Successfully {Fore.WHITE}Injected {Fore.RED}{virus}-virus.exe into {Fore.YELLOW}{user.name}")
        for i in ls:
            await m.edit(content=f"{PREFIX}{i}{SUFFIX}")
            await asyncio.sleep(1.5)

    @commands.command(name="boom", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_boom(self, ctx: Context[Parrot]):
        """Booms a message!."""
        m = await ctx.reply("THIS MESSAGE WILL SELFDESTRUCT IN 5")
        await asyncio.sleep(1.5)
        ls = (
            "THIS MESSAGE WILL SELFDESTRUCT IN 4",
            "THIS MESSAGE WILL SELFDESTRUCT IN 3",
            "THIS MESSAGE WILL SELFDESTRUCT IN 2",
            "THIS MESSAGE WILL SELFDESTRUCT IN 1",
            "THIS MESSAGE WILL SELFDESTRUCT IN 0",
            "\N{BOMB}",
            "\N{COLLISION SYMBOL}",
        )
        for i in ls:
            await m.edit(content=i)
            await asyncio.sleep(1.5)

    @commands.command(name="table", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_table(self, ctx: Context[Parrot]):
        # Thanks `CutieRei#5211`(830248412904947753)
        DEGREE_SIGN = "\N{DEGREE SIGN}"
        WHITE_SQUARE = "\N{WHITE SQUARE}"
        HAND_UP = "\N{BOX DRAWINGS LIGHT ARC UP AND LEFT}"

        TOP = "\N{HANGUL LETTER YU}"
        RIGHT = "\N{HANGUL LETTER YEO}"
        DOWN = "\N{HANGUL LETTER YO}"
        LEFT = "\N{HANGUL LETTER YA}"

        m: discord.Message = await ctx.reply(rf"`(\{DEGREE_SIGN}-{DEGREE_SIGN})\  {TOP}`")
        lst = (
            rf"`(\{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN})\  {TOP}`",
            rf"`(-{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN})-  {TOP}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}  {RIGHT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}    {DOWN}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}      {LEFT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}        {TOP}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}          {RIGHT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}            {DOWN}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}              {LEFT}`",
            rf"`(\{DEGREE_SIGN}-{DEGREE_SIGN})\                 {TOP}`",
        )

        for k in lst:
            await m.edit(content=k)
            await asyncio.sleep(1.5)

    @commands.command(name="funwarn", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_warning(self, ctx: Context[Parrot]):
        msg = await ctx.reply("...")
        IDEA_GRAPHIC_FULL_STOP = "\N{HALFWIDTH IDEOGRAPHIC FULL STOP}"
        IDEA_GRAPHIC = "\N{CJK UNIFIED IDEOGRAPH-76CA}"
        KATAKANA_MIDDLE_DOT = "\N{HALFWIDTH KATAKANA MIDDLE DOT}"
        MACRON = "\N{MACRON}"

        FACE = f"{MACRON}\\({IDEA_GRAPHIC_FULL_STOP}{KATAKANA_MIDDLE_DOT}{IDEA_GRAPHIC}{KATAKANA_MIDDLE_DOT})/{MACRON}"

        ls = (
            "```diff\n- OAD !! WARNING !! SYSTEM OVERL -\n```",
            "```diff\n- D !! WARNING !! SYSTEM OVERLOA -\n```",
            "```diff\n- !! WARNING !! SYSTEM OVERLOAD  -\n```",
            "```diff\n-  WARNING !! SYSTEM OVERLOAD !! -\n```",
            "```diff\n- ARNING !! SYSTEM OVERLOAD !! W -\n```",
            "```diff\n- NING !! SYSTEM OVERLOAD !! WAR -\n```",
            "```diff\n- NG !! SYSTEM OVERLOAD !! WARNI -\n```",
            "```diff\n-  !! SYSTEM OVERLOAD !! WARNING -\n```",
            "```diff\n- ! SYSTEM OVERLOAD !! WARNING ! -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.5 SEC! -\n```",
            "```diff\n- WARNING !! SYSTEM OVERLOAD !!  -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.2 SEC! -\n```",
            "```diff\n- SYSTEM OVERLOAD !! WARNING !!  -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.01 SEC! -\n```",
            f"```diff\n- SHUT-DOWN EXIT ERROR {FACE} -\n```",
            "```diff\n- CTRL + R FOR MANUAL OVERRIDE... -\n```",
        )

        for i in ls:
            await msg.edit(content=i)
            await asyncio.sleep(1.5)

    @commands.group(aliases=("color",), invoke_without_command=True)
    async def colour(
        self,
        ctx: Context[Parrot],
        *,
        colour_input: str = commands.parameter(description="The colour to display.", displayed_name="color"),
    ) -> None:
        """Create an embed that displays colour information.

        If no subcommand is called, a randomly selected colour will be shown.
        """
        try:
            extra_colour = cast(tuple[int, int, int], ImageColor.getrgb(colour_input))
            await self.send_colour_response(ctx, extra_colour)
        except ValueError:
            pass
            # TODO: Handle unknown colour formats

    @colour.command()
    async def rgb(
        self,
        ctx: Context[Parrot],
        red: int = commands.parameter(description="The red value (0-255)."),
        green: int = commands.parameter(description="The green value (0-255)."),
        blue: int = commands.parameter(description="The blue value (0-255)."),
    ) -> None:
        """Create an embed from an RGB input."""
        if any(c not in range(256) for c in (red, green, blue)):
            raise commands.BadArgument(message=f"RGB values can only be from 0 to 255. User input was: `{red, green, blue}`.")
        rgb_tuple = (red, green, blue)
        await self.send_colour_response(ctx, rgb_tuple)

    @colour.command()
    async def hsv(
        self,
        ctx: Context[Parrot],
        hue: int = commands.parameter(description="The hue value (0-360)."),
        saturation: int = commands.parameter(description="The saturation value (0-100)."),
        value: int = commands.parameter(description="The value (brightness) (0-100)."),
    ) -> None:
        """Create an embed from an HSV input."""
        if (hue not in range(361)) or any(c not in range(101) for c in (saturation, value)):
            raise commands.BadArgument(
                message=f"Hue can only be from 0 to 360. Saturation and Value can only be from 0 to 100. User input was: `{hue, saturation, value}`.",
            )
        hsv_tuple = cast(tuple[int, int, int], ImageColor.getrgb(f"hsv({hue}, {saturation}%, {value}%)"))
        await self.send_colour_response(ctx, hsv_tuple)

    @colour.command()
    async def hsl(
        self,
        ctx: Context[Parrot],
        hue: int = commands.parameter(description="The hue value (0-360)."),
        saturation: int = commands.parameter(description="The saturation value (0-100)."),
        lightness: int = commands.parameter(description="The lightness value (0-100)."),
    ) -> None:
        """Create an embed from an HSL input."""
        if (hue not in range(361)) or any(c not in range(101) for c in (saturation, lightness)):
            raise commands.BadArgument(
                message=f"Hue can only be from 0 to 360. Saturation and Lightness can only be from 0 to 100. User input was: `{hue, saturation, lightness}`.",
            )
        hsl_tuple = cast(tuple[int, int, int], ImageColor.getrgb(f"hsl({hue}, {saturation}%, {lightness}%)"))
        await self.send_colour_response(ctx, hsl_tuple)

    @colour.command()
    async def cmyk(
        self,
        ctx: Context[Parrot],
        cyan: int = commands.parameter(description="The cyan value (0-100)."),
        magenta: int = commands.parameter(description="The magenta value (0-100)."),
        yellow: int = commands.parameter(description="The yellow value (0-100)."),
        key: int = commands.parameter(description="The key (black) value (0-100)."),
    ) -> None:
        """Create an embed from a CMYK input."""
        if any(c not in range(101) for c in (cyan, magenta, yellow, key)):
            raise commands.BadArgument(message=f"CMYK values can only be from 0 to 100. User input was: `{cyan, magenta, yellow, key}`.")
        r = round(255 * (1 - (cyan / 100)) * (1 - (key / 100)))
        g = round(255 * (1 - (magenta / 100)) * (1 - (key / 100)))
        b = round(255 * (1 - (yellow / 100)) * (1 - (key / 100)))
        await self.send_colour_response(ctx, (r, g, b))

    @colour.command()
    async def hex(
        self,
        ctx: Context[Parrot],
        hex_code: str = commands.parameter(description="The HEX color code.", displayed_name="hex"),
    ) -> None:
        """Create an embed from a HEX input."""
        if hex_code[0] != "#":
            hex_code = f"#{hex_code}"

        if len(hex_code) not in (4, 5, 7, 9) or any(digit not in string.hexdigits for digit in hex_code[1:]):
            raise commands.BadArgument(
                message=f"Cannot convert `{hex_code}` to a recognizable Hex format. Hex values must be hexadecimal and take the form *#RRGGBB* or *#RGB*.",
            )

        hex_tuple = ImageColor.getrgb(hex_code)
        if len(hex_tuple) == 4:
            hex_tuple = hex_tuple[:-1]  # Colour must be RGB. If RGBA, we remove the alpha value
        await self.send_colour_response(ctx, hex_tuple)

    @colour.command()
    async def name(
        self,
        ctx: Context[Parrot],
        *,
        user_colour_name: str = commands.parameter(description="The name of the colour.", displayed_name="colour name"),
    ) -> None:
        """Create an embed from a name input."""
        hex_colour = self.match_colour_name(user_colour_name)
        if hex_colour is None:
            name_error_embed = discord.Embed(
                title="No colour match found.",
                description=f"No colour found for: `{user_colour_name}`",
                colour=discord.Color.dark_red(),
            )
            await ctx.reply(embed=name_error_embed)
            return
        hex_tuple = ImageColor.getrgb(hex_colour)
        await self.send_colour_response(ctx, hex_tuple)

    @colour.command()
    async def random(self, ctx: Context[Parrot]) -> None:
        """Create an embed from a randomly chosen colour."""
        hex_colour = random.choice(list(color_names.values()))
        hex_tuple = ImageColor.getrgb(f"#{hex_colour}")
        await self.send_colour_response(ctx, hex_tuple)

    @commands.command(name="urbandictionary", aliases=["ud", "urban"])
    async def urban_dictionary(self, ctx: Context[Parrot], *, term: str = commands.parameter(description="The term to define.")) -> discord.Message:
        """Fetch a definition from Urban Dictionary."""
        return await self.get_urban_definition(ctx, term)

    async def get_urban_definition(self, ctx: Context[Parrot], term: str) -> discord.Message:
        """Fetch a definition from Urban Dictionary API."""
        url = f"https://api.urbandictionary.com/v0/define?term={term}"
        pages: list[discord.Embed] = []

        async with self.bot.http_session.get(url) as response:
            if response.status != 200:
                return await ctx.reply("Failed to fetch definition from Urban Dictionary.")

            data = await response.json()
            if not data["list"]:
                return await ctx.reply(f"No definition found for: `{term}`")

            results = data["list"]
            for result in results:
                definition = result["definition"]
                example = result["example"]

                embed = discord.Embed(
                    title=f"Definition of {term}",
                    description=f"{definition}\n\n**Example:**\n{example}",
                )
                pages.append(embed)

        view = PaginationView(author=ctx.author, items=pages)
        message = await view.start(ctx)

        return message

    @commands.command(name="bottomify", aliases=["bottom"])
    async def _bottomify(self, ctx: Context, *, text: Annotated[str, commands.clean_content]):
        """Bottomify your text."""
        text = to_bottom(text)
        if len(text) > 2000:
            await ctx.reply(text[:2000])
        else:
            await ctx.reply(text)

    @commands.command(name="debottomify", aliases=["debottom"])
    async def _debottomify(self, ctx: Context, *, text: Annotated[str, commands.clean_content]):
        """Debottomify your text."""
        text = from_bottom(text)
        if len(text) > 2000:
            await ctx.reply(text[:2000])
        else:
            await ctx.reply(text)

    @commands.command(name="pour", aliases=["pourpuzzle"])
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _pour(self, ctx: Context, *, level: int = 1):
        """Pour puzzle."""
        if level > 50:
            return await ctx.reply("Level must be between 1 and 50")

        view = PourView(ctx, level)
        img_buf = await asyncio.to_thread(view.draw_image)
        embed = discord.Embed(
            title="Pour puzzle",
            description=f"Level: {level}",
        )

        file = discord.File(img_buf, filename="pour_game.png")
        embed.set_image(url="attachment://pour_game.png")

        embed.set_footer(
            text=f"Game played by: {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )
        view.message = await ctx.reply(file=file, embed=embed, view=view)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def uwuify(self, ctx: Context, *, text: Annotated[str, commands.clean_content]):
        """Converts a given `text` into it's uwu equivalent."""
        conversion_func = functools.partial(replace_many, replacements=UWU_WORDS, ignore_case=True, match_case=True)

        converted_text = conversion_func(text)
        converted_text = suppress_links(converted_text)
        # Don't put >>> if only embed present
        if converted_text:
            converted_text = f">>> {converted_text.lstrip('> ')}"
        await ctx.send(content=converted_text)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def quiz(self, ctx: commands.Context[Parrot]):
        """Starts a quiz game."""
        view = QuizConfigLayout(author=ctx.author)
        await ctx.reply(view=view)
        await view.wait()
        url = view.url
        if url is None:
            await ctx.reply("Quiz cancelled.")
            return

        message = await ctx.reply("Fetching quiz questions...")
        async with self.bot.http_session.get(url) as response:
            if response.status != 200:
                await message.edit(content="Failed to fetch quiz questions.")
                return

            data = await response.json()
            response_code = data.get("response_code")
            if response_code != 0:
                await message.edit(content="No questions found for the selected configuration.")
                return

            questions = data.get("results", [])
            if not questions:
                await message.edit(content="No questions found for the selected configuration.")
                return

        await message.edit(content=f"Starting the quiz game... [Fetched {len(questions)} questions]")
        await self.start_quiz_game(ctx, questions)

    async def start_quiz_game(self, ctx: commands.Context[Parrot], questions: list[QuizData]):
        score_board: dict[discord.User | discord.Member, int] = defaultdict(int)

        for index, question in enumerate(questions, start=1):
            correct_answer = question["correct_answer"]
            incorrect_answers = question["incorrect_answers"]

            options = [*incorrect_answers, correct_answer]
            random.shuffle(options)

            description = html.unescape(question["question"])
            options_text = "\n".join(f"- {html.unescape(option)}" for option in options)

            end_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=30)
            relative_time = discord.utils.format_dt(end_time, style="R")

            embed = discord.Embed(
                title=f"Question {index}",
                description=(f"{description}\n\n**Options:**\n{options_text}\n\n-# Time left: {relative_time}"),
            )

            question_message = await ctx.send(embed=embed)

            answered_users: set[int] = set()

            def check(message: discord.Message) -> bool:
                return message.channel == ctx.channel and not message.author.bot and message.author.id not in answered_users

            while False == False in [False]:  # noqa: E712, PLR0133
                try:
                    message = await self.bot.wait_for("message", check=check, timeout=30.0)
                except TimeoutError:
                    await ctx.send(f"Time's up! The correct answer was: **{correct_answer}**")
                    break

                user = message.author
                answered_users.add(user.id)

                answer = message.content.strip()

                similarity = difflib.SequenceMatcher(None, answer.casefold(), correct_answer.casefold()).ratio()

                if similarity >= 0.9:
                    score_board[user] += 10
                    await ctx.send(f"{user.mention} Correct! Your score: {score_board[user]}")

                    embed.set_footer(text=f"{user} answered correctly!")
                    await question_message.edit(embed=embed)
                else:
                    await message.add_reaction("\N{CROSS MARK}")

            if score_board:
                scoreboard_embed = discord.Embed(title="Scoreboard", description="\n".join(f"{user}: {score}" for user, score in score_board.items()))
                await ctx.send(embed=scoreboard_embed)

        winner = None
        for user, score in score_board.items():
            if winner is None or score > score_board[winner]:
                winner = user

        if winner:
            await ctx.send(f"Quiz finished! The winner is {winner.mention} with a score of {score_board[winner]}!")
        else:
            await ctx.send("Quiz finished! No one scored any points.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Fun(bot))
