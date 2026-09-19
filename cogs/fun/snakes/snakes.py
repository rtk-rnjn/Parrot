from __future__ import annotations

import asyncio
import colorsys
import os
import random
import re
import string
import textwrap
from functools import partial
from io import BytesIO
from typing import TYPE_CHECKING, Annotated, TypedDict, cast

from discord import Embed, File, Member, Message, PartialEmoji, Reaction
from discord.ext import commands
from discord.ext.commands import BucketType, bot_has_permissions, group
from PIL import Image, ImageDraw, ImageFont

from core.constants import NEGATIVE_REPLIES as INCORRECT_GUESS
from core.constants import POSITIVE_REPLIES as CORRECT_GUESS

from .converter import Snake
from .utils import (
    PerlinNoiseFactory,
    SnakeAndLaddersGame,
    create_snek_frame,
    frame_to_png_bytes,
    get_resource,
    snakes,
    stages,
)

if TYPE_CHECKING:
    from core import Parrot

SNAKE_COLOR = 0x399600


SYRINGE_EMOJI = "\U0001f489"
PILL_EMOJI = "\U0001f48a"
HOURGLASS_EMOJI = "\u231b"
CROSSBONES_EMOJI = "\u2620"
ALEMBIC_EMOJI = "\u2697"
TICK_EMOJI = "\u2705"
CROSS_EMOJI = "\u274c"
BLANK_EMOJI = "\u26aa"
HOLE_EMOJI = "\u2b1c"
EMPTY_UNICODE = "\u200b"

ANTIDOTE_EMOJI = (
    SYRINGE_EMOJI,
    PILL_EMOJI,
    HOURGLASS_EMOJI,
    CROSSBONES_EMOJI,
    ALEMBIC_EMOJI,
)


ANSWERS_EMOJI = {
    "a": "\U0001f1e6",
    "b": "\U0001f1e7",
    "c": "\U0001f1e8",
    "d": "\U0001f1e9",
}

ANSWERS_EMOJI_REVERSE = {
    "\U0001f1e6": "A",
    "\U0001f1e7": "B",
    "\U0001f1e8": "C",
    "\U0001f1e9": "D",
}


class ImageInfo(TypedDict):
    title: str


class SnakeInfo(TypedDict, total=False):
    title: str
    extract: str
    images: list[ImageInfo]
    fullurl: str
    pageid: int
    error: bool
    image_list: list[str]
    map_list: list[str]
    thumb_list: list[str]
    name: str
    info: str | None


class WikiPage(TypedDict):
    title: str
    extract: str
    images: list[ImageInfo]
    fullurl: str
    pageid: int


class WikiQuery(TypedDict):
    pages: dict[str, WikiPage]


class WikiResponse(TypedDict):
    query: WikiQuery


class SearchResult(TypedDict):
    pageid: int


class SearchQuery(TypedDict):
    search: list[SearchResult]


class SearchResponse(TypedDict):
    query: SearchQuery


ZEN = """
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
"""

WIKI_API_ENDPOINT = "https://en.wikipedia.org/w/api.php?"


CARD = {
    "top": Image.open("assets/snakes/snake_cards/card_top.png"),
    "frame": Image.open("assets/snakes/snake_cards/card_frame.png"),
    "bottom": Image.open("assets/snakes/snake_cards/card_bottom.png"),
    "backs": [Image.open(f"assets/snakes/snake_cards/backs/{file}") for file in os.listdir("assets/snakes/snake_cards/backs")],
    "font": ImageFont.truetype("assets/snakes/snake_cards/expressway.ttf", 20),
}


async def invoke_help_command(ctx: commands.Context[Parrot]) -> None:
    """Invoke the help command or default help command if help extensions is not loaded."""
    await ctx.send_help(ctx.command)


