from __future__ import annotations

import asyncio
import logging
import random
import re
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord.utils import _from_json as loads
from PIL import Image

if TYPE_CHECKING:
    from core.bot import Parrot

    type Context = commands.Context[Parrot]

ALL_VIDS: dict = loads(Path(r"assets/easter/april_fools_vids.json").read_text("utf-8"))
BUNNY_NAMES: dict = loads(Path(r"assets/easter/bunny_names.json").read_text("utf8"))
RIDDLE_QUESTIONS: dict = loads(Path(r"assets/easter/easter_riddle.json").read_text("utf8"))
EGG_FACTS: dict = loads(Path(r"assets/easter/easter_egg_facts.json").read_text("utf8"))
EGGHEAD_QUESTIONS: dict = loads(Path(r"assets/easter/egghead_questions.json").read_text("utf8"))
traditions: dict = loads(Path(r"assets/easter/traditions.json").read_text("utf8"))

TIMELIMIT = 10
HTML_COLOURS: dict = loads(Path(r"assets/html_colours.json").read_text("utf8"))
XKCD_COLOURS: dict = loads(Path(r"assets/xkcd_colours.json").read_text("utf8"))

COLOURS = [
    (255, 0, 0, 255),
    (255, 128, 0, 255),
    (255, 255, 0, 255),
    (0, 255, 0, 255),
    (0, 255, 255, 255),
    (0, 0, 255, 255),
    (255, 0, 255, 255),
    (128, 0, 128, 255),
]  # Colours to be replaced - Red, Orange, Yellow, Green, Light Blue, Dark Blue, Pink, Purple

IRREPLACEABLE = [
    (0, 0, 0, 0),
    (0, 0, 0, 255),
]  # Colours that are meant to stay the same - Transparent and Black

EMOJIS = [
    "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Z}",
]  # ITS ABCDEFGHIJKLMNOPQRSTUVWXYZ

_log = logging.getLogger("bot.cogs.fun.easter")


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


