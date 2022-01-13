from __future__ import annotations
import random
from json import loads
import re
import discord
import asyncio
from discord.ext import commands

from pathlib import Path
from typing import Optional, Union
from contextlib import suppress
from io import BytesIO
from PIL import Image
from utilities.constants import Colours, Month

from utilities.deco import seasonal_task

from core import Cog, Context, Parrot

ALL_VIDS = loads(Path(r"extra/april_fools_vids.json").read_text("utf-8"))
BUNNY_NAMES = loads(Path(r"extra/easter/bunny_names.json").read_text("utf8"))
RIDDLE_QUESTIONS = loads(Path(r"extra/easter/easter_riddle.json").read_text("utf8"))

TIMELIMIT = 10
HTML_COLOURS = loads(Path(r"extra/html_colours.json").read_text("utf8"))
EGG_FACTS = loads(Path(r"extra/easter/easter_egg_facts.json").read_text("utf8"))
XKCD_COLOURS = loads(Path(r"bot/resources/fun/xkcd_colours.json").read_text("utf8"))
EGGHEAD_QUESTIONS = loads(
    Path(r"extra/easter/egghead_questions.json").read_text("utf8")
)
traditions = loads(Path(r"extra/easter/traditions.json").read_text("utf8"))

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
    "\U0001f1e6",
    "\U0001f1e7",
    "\U0001f1e8",
    "\U0001f1e9",
    "\U0001f1ea",
    "\U0001f1eb",
    "\U0001f1ec",
    "\U0001f1ed",
    "\U0001f1ee",
    "\U0001f1ef",
    "\U0001f1f0",
    "\U0001f1f1",
    "\U0001f1f2",
    "\U0001f1f3",
    "\U0001f1f4",
    "\U0001f1f5",
    "\U0001f1f6",
    "\U0001f1f7",
    "\U0001f1f8",
    "\U0001f1f9",
    "\U0001f1fa",
    "\U0001f1fb",
    "\U0001f1fc",
    "\U0001f1fd",
    "\U0001f1fe",
    "\U0001f1ff",
]  # ITS ABCDEFGHIJKLMNOPQRSTUVWXYZ


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