class Snakes(commands.Cog):
    wiki_brief = re.compile(r"(.*?)(=+ (.*?) =+)", flags=re.DOTALL)
    valid_image_extensions = ("gif", "png", "jpeg", "jpg", "webp")

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self.active_sal = {}
        self.snake_names = get_resource("snake_names")
        self.snake_idioms = get_resource("snake_idioms")
        self.snake_quizzes = get_resource("snake_quiz")
        self.snake_facts = get_resource("snake_facts")
        self.num_movie_pages = None

    @staticmethod
    def _beautiful_pastel(hue: float) -> int:
        """Returns random bright pastels."""
        light = random.uniform(0.7, 0.85)
        saturation = 1

        rgb = colorsys.hls_to_rgb(hue, light, saturation)
        hex_rgb = ""

        for part in rgb:
            value = int(part * 0xFF)
            hex_rgb += f"{value:02x}"

        return int(hex_rgb, 16)

    @staticmethod
    def _generate_card(buffer: BytesIO, content: dict) -> BytesIO:
        """Generate a card from snake information.
        Written by juan and Someone during the first code jam.
        """
        snake = Image.open(buffer)

        icon_width = 347
        icon_height = int((icon_width / snake.width) * snake.height)
        frame_copies = icon_height // CARD["frame"].height + 1
        snake.thumbnail((icon_width, icon_height))

        main_height = icon_height + CARD["top"].height + CARD["bottom"].height
        main_width = CARD["frame"].width

        foreground = Image.new("RGBA", (main_width, main_height), (0, 0, 0, 0))
        foreground.paste(CARD["top"], (0, 0))

        for offset in range(frame_copies):
            position = (0, CARD["top"].height + offset * CARD["frame"].height)
            foreground.paste(CARD["frame"], position)

        foreground.paste(snake, (36, CARD["top"].height))
        foreground.paste(CARD["bottom"], (0, CARD["top"].height + icon_height))

        back = random.choice(CARD["backs"])
        back_copies = main_height // back.height + 1
        full_image = Image.new("RGBA", (main_width, main_height), (0, 0, 0, 0))

        for offset in range(back_copies):
            full_image.paste(back, (16, 16 + offset * back.height))

        full_image.paste(foreground, (0, 0), foreground)

        description = ".".join(content["info"].split(".")[:2]) + "."

        margin = 36
        offset = CARD["top"].height + icon_height + margin

        rectangle = Image.new("RGBA", (main_width, main_height), (0, 0, 0, 0))

        rect = ImageDraw.Draw(rectangle)
        rect.rectangle(
            (margin, offset, main_width - margin, main_height - margin),
            fill=(63, 63, 63, 128),
        )

        full_image.paste(rectangle, (0, 0), mask=rectangle)

        draw = ImageDraw.Draw(full_image)
        for line in textwrap.wrap(description, 36):
            draw.text((margin + 4, offset), line, font=CARD["font"])
            offset += CARD["font"].getsize(line)[1]

        buffer = BytesIO()
        full_image.save(buffer, "PNG")
        buffer.seek(0)

        return buffer

    @staticmethod
    def _snakify(message: str) -> str:
        """Sssnakifffiesss a sstring."""

        simple_fricatives = [
            "f",
            "s",
            "z",
            "h",
            "F",
            "S",
            "Z",
            "H",
        ]
        complex_fricatives = ["th", "sh", "Th", "Sh"]

        for letter in simple_fricatives:
            if letter.islower():
                message = message.replace(letter, letter * random.randint(2, 4))
            else:
                message = message.replace(letter, (letter * random.randint(2, 4)).title())

        for fricative in complex_fricatives:
            message = message.replace(fricative, fricative[0] + fricative[1] * random.randint(2, 4))

        return message

    async def _fetch(self, url: str, params: dict | None = None) -> dict:
        """Asynchronous web request helper method."""
        if params is None:
            params = {}

        async with asyncio.timeout(10):
            async with self.bot.http_session.get(url, params=params) as response:
                return await response.json()

    def _get_random_long_message(self, messages: list[str], retries: int = 10) -> str:
        """Fetch a message that's at least 3 words long, if possible to do so in retries attempts.
        Else, just return whatever the last message is.
        """
        long_message = random.choice(messages)
        if len(long_message.split()) < 3 and retries > 0:
            return self._get_random_long_message(messages, retries=retries - 1)

        return long_message

    async def _get_snek(self, name: str) -> SnakeInfo | None:
        """Fetch all available data from a Wikipedia article about a snake."""
        snake_info: SnakeInfo = {
            "image_list": [],
            "map_list": [],
            "thumb_list": [],
            "name": name,
        }

        params = {
            "format": "json",
            "action": "query",
            "list": "search",
            "srsearch": name,
            "utf8": "",
            "srlimit": "1",
        }

        data = await self._fetch(WIKI_API_ENDPOINT, params=params)
        search_data = cast(SearchResponse, data)

        try:
            pageid = search_data["query"]["search"][0]["pageid"]
        except KeyError:
            pageid = 41118
        except IndexError:
            return None

        params = {
            "format": "json",
            "action": "query",
            "prop": "extracts|images|info",
            "exlimit": "max",
            "explaintext": "",
            "inprop": "url",
            "pageids": pageid,
        }

        data = await self._fetch(WIKI_API_ENDPOINT, params=params)
        wiki_data = cast(WikiResponse, data)

        try:
            page = wiki_data["query"]["pages"][str(pageid)]

            snake_info.update(
                {
                    "title": page["title"],
                    "extract": page["extract"],
                    "images": page["images"],
                    "fullurl": page["fullurl"],
                    "pageid": page["pageid"],
                },
            )
        except KeyError:
            snake_info["error"] = True
            return snake_info

        image_list = snake_info["image_list"]
        map_list = snake_info["map_list"]
        thumb_list = snake_info["thumb_list"]

        image_url = "https://commons.wikimedia.org/wiki/Special:FilePath/"

        banned = (
            "Commons-logo.svg",
            "Red%20Pencil%20Icon.png",
            "distribution",
            "The%20Death%20of%20Cleopatra%20arthur.jpg",
            "Head%20of%20holotype",
            "locator",
            "Woma.png",
            "-map.",
            ".svg",
            "ange.",
            "Adder%20(PSF).png",
        )

        for image in snake_info.get("images", []):
            _, _, filename = image["title"].partition(":")
            filename = filename.replace(" ", "%20")

            if filename.startswith("Map"):
                map_list.append(f"{image_url}{filename}")
            elif all(item not in filename for item in banned):
                image_list.append(f"{image_url}{filename}")
                thumb_list.append(f"{image_url}{filename}?width=100")

        extract = snake_info.get("extract", "")
        match = self.wiki_brief.match(extract)
        info = match.group(1) if match else None

        snake_info["info"] = info.replace("\n", "\n\n") if info else None

        return snake_info

    async def _get_snake_name(self) -> dict[str, str]:
        """Gets a random snake name."""
        return random.choice(self.snake_names)

    async def _validate_answer(self, ctx: commands.Context[Parrot], message: Message, answer: str, options: dict[str, str]) -> None:
        """Validate the answer using a reaction event loop."""

        def predicate(reaction: Reaction, user: Member) -> bool:
            """Test if the the answer is valid and can be evaluated."""
            return reaction.message.id == message.id and user == ctx.author and str(reaction.emoji) in ANSWERS_EMOJI.values()

        for emoji in ANSWERS_EMOJI.values():
            await message.add_reaction(emoji)

        try:
            reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=45.0, check=predicate)
        except TimeoutError:
            await ctx.send(f"You took too long. The correct answer was **{options[answer]}**.")
            await message.clear_reactions()
            return

        if str(reaction.emoji) == ANSWERS_EMOJI[answer]:
            await ctx.send(f"{random.choice(CORRECT_GUESS)} The correct answer was **{options[answer]}**.")
        else:
            await ctx.send(f"{random.choice(INCORRECT_GUESS)} The correct answer was **{options[answer]}**.")

        await message.clear_reactions()

    @group(name="snakes", aliases=("snake",), invoke_without_command=True)
    @bot_has_permissions(manage_messages=True)
    async def snakes_group(self, ctx: commands.Context[Parrot]) -> None:
        """Commands from our first code jam."""
        if not ctx.invoked_subcommand:
            await invoke_help_command(ctx)

    @bot_has_permissions(manage_messages=True)
    @snakes_group.command(name="antidote")
    @commands.max_concurrency(1, per=BucketType.channel)
    async def antidote_command(self, ctx: commands.Context[Parrot]) -> None:  # noqa: PLR0915
        """Antidote! Can you create the antivenom before the patient dies?
        Rules:  You have 4 ingredients for each antidote, you only have 10 attempts
                Once you synthesize the antidote, you will be presented with 4 markers
                Tick: This means you have a CORRECT ingredient in the CORRECT position
                Circle: This means you have a CORRECT ingredient in the WRONG position
                Cross: This means you have a WRONG ingredient in the WRONG position
        Info:   The game automatically ends after 5 minutes inactivity.
                You should only use each ingredient once.
        This game was created by Lord Bisk and Runew0lf.
        """

        def predicate(reaction_: Reaction, user_: Member) -> bool:
            """Make sure that this reaction is what we want to operate on."""
            return all(
                (
                    reaction_.message.id == board_id.id,
                    reaction_.emoji in ANTIDOTE_EMOJI,
                    user_.id != self.bot.user.id,
                    user_.id == ctx.author.id,
                ),
            )

        antidote_tries = 0
        antidote_guess_count = 0
        antidote_guess_list = []
        guess_result = []
        board = []
        page_guess_list = []
        page_result_list = []
        win = False

        antidote_embed = Embed(color=SNAKE_COLOR, title="Antidote")
        antidote_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        antidote_answer = list(ANTIDOTE_EMOJI)
        random.shuffle(antidote_answer)
        antidote_answer.pop()

        for i in range(10):
            page_guess_list.append(f"{HOLE_EMOJI} {HOLE_EMOJI} {HOLE_EMOJI} {HOLE_EMOJI}")
            page_result_list.append(f"{CROSS_EMOJI} {CROSS_EMOJI} {CROSS_EMOJI} {CROSS_EMOJI}")
            board.append(f"`{i + 1:02d}` {page_guess_list[i]} - {page_result_list[i]}")
            board.append(EMPTY_UNICODE)
        antidote_embed.add_field(name="10 guesses remaining", value="\n".join(board))
        board_id = await ctx.send(embed=antidote_embed)

        for emoji in ANTIDOTE_EMOJI:
            await board_id.add_reaction(emoji)

        while not win and antidote_tries < 10:
            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", timeout=300, check=predicate)
            except TimeoutError:
                break

            if antidote_tries < 10 and antidote_guess_count < 4:
                if reaction.emoji in ANTIDOTE_EMOJI:
                    antidote_guess_list.append(reaction.emoji)
                    antidote_guess_count += 1

                if antidote_guess_count == 4:
                    antidote_guess_count = 0
                    page_guess_list[antidote_tries] = " ".join(antidote_guess_list)

                    for i, item in enumerate(antidote_answer):
                        if antidote_guess_list[i] == item:
                            guess_result.append(TICK_EMOJI)
                        elif antidote_guess_list[i] in antidote_answer:
                            guess_result.append(BLANK_EMOJI)
                        else:
                            guess_result.append(CROSS_EMOJI)
                    guess_result.sort()
                    page_result_list[antidote_tries] = " ".join(guess_result)

                    board = []
                    for i in range(10):
                        board.append(f"`{i + 1:02d}` {page_guess_list[i]} - {page_result_list[i]}")
                        board.append(EMPTY_UNICODE)

                    for emoji in antidote_guess_list:
                        await board_id.remove_reaction(emoji, user)

                    if antidote_guess_list == antidote_answer:
                        win = True

                    antidote_tries += 1
                    guess_result = []
                    antidote_guess_list = []

                    antidote_embed.clear_fields()
                    antidote_embed.add_field(
                        name=f"{10 - antidote_tries} guesses remaining",
                        value="\n".join(board),
                    )

                    await board_id.edit(embed=antidote_embed)

        if win:
            antidote_embed = Embed(color=SNAKE_COLOR, title="Antidote")
            antidote_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            antidote_embed.set_image(url="https://i.makeagif.com/media/7-12-2015/Cj1pts.gif")
            antidote_embed.add_field(
                name="You have created the snake antidote!",
                value=f"The solution was: {' '.join(antidote_answer)}\nYou had {10 - antidote_tries} tries remaining.",
            )
            await board_id.edit(embed=antidote_embed)
        else:
            antidote_embed = Embed(color=SNAKE_COLOR, title="Antidote")
            antidote_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            antidote_embed.set_image(url="https://media.giphy.com/media/ceeN6U57leAhi/giphy.gif")
            antidote_embed.add_field(
                name=EMPTY_UNICODE,
                value=(f"Sorry you didnt make the antidote in time.\nThe formula was {' '.join(antidote_answer)}"),
            )
            await board_id.edit(embed=antidote_embed)

        await board_id.clear_reactions()

    @snakes_group.command(name="draw")
    async def draw_command(self, ctx: commands.Context[Parrot]) -> None:
        """Draws a random snek using Perlin noise.
        Written by Momo and kel.
        Modified by juan and lemon.
        """
        async with ctx.typing():
            width = random.randint(6, 10)
            length = random.randint(15, 22)
            random_hue = random.random()
            snek_color = self._beautiful_pastel(random_hue)
            text_color = self._beautiful_pastel((random_hue + 0.5) % 1)
            bg_color = (
                random.randint(32, 50),
                random.randint(32, 50),
                random.randint(50, 70),
            )

            text = random.choice(self.snake_idioms)["idiom"]
            factory = PerlinNoiseFactory(dimension=1, octaves=2)
            image_frame = create_snek_frame(
                factory,
                snake_width=width,
                snake_length=length,
                snake_color=snek_color,
                text=text,
                text_color=text_color,
                bg_color=bg_color,
            )
            png_bytes = frame_to_png_bytes(image_frame)
            file = File(png_bytes, filename="snek.png")
            await ctx.send(file=file)

    @snakes_group.command(name="get")
    @bot_has_permissions(manage_messages=True)
    @commands.max_concurrency(1, per=BucketType.channel)
    async def get_command(self, ctx: commands.Context[Parrot], *, name: Annotated[str | None, Snake] = None) -> None:
        """Fetches information about a snake from Wikipedia.
        Created by Ava and eivl.
        """
        async with ctx.typing():
            if name is None:
                name = await Snake.random()

            data = await self._get_snek(name)
            if data is None:
                await ctx.send("Could not find any information about that snake.")
                return

            if data.get("error"):
                await ctx.send("Could not fetch data from Wikipedia.")
                return

            description = data.get("info") or "No description available."

            if len(description) > 1000:
                description = description[:1000]
                last_newline = description.rfind("\n")
                if last_newline > 0:
                    description = description[:last_newline]

            if "fullurl" in data:
                description = description.strip("\n")
                description += f"\n\nRead more on [Wikipedia]({data['fullurl']})"

            embed = Embed(
                title=data.get("title", data.get("name")),
                description=description,
                colour=0x59982F,
            )

            emoji = "https://emojipedia-us.s3.amazonaws.com/thumbs/60/google/3/snake_1f40d.png"

            _iter = (url for url in data["image_list"] if url.endswith(self.valid_image_extensions))
            image = next(_iter, emoji)

            embed.set_image(url=image)

            await ctx.send(embed=embed)

    @snakes_group.command(name="guess", aliases=("identify",))
    @commands.max_concurrency(1, per=BucketType.channel)
    async def guess_command(self, ctx: commands.Context[Parrot]) -> None:
        """Snake identifying game.
        Made by Ava and eivl.
        Modified by lemon.
        """
        async with ctx.typing():
            image = None

            while image is None:
                snakes = [await Snake.random() for _ in range(4)]
                snake = random.choice(snakes)
                answer = "abcd"[snakes.index(snake)]

                data = await self._get_snek(snake)

                _iter = (url for url in data["image_list"] if url.endswith(self.valid_image_extensions))
                image = next(_iter, None)

            embed = Embed(
                title="Which of the following is the snake in the image?",
                description="\n".join(f"{'ABCD'[snakes.index(snake)]}: {snake}" for snake in snakes),
                colour=SNAKE_COLOR,
            )
            embed.set_image(url=image)

        guess = await ctx.send(embed=embed)
        options = {f"{'abcd'[snakes.index(snake)]}": snake for snake in snakes}
        await self._validate_answer(ctx, guess, answer, options)

    @snakes_group.command(name="hatch")
    async def hatch_command(self, ctx: commands.Context[Parrot]) -> None:
        """Hatches your personal snake.
        Written by Momo and kel.
        """

        snake_name = random.choice(list(snakes.keys()))
        snake_image = snakes[snake_name]

        message = await ctx.send(embed=Embed(description="Hatching your snake :snake:..."))
        await asyncio.sleep(1)

        for stage in stages:
            hatch_embed = Embed(description=stage)
            await message.edit(embed=hatch_embed)
            await asyncio.sleep(1)
        await asyncio.sleep(1)
        await message.delete()

        my_snake_embed = Embed(description=f":tada: Congrats! You hatched: **{snake_name}**")
        my_snake_embed.set_thumbnail(url=snake_image)
        my_snake_embed.set_footer(text=f" Owner: {ctx.author}")

        await ctx.send(embed=my_snake_embed)

    @snakes_group.command(name="quiz")
    @commands.max_concurrency(1, per=BucketType.channel)
    async def quiz_command(self, ctx: commands.Context[Parrot]) -> None:
        """Asks a snake-related question in the chat and validates the user's guess.
        This was created by Mushy and Cardium,
        and modified by Urthas and lemon.
        """

        question = random.choice(self.snake_quizzes)
        answer = question["answerkey"]
        options = {key: question["options"][key] for key in ANSWERS_EMOJI}

        embed = Embed(
            color=SNAKE_COLOR,
            title=question["question"],
            description="\n".join([f"**{key.upper()}**: {answer}" for key, answer in options.items()]),
        )

        quiz = await ctx.send(embed=embed)
        await self._validate_answer(ctx, quiz, answer, options)

    @snakes_group.command(name="name", aliases=("name_gen",))
    async def name_command(self, ctx: commands.Context[Parrot], *, name: str = None) -> None:
        """Snakifies a username.
        Slices the users name at the last vowel (or second last if the name
        ends with a vowel), and then combines it with a random snake name,
        which is sliced at the first vowel (or second if the name starts with
        a vowel).
        If the name contains no vowels, it just appends the snakename
        to the end of the name.

        Examples
        --------
            lemon + anaconda = lemoconda
            krzsn + anaconda = krzsnconda
            gdude + anaconda = gduconda
            aperture + anaconda = apertuconda
            lucy + python = luthon
            joseph + taipan = joseipan
        This was written by Iceman, and modified for inclusion into the bot by lemon.
        """
        snake_name = await self._get_snake_name()
        snake_name = snake_name["name"]
        snake_prefix = ""

        if " " in snake_name:
            snake_prefix = " ".join(snake_name.split()[:-1])
            snake_name = snake_name.split()[-1]

        user_name = name or ctx.author.display_name

        user_slice_index = len(user_name)
        for index, char in enumerate(reversed(user_name)):
            if index == 0:
                continue
            if char.lower() in "aeiouy":
                user_slice_index -= index
                break

        snake_slice_index = 0
        for index, char in enumerate(snake_name):
            if index == 0:
                continue
            if char.lower() in "aeiouy":
                snake_slice_index = index + 1
                break

        snake_name = snake_name[snake_slice_index:]
        user_name = user_name[:user_slice_index]
        result = f"{snake_prefix} {user_name}{snake_name}"
        result = string.capwords(result)

        embed = Embed(
            title="Snake name",
            description=f"Your snake-name is **{result}**",
            color=SNAKE_COLOR,
        )

        await ctx.send(embed=embed)

    @snakes_group.command(name="sal")
    @commands.max_concurrency(1, per=BucketType.channel)
    async def sal_command(self, ctx: commands.Context[Parrot]) -> None:
        """Play a game of Snakes and Ladders.
        Written by Momo and kel.
        Modified by lemon.
        """

        if ctx.channel in self.active_sal:
            await ctx.send(f"{ctx.author.mention} A game is already in progress in this channel.")
            return

        game = SnakeAndLaddersGame(snakes=self, context=ctx)
        self.active_sal[ctx.channel] = game

        await game.open_game()

    @snakes_group.command(name="card")
    async def card_command(self, ctx: commands.Context[Parrot], *, name: Annotated[str | None, Snake] = None) -> None:
        """Create an interesting little card from a snake.
        Created by juan and Someone during the first code jam.
        """

        if name is None:
            name_obj = await self._get_snake_name()
            name = name_obj["scientific"]
            content = await self._get_snek(name)

        elif isinstance(name, dict):
            content = name

        else:
            content = await self._get_snek(name)

        async with ctx.typing():
            stream = BytesIO()
            async with asyncio.timeout(10):
                async with self.bot.http_session.get(content["image_list"][0]) as response:
                    stream.write(await response.read())

            stream.seek(0)

            func = partial(self._generate_card, stream, content)
            final_buffer = await self.bot.loop.run_in_executor(None, func)

        await ctx.send(
            f"A wild {content['name'].title()} appears!",
            file=File(final_buffer, filename=content["name"].replace(" ", "") + ".png"),
        )

    @snakes_group.command(name="fact")
    async def fact_command(self, ctx: commands.Context[Parrot]) -> None:
        """Gets a snake-related fact.
        Written by Andrew and Prithaj.
        Modified by lemon.
        """
        question = random.choice(self.snake_facts)["fact"]
        embed = Embed(title="Snake fact", color=SNAKE_COLOR, description=question)
        await ctx.send(embed=embed)

    @snakes_group.command(name="snakify")
    async def snakify_command(self, ctx: commands.Context[Parrot], *, message: str) -> None:
        """How would I talk if I were a snake?
        If `message` is passed, the bot will snakify the message.
        Otherwise, a random message from the user's history is snakified.
        Written by Momo and kel.
        Modified by lemon.
        """
        embed = Embed()
        user = ctx.author

        embed.set_author(
            name=f"{user}",
            icon_url=user.display_avatar.url,
        )
        embed.description = f"*{self._snakify(message)}*"

        await ctx.send(embed=embed)

    @snakes_group.command(name="zen")
    async def zen_command(self, ctx: commands.Context[Parrot]) -> None:
        """Gets a random quote from the Zen of Python, except as if spoken by a snake.
        Written by Prithaj and Andrew.
        Modified by lemon.
        """
        embed = Embed(title="Zzzen of Pythhon", color=SNAKE_COLOR)

        zen_quote = random.choice(ZEN.splitlines())
        zen_quote = self._snakify(zen_quote)

        embed.description = zen_quote
        await ctx.send(embed=embed)