class Easter(commands.Cog, command_attrs={"hidden": True}):
    """A cog for April."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.winners: set[str] = set()
        self.correct = ""
        self.current_channel = None
        self.quiz_messages: dict[int, list[str]] = {}

        _log.info("Cog loaded: %s", self.__class__.__name__)

    @staticmethod
    def replace_invalid(colour: str) -> int | None:
        """Attempts to match with HTML or XKCD colour names, returning the int value."""
        with suppress(KeyError):
            return int(HTML_COLOURS[colour], 16)
        with suppress(KeyError):
            return int(XKCD_COLOURS[colour], 16)
        return None

    @commands.command(name="fool")
    async def april_fools(self, ctx: Context) -> None:
        """Get a random April Fools' video from Youtube."""
        video = random.choice(ALL_VIDS)

        channel, url = video["channel"], video["url"]

        await ctx.send(f"Check out this April Fools' video by {channel}.\n\n{url}")

    @staticmethod
    def find_separators(displayname: str) -> list[str] | None:
        """Check if Discord name contains spaces so we can bunnify an individual word in the name."""
        new_name = re.split(r"[_.\s]", displayname)
        return new_name if displayname not in new_name else None

    @staticmethod
    def find_vowels(displayname: str) -> str | None:
        """Finds vowels in the user's display name.
        If the Discord name contains a vowel and the letter y, it will match one or more of these patterns.
        Only the most recently matched pattern will apply the changes.
        """
        expressions = [
            ("a.+y", "patchy"),
            ("e.+y", "ears"),
            ("i.+y", "ditsy"),
            ("o.+y", "oofy"),
            ("u.+y", "uffy"),
        ]

        for exp, vowel_sub in expressions:
            new_name = re.sub(exp, vowel_sub, displayname)
            if new_name != displayname:
                return new_name
        return None

    @staticmethod
    def append_name(displayname: str) -> str:
        """Adds a suffix to the end of the Discord name."""
        extensions = ["foot", "ear", "nose", "tail"]
        suffix = random.choice(extensions)
        return displayname + suffix

    @commands.command()
    async def bunnyname(self, ctx: Context) -> None:
        """Picks a random bunny name from a JSON file."""
        await ctx.send(random.choice(BUNNY_NAMES["names"]))

    @commands.command()
    async def bunnifyme(self, ctx: Context) -> None:
        """Gets your Discord username and bunnifies it."""
        username = ctx.author.display_name

        # If name contains spaces or other separators, get the individual words to randomly bunnify
        spaces_in_name = self.find_separators(username)

        # If name contains vowels, see if it matches any of the patterns in this function
        # If there are matches, the bunnified name is returned.
        vowels_in_name = self.find_vowels(username)

        # Default if the checks above return None
        unmatched_name = self.append_name(username)

        if spaces_in_name is not None:
            replacements = [
                "Cotton",
                "Fluff",
                "FloofBounce",
                "Snuffle",
                "Nibble",
                "Cuddle",
                "Velvetpaw",
                "Carrot",
            ]
            word_to_replace = random.choice(spaces_in_name)
            substitute = random.choice(replacements)
            bunnified_name = username.replace(word_to_replace, substitute)
        elif vowels_in_name is not None:
            bunnified_name = vowels_in_name
        elif unmatched_name:
            bunnified_name = unmatched_name

        await ctx.send(bunnified_name)

    @commands.command(aliases=("riddlemethis", "riddleme"))
    async def riddle(self, ctx: Context) -> None:
        """Gives a random riddle, then provides 2 hints at certain intervals before revealing the answer.
        The duration of the hint interval can be configured by changing the TIMELIMIT constant in this file.
        """
        if self.current_channel:
            await ctx.send(f"A riddle is already being solved in {self.current_channel.mention}!")
            return

        self.current_channel = ctx.channel

        random_question = random.choice(RIDDLE_QUESTIONS)
        question = random_question["question"]
        hints = random_question["riddles"]
        self.correct = random_question["correct_answer"]

        description = f"You have {TIMELIMIT} seconds before the first hint."

        riddle_embed = discord.Embed(title=question, description=description, colour=0xCF84E0)

        await ctx.send(embed=riddle_embed)
        await asyncio.sleep(TIMELIMIT)

        hint_embed = discord.Embed(title=f"Here's a hint: {hints[0]}!", colour=0xCF84E0)

        await ctx.send(embed=hint_embed)
        await asyncio.sleep(TIMELIMIT)

        hint_embed = discord.Embed(title=f"Here's a hint: {hints[1]}!", colour=0xCF84E0)

        await ctx.send(embed=hint_embed)
        await asyncio.sleep(TIMELIMIT)

        if self.winners:
            win_list = " ".join(self.winners)
            content = f"Well done {win_list} for getting it right!"
        else:
            content = "Nobody got it right..."

        answer_embed = discord.Embed(title=f"The answer is: {self.correct}!", colour=0xCF84E0)

        await ctx.send(content, embed=answer_embed)

        self.winners.clear()
        self.current_channel = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        """If a non-bot user enters a correct answer, their username gets added to self.winners."""
        if self.current_channel != message.channel:
            return

        if self.bot.user == message.author:
            return

        if message.content.lower() == self.correct.lower():
            self.winners.add(message.author.mention)

    @commands.command(aliases=("decorateegg",))
    async def eggdecorate(
        self,
        ctx: Context,
        *colors: discord.Colour | str,
    ) -> Image.Image | None:
        """Picks a random egg design and decorates it using the given colours.
        Colours are split by spaces, unless you wrap the colour name in double quotes.
        Discord colour names, HTML colour names, XKCD colour names and hex values are accepted.
        """
        if len(colors) < 2:
            await ctx.send("You must include at least 2 colours!")
            return None

        invalid_colours = []
        colours = list(colors)

        for colour_index, colour in enumerate(colours):
            if isinstance(colour, discord.Colour):
                continue

            colour_value = self.replace_invalid(colour)
            if colour_value is not None:
                colours[colour_index] = discord.Colour(colour_value)
            else:
                invalid_colours.append(suppress_links(colour))

        if len(invalid_colours) > 1:
            await ctx.send(
                f"Sorry, I don't know these colours: {' '.join(invalid_colours)}",
            )
            return None

        if len(invalid_colours) == 1:
            await ctx.send(f"Sorry, I don't know the colour {invalid_colours[0]}!")
            return None

        async with ctx.typing():
            # Expand list to 8 colours
            colour_count = len(colours)
            if colour_count < 8:
                repeat_count, remainder = divmod(8, colour_count)
                colours = colours * repeat_count + colours[:remainder]

            design_number = random.randint(1, 6)
            image = Image.open(
                Path(f"assets/easter/easter_eggs/design{design_number}.png"),
            )
            pixel_data = list(image.getdata())

            replaceable_colours = {pixel for pixel in pixel_data if pixel not in IRREPLACEABLE}
            replaceable_colours = sorted(
                replaceable_colours,
                key=COLOURS.index,
            )

            colour_replacements = {colour: colours[colour_index] for colour_index, colour in enumerate(replaceable_colours)}

            recoloured_data = []
            for pixel in pixel_data:
                if pixel in colour_replacements:
                    recoloured_data.append(
                        (*colour_replacements[pixel].to_rgb(), 255),
                    )
                    # Also ensures that the alpha channel has a value
                else:
                    recoloured_data.append(pixel)

            recoloured_image = Image.new(image.mode, image.size)
            recoloured_image.putdata(recoloured_data)

            image_buffer = BytesIO()
            recoloured_image.save(image_buffer, format="PNG")
            image_buffer.seek(0)

            file = discord.File(image_buffer, filename="egg.png")
            embed = discord.Embed(
                title="Your Colourful Easter Egg",
                description="Here is your pretty little egg. Hope you like it!",
            )
            embed.set_image(url="attachment://egg.png")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )

        await ctx.send(file=file, embed=embed)
        return recoloured_image

    @commands.command(name="eggfact", aliases=("efact",))
    async def easter_facts(self, ctx: Context) -> None:
        """Get easter egg facts."""
        embed = self.make_embed()
        await ctx.send(embed=embed)

    @staticmethod
    def make_embed() -> discord.Embed:
        """Makes a nice embed for the message to be sent."""
        return discord.Embed(
            colour=discord.Color.red(),
            title="Easter Egg Fact",
            description=random.choice(EGG_FACTS),
        )

    @commands.command(aliases=("eggheadquiz", "easterquiz"))
    async def eggquiz(self, ctx: Context) -> None:
        """Gives a random quiz question, waits 30 seconds and then outputs the answer.
        Also informs of the percentages and votes of each option.
        """
        random_question = random.choice(EGGHEAD_QUESTIONS)
        question, answers = random_question["question"], random_question["answers"]
        answers = [(EMOJIS[i], a) for i, a in enumerate(answers)]
        correct = EMOJIS[random_question["correct_answer"]]

        valid_emojis = [emoji for emoji, _ in answers]

        description = f"You have {TIMELIMIT} seconds to vote.\n\n"
        description += "\n".join([f"{emoji} -> **{answer}**" for emoji, answer in answers])

        q_embed = discord.Embed(title=question, description=description, colour=discord.Color.pink())

        msg: discord.Message = await ctx.send(embed=q_embed)
        for emoji in valid_emojis:
            await msg.add_reaction(emoji)

        self.quiz_messages[msg.id] = valid_emojis

        await asyncio.sleep(TIMELIMIT)

        del self.quiz_messages[msg.id]

        msg: discord.Message = await self.bot.get_or_fetch_message(msg.channel, msg.id)

        total_no = sum(r.count for r in msg.reactions) - len(valid_emojis)  # - bot's reactions

        if total_no == 0:
            return await msg.delete()  # To avoid ZeroDivisionError if nobody reacts

        results = ["**VOTES:**"]
        for emoji, _ in answers:
            num = [r.count for r in msg.reactions if str(r.emoji) == emoji][0] - 1
            percent = round(100 * num / total_no)
            s = "" if num == 1 else "s"
            string = f"{emoji} - {num} vote{s} ({percent}%)"
            results.append(string)

        # mentions = " ".join(
        #     [
        #         u.mention
        #         for u in [
        #             [i async for i in r.users()]
        #             for r in msg.reactions
        #             if str(r.emoji) == correct
        #         ][0]
        #         if not u.bot
        #     ]
        # )
        mentions = ""

        for r in msg.reactions:
            async for u in r.users():
                if str(r.emoji) == correct and not u.bot:
                    mentions += f" {u.mention}"
                    break

        content = f"Well done {mentions} for getting it correct!" if mentions else "Nobody got it right..."

        a_embed = discord.Embed(
            title=f"The correct answer was {correct}!",
            description="\n".join(results),
            colour=discord.Color.pink(),
        )

        await ctx.send(content, embed=a_embed)

    @staticmethod
    async def already_reacted(message: discord.Message, user: discord.Member | discord.User) -> bool:
        """Returns whether a given user has reacted more than once to a given message."""
        users = []

        for r in message.reactions:
            async for i in r.users():
                users.append(i.id)

        return users.count(user.id) > 1  # Old reaction plus new reaction

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member | discord.User) -> None:
        """Listener to listen specifically for reactions of quiz messages."""
        if user.bot or reaction.message.id not in self.quiz_messages:
            return
        if str(reaction.emoji) not in self.quiz_messages[reaction.message.id]:
            return await reaction.message.remove_reaction(reaction, user)
        if await self.already_reacted(reaction.message, user):
            return await reaction.message.remove_reaction(reaction, user)

    @commands.command(aliases=("eastercustoms",))
    async def easter_tradition(self, ctx: Context) -> None:
        """Responds with a random tradition or custom."""
        random_country = random.choice(list(traditions))

        await ctx.send(f"{random_country}:\n{traditions[random_country]}")


async def setup(bot: Parrot) -> None:
    """Load the cog."""
    await bot.add_cog(Easter(bot))