class Easter(Cog):
    """A cog for April"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.winners = set()
        self.correct = ""
        self.current_channel = None
        self.daily_fact_task = self.bot.loop.create_task(self.send_egg_fact_daily())

    @staticmethod
    def replace_invalid(colour: str) -> Optional[int]:
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
    def find_separators(displayname: str) -> Optional[list[str]]:
        """Check if Discord name contains spaces so we can bunnify an individual word in the name."""
        new_name = re.split(r"[_.\s]", displayname)
        if displayname not in new_name:
            return new_name
        return None

    @staticmethod
    def find_vowels(displayname: str) -> Optional[str]:
        """
        Finds vowels in the user's display name.
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

    @staticmethod
    def append_name(displayname: str) -> str:
        """Adds a suffix to the end of the Discord name."""
        extensions = ["foot", "ear", "nose", "tail"]
        suffix = random.choice(extensions)
        appended_name = displayname + suffix

        return appended_name

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
                "Floof" "Bounce",
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
        """
        Gives a random riddle, then provides 2 hints at certain intervals before revealing the answer.
        The duration of the hint interval can be configured by changing the TIMELIMIT constant in this file.
        """
        if self.current_channel:
            await ctx.send(
                f"A riddle is already being solved in {self.current_channel.mention}!"
            )
            return

        self.current_channel = ctx.channel

        random_question = random.choice(RIDDLE_QUESTIONS)
        question = random_question["question"]
        hints = random_question["riddles"]
        self.correct = random_question["correct_answer"]

        description = f"You have {TIMELIMIT} seconds before the first hint."

        riddle_embed = discord.Embed(
            title=question, description=description, colour=0xCF84E0
        )

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

        answer_embed = discord.Embed(
            title=f"The answer is: {self.correct}!", colour=0xCF84E0
        )

        await ctx.send(content, embed=answer_embed)

        self.winners.clear()
        self.current_channel = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """If a non-bot user enters a correct answer, their username gets added to self.winners."""
        if self.current_channel != message.channel:
            return

        if self.bot.user == message.author:
            return

        if message.content.lower() == self.correct.lower():
            self.winners.add(message.author.mention)

    @commands.command(aliases=("decorateegg",))
    async def eggdecorate(
        self, ctx: Context, *colours: Union[discord.Colour, str]
    ) -> Optional[Image.Image]:
        """
        Picks a random egg design and decorates it using the given colours.
        Colours are split by spaces, unless you wrap the colour name in double quotes.
        Discord colour names, HTML colour names, XKCD colour names and hex values are accepted.
        """
        if len(colours) < 2:
            await ctx.send("You must include at least 2 colours!")
            return

        invalid = []
        colours = list(colours)
        for idx, colour in enumerate(colours):
            if isinstance(colour, discord.Colour):
                continue
            value = self.replace_invalid(colour)
            if value:
                colours[idx] = discord.Colour(value)
            else:
                invalid.append(suppress_links(colour))

        if len(invalid) > 1:
            await ctx.send(f"Sorry, I don't know these colours: {' '.join(invalid)}")
            return
        if len(invalid) == 1:
            await ctx.send(f"Sorry, I don't know the colour {invalid[0]}!")
            return

        async with ctx.typing():
            # Expand list to 8 colours
            colours_n = len(colours)
            if colours_n < 8:
                q, r = divmod(8, colours_n)
                colours = colours * q + colours[:r]
            num = random.randint(1, 6)
            im = Image.open(
                Path(f"bot/resources/holidays/easter/easter_eggs/design{num}.png")
            )
            data = list(im.getdata())

            replaceable = {x for x in data if x not in IRREPLACEABLE}
            replaceable = sorted(replaceable, key=COLOURS.index)

            replacing_colours = {
                colour: colours[i] for i, colour in enumerate(replaceable)
            }
            new_data = []
            for x in data:
                if x in replacing_colours:
                    new_data.append((*replacing_colours[x].to_rgb(), 255))
                    # Also ensures that the alpha channel has a value
                else:
                    new_data.append(x)
            new_im = Image.new(im.mode, im.size)
            new_im.putdata(new_data)

            bufferedio = BytesIO()
            new_im.save(bufferedio, format="PNG")

            bufferedio.seek(0)

            file = discord.File(
                bufferedio, filename="egg.png"
            )  # Creates file to be used in embed
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
        return new_im

    @seasonal_task(Month.APRIL)
    async def send_egg_fact_daily(self) -> None:
        """A background task that sends an easter egg fact in the event channel everyday."""
        await self.bot.wait_until_guild_available()

        channel = self.bot.get_channel(776420233832955934)  # umm, IDK... LOL
        await channel.send(embed=self.make_embed())

    @commands.command(name="eggfact", aliases=("fact",))
    async def easter_facts(self, ctx: Context) -> None:
        """Get easter egg facts."""
        embed = self.make_embed()
        await ctx.send(embed=embed)

    @staticmethod
    def make_embed() -> discord.Embed:
        """Makes a nice embed for the message to be sent."""
        return discord.Embed(
            colour=Colours.soft_red,
            title="Easter Egg Fact",
            description=random.choice(EGG_FACTS),
        )

    @commands.command(aliases=("eggheadquiz", "easterquiz"))
    async def eggquiz(self, ctx: Context) -> None:
        """
        Gives a random quiz question, waits 30 seconds and then outputs the answer.
        Also informs of the percentages and votes of each option
        """
        random_question = random.choice(EGGHEAD_QUESTIONS)
        question, answers = random_question["question"], random_question["answers"]
        answers = [(EMOJIS[i], a) for i, a in enumerate(answers)]
        correct = EMOJIS[random_question["correct_answer"]]

        valid_emojis = [emoji for emoji, _ in answers]

        description = f"You have {TIMELIMIT} seconds to vote.\n\n"
        description += "\n".join(
            [f"{emoji} -> **{answer}**" for emoji, answer in answers]
        )

        q_embed = discord.Embed(
            title=question, description=description, colour=Colours.pink
        )

        msg = await ctx.send(embed=q_embed)
        for emoji in valid_emojis:
            await msg.add_reaction(emoji)

        self.quiz_messages[msg.id] = valid_emojis

        await asyncio.sleep(TIMELIMIT)

        del self.quiz_messages[msg.id]

        msg = await ctx.fetch_message(msg.id)  # Refreshes message

        total_no = sum([len(await r.users().flatten()) for r in msg.reactions]) - len(
            valid_emojis
        )  # - bot's reactions

        if total_no == 0:
            return await msg.delete()  # To avoid ZeroDivisionError if nobody reacts

        results = ["**VOTES:**"]
        for emoji, _ in answers:
            num = [
                len(await r.users().flatten())
                for r in msg.reactions
                if str(r.emoji) == emoji
            ][0] - 1
            percent = round(100 * num / total_no)
            s = "" if num == 1 else "s"
            string = f"{emoji} - {num} vote{s} ({percent}%)"
            results.append(string)

        mentions = " ".join(
            [
                u.mention
                for u in [
                    await r.users().flatten()
                    for r in msg.reactions
                    if str(r.emoji) == correct
                ][0]
                if not u.bot
            ]
        )

        content = (
            f"Well done {mentions} for getting it correct!"
            if mentions
            else "Nobody got it right..."
        )

        a_embed = discord.Embed(
            title=f"The correct answer was {correct}!",
            description="\n".join(results),
            colour=Colours.pink,
        )

        await ctx.send(content, embed=a_embed)

    @staticmethod
    async def already_reacted(
        message: discord.Message, user: Union[discord.Member, discord.User]
    ) -> bool:
        """Returns whether a given user has reacted more than once to a given message."""
        users = [
            u.id
            for reaction in [await r.users().flatten() for r in message.reactions]
            for u in reaction
        ]
        return users.count(user.id) > 1  # Old reaction plus new reaction

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]
    ) -> None:
        """Listener to listen specifically for reactions of quiz messages."""
        if user.bot:
            return
        if reaction.message.id not in self.quiz_messages:
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
