from __future__ import annotations

import asyncio
import colorsys
import io
import itertools
import json
import logging
import math
import random
import string
from typing import TYPE_CHECKING, Annotated, Any, cast

import discord
from colorama import Fore
from discord.ext import commands
from discord.ext.commands import Context
from PIL import Image, ImageColor
from rapidfuzz.process import extractOne as rf_extract_one

from core.utils import PaginationView

if TYPE_CHECKING:
    from core.bot import Parrot

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
            await asyncio.sleep(1)

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
            await asyncio.sleep(1)

    @commands.command(name="boom", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_boom(self, ctx: Context[Parrot]):
        """Booms a message!."""
        m = await ctx.reply("THIS MESSAGE WILL SELFDESTRUCT IN 5")
        await asyncio.sleep(1)
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
            await asyncio.sleep(1)

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
            await asyncio.sleep(0.5)

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
            await asyncio.sleep(1)

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
        pages: list[str] = []

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

                pages.append(f"**Definition of {term}:**\n{definition}\n\n**Example:**\n{example}")

        view = PaginationView(pages)
        await view.start(ctx)

        return view.message

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


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Fun(bot))
