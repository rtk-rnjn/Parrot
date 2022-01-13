from __future__ import annotations

import random
import asyncio
import discord
import bisect
import re
from collections import defaultdict
from typing import Union, Optional

from json import loads, dumps
from datetime import timedelta, datetime
from pathlib import Path

from discord import Embed, Reaction, TextChannel, User
from discord.colour import Colour
from discord.ext import tasks
from discord.ext.commands import group
from discord.ext import commands

from async_rediscache import RedisCache

from utilities.constants import Colours, Month
from utilities.deco import in_month

from core import Cog, Parrot, Context

# chance is 1 in x range, so 1 in 20 range would give 5% chance (for add candy)
ADD_CANDY_REACTION_CHANCE = 20  # 5%
ADD_CANDY_EXISTING_REACTION_CHANCE = 10  # 10%
ADD_SKULL_REACTION_CHANCE = 50  # 2%
ADD_SKULL_EXISTING_REACTION_CHANCE = 20  # 5%

EMOJIS = dict(
    CANDY="\N{CANDY}",
    SKULL="\N{SKULL}",
    MEDALS=(
        "\N{FIRST PLACE MEDAL}",
        "\N{SECOND PLACE MEDAL}",
        "\N{THIRD PLACE MEDAL}",
        "\N{SPORTS MEDAL}",
        "\N{SPORTS MEDAL}",
    ),
)

SPOOKY_EMOJIS = [
    "\N{BAT}",
    "\N{DERELICT HOUSE BUILDING}",
    "\N{EXTRATERRESTRIAL ALIEN}",
    "\N{GHOST}",
    "\N{JACK-O-LANTERN}",
    "\N{SKULL}",
    "\N{SKULL AND CROSSBONES}",
    "\N{SPIDER WEB}",
]
PUMPKIN_ORANGE = 0xFF7518
INTERVAL = timedelta(hours=6).total_seconds()

HALLOWEENIFY_DATA = loads(Path(r"extra/halloween/halloweenify.json").read_text("utf8"))

FACTS = loads(Path(r"extra/halloween/halloween_facts.json").read_text("utf8"))
FACTS = list(enumerate(FACTS))
TEXT_OPTIONS = loads(
    Path(r"extra/halloween/monster.json").read_text("utf8")
)  # Data for a mad-lib style generation of text

EMOJIS_VAL = {
    "\N{Jack-O-Lantern}": 1,
    "\N{Ghost}": 2,
    "\N{Skull and Crossbones}": 3,
    "\N{Zombie}": 4,
    "\N{Face Screaming In Fear}": 5,
}
ADDED_MESSAGES = [
    "Let's see if you win?",
    ":jack_o_lantern: SPOOKY :jack_o_lantern:",
    "If you got it, haunt it.",
    "TIME TO GET YOUR SPOOKY ON! :skull:",
]
PING = "<@{id}>"

EMOJI_MESSAGE = "\n".join(f"- {emoji} {val}" for emoji, val in EMOJIS_VAL.items())
HELP_MESSAGE_DICT = {
    "title": "Spooky Name Rate",
    "description": "Help for the `$spookynamerate` command",
    "color": Colours.soft_orange,
    "fields": [
        {
            "name": "How to play",
            "value": (
                "Everyday, the bot will post a random name, which you will need to spookify using your creativity.\n"
                "You can rate each message according to how scary it is.\n"
                "At the end of the day, the author of the message with most reactions will be the winner of the day.\n"
                f"On a scale of 1 to {len(EMOJIS_VAL)}, the reactions order:\n"
                f"{EMOJI_MESSAGE}"
            ),
            "inline": False,
        },
        {
            "name": "How do I add my spookified name?",
            "value": "Simply type `$spookynamerate add my name`",
            "inline": False,
        },
        {
            "name": "How do I *delete* my spookified name?",
            "value": "Simply type `$spookynamerate delete`",
            "inline": False,
        },
    ],
}

# The names are from https://www.mockaroo.com/
NAMES = loads(Path(r"extra/halloween/spookynamerate_names.json").read_text("utf8"))
FIRST_NAMES = NAMES["first_names"]
LAST_NAMES = NAMES["last_names"]
data: dict[str, dict[str, str]] = loads(
    Path(r"extra/halloween/spooky_rating.json").read_text("utf8")
)
SPOOKY_DATA = sorted((int(key), value) for key, value in data.items())
SPOOKY_TRIGGERS = {
    "spooky": (r"\bspo{2,}ky\b", "\U0001F47B"),
    "skeleton": (r"\bskeleton\b", "\U0001F480"),
    "doot": (r"\bdo{2,}t\b", "\U0001F480"),
    "pumpkin": (r"\bpumpkin\b", "\U0001F383"),
    "halloween": (r"\bhalloween\b", "\U0001F383"),
    "jack-o-lantern": (r"\bjack-o-lantern\b", "\U0001F383"),
    "danger": (r"\bdanger\b", "\U00002620"),
}


class Halloween(Cog):
    """Halloween collection games and other stuff."""

    # User candy amount records
    candy_records = RedisCache()
    messages = RedisCache()
    data = RedisCache()
    # Candy and skull messages mapping
    candy_messages = RedisCache()
    skull_messages = RedisCache()

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.registry_path = Path("extra", "halloween", "monstersurvey.json")
        self.voter_registry = loads(self.registry_path.read_text("utf8"))
        self.name = None
        self.debug = True
        self.bot.loop.create_task(self.load_vars())
        self.local_random = random.Random()
        self.first_time = None
        self.poll = False
        self.announce_name.start()
        self.checking_messages = asyncio.Lock()

    async def load_vars(self) -> None:
        """Loads the variables that couldn't be loaded in __init__."""
        self.first_time = await self.data.get("first_time", True)
        self.name = await self.data.get("name")

    def random_fact(self) -> tuple[int, str]:
        """Return a random fact from the loaded facts."""
        return random.choice(FACTS)

    def json_write(self) -> None:
        """Write voting results to a local JSON file."""
        self.registry_path.write_text(dumps(self.voter_registry, indent=2))

    def cast_vote(self, id: int, monster: str) -> None:
        """
        Cast a user's vote for the specified monster.
        If the user has already voted, their existing vote is removed.
        """
        vr = self.voter_registry
        for m in vr:
            if id not in vr[m]["votes"] and m == monster:
                vr[m]["votes"].append(id)
            else:
                if id in vr[m]["votes"] and m != monster:
                    vr[m]["votes"].remove(id)

    def get_name_by_leaderboard_index(self, n: int) -> str:
        """Return the monster at the specified leaderboard index."""
        n = n - 1
        vr = self.voter_registry
        top = sorted(vr, key=lambda k: len(vr[k]["votes"]), reverse=True)
        name = top[n] if n >= 0 else None
        return name

    async def _short_circuit_check(self, message: discord.Message) -> bool:
        """
        Short-circuit helper check.
        Return True if:
          * author is a bot
          * prefix is not None
        """
        # Check if message author is a bot
        if message.author.bot:
            return True

        # Check for command invocation
        # Because on_message doesn't give a full Context object, generate one first
        ctx = await self.bot.get_context(message)
        if ctx.prefix:
            return True

        return False

    @in_month(Month.OCTOBER)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Randomly adds candy or skull reaction to non-bot messages in the Event channel."""
        # Ignore messages in DMs
        if not message.guild:
            return
        # make sure its a human message
        if message.author.bot:
            return
        # ensure it's hacktober channel
        for name, trigger in SPOOKY_TRIGGERS.items():
            trigger_test = re.search(trigger[0], message.content.lower())
            if trigger_test:
                # Check message for bot replies and/or command invocations
                # Short circuit if they're found, logging is handled in _short_circuit_check
                if await self._short_circuit_check(message):
                    return
                await message.add_reaction(trigger[1])

        # do random check for skull first as it has the lower chance
        if random.randint(1, ADD_SKULL_REACTION_CHANCE) == 1:
            await self.skull_messages.set(message.id, "skull")
            await message.add_reaction(EMOJIS["SKULL"])
        # check for the candy chance next
        elif random.randint(1, ADD_CANDY_REACTION_CHANCE) == 1:
            await self.candy_messages.set(message.id, "candy")
            await message.add_reaction(EMOJIS["CANDY"])

    @in_month(Month.OCTOBER)
    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]
    ) -> None:
        """Add/remove candies from a person if the reaction satisfies criteria."""
        message = reaction.message
        # check to ensure the reactor is human
        if user.bot:
            return

        # if its not a candy or skull, and it is one of 10 most recent messages,
        # proceed to add a skull/candy with higher chance
        if str(reaction.emoji) not in (EMOJIS["SKULL"], EMOJIS["CANDY"]):
            # Ensure the reaction is not for a bot's message so users can't spam
            # reaction buttons like in .help to get candies.
            if message.author.bot:
                return

            recent_message_ids = map(
                lambda m: m.id, await self.hacktober_channel.history(limit=10).flatten()
            )
            if message.id in recent_message_ids:
                await self.reacted_msg_chance(message)
            return

        if (
            await self.candy_messages.get(message.id) == "candy"
            and str(reaction.emoji) == EMOJIS["CANDY"]
        ):
            await self.candy_messages.delete(message.id)
            if await self.candy_records.contains(user.id):
                await self.candy_records.increment(user.id)
            else:
                await self.candy_records.set(user.id, 1)

        elif (
            await self.skull_messages.get(message.id) == "skull"
            and str(reaction.emoji) == EMOJIS["SKULL"]
        ):
            await self.skull_messages.delete(message.id)

            if prev_record := await self.candy_records.get(user.id):
                lost = min(random.randint(1, 3), prev_record)
                await self.candy_records.decrement(user.id, lost)

                if lost == prev_record:
                    await self.send_spook_msg(user, message.channel, "all of your")
                else:
                    await self.send_spook_msg(user, message.channel, lost)
            else:
                await self.send_no_candy_spook_message(user, message.channel)
        else:
            return  # Skip saving

        await reaction.clear()

    async def reacted_msg_chance(self, message: discord.Message) -> None:
        """
        Randomly add a skull or candy reaction to a message if there is a reaction there already.
        This event has a higher probability of occurring than a reaction add to a message without an
        existing reaction.
        """
        if random.randint(1, ADD_SKULL_EXISTING_REACTION_CHANCE) == 1:
            await self.skull_messages.set(message.id, "skull")
            await message.add_reaction(EMOJIS["SKULL"])

        elif random.randint(1, ADD_CANDY_EXISTING_REACTION_CHANCE) == 1:
            await self.candy_messages.set(message.id, "candy")
            await message.add_reaction(EMOJIS["CANDY"])

    @property
    def hacktober_channel(self) -> discord.TextChannel:
        """Get #parrot channel from its ID."""
        channel = discord.utils.get(self.bot.get_all_channels(), name="parrot")
        return channel

    @staticmethod
    async def send_spook_msg(
        author: discord.Member, channel: discord.TextChannel, candies: Union[str, int]
    ) -> None:
        """Send a spooky message."""
        e = discord.Embed(colour=author.colour)
        e.set_author(
            name="Ghosts and Ghouls and Jack o' lanterns at night; "
            f"I took {candies} candies and quickly took flight."
        )
        await channel.send(embed=e)

    @staticmethod
    async def send_no_candy_spook_message(
        author: discord.Member, channel: discord.TextChannel
    ) -> None:
        """An alternative spooky message sent when user has no candies in the collection."""
        embed = discord.Embed(color=author.color)
        embed.set_author(
            name=(
                "Ghosts and Ghouls and Jack o' lanterns at night; "
                "I tried to take your candies but you had none to begin with!"
            )
        )
        await channel.send(embed=embed)

    @in_month(Month.OCTOBER)
    @commands.command()
    async def candy(self, ctx: Context) -> None:
        """Get the candy leaderboard and save to JSON."""
        records = await self.candy_records.items()

        def generate_leaderboard() -> str:
            top_sorted = sorted(
                ((user_id, score) for user_id, score in records if score > 0),
                key=lambda x: x[1],
                reverse=True,
            )
            top_five = top_sorted[:5]

            return (
                "\n".join(
                    f"{EMOJIS['MEDALS'][index]} <@{record[0]}>: {record[1]}"
                    for index, record in enumerate(top_five)
                )
                if top_five
                else "No Candies"
            )

        def get_user_candy_score() -> str:
            for user_id, score in records:
                if user_id == ctx.author.id:
                    return f"{ctx.author.mention}: {score}"
            return f"{ctx.author.mention}: 0"

        e = discord.Embed(colour=discord.Colour.og_blurple())
        e.add_field(
            name="Top Candy Records", value=generate_leaderboard(), inline=False
        )
        e.add_field(name="Your Candy Score", value=get_user_candy_score(), inline=False)
        e.add_field(
            name="\u200b",
            value="Candies will randomly appear on messages sent. "
            "\nHit the candy when it appears as fast as possible to get the candy! "
            "\nBut beware the ghosts...",
            inline=False,
        )
        await ctx.send(embed=e)

    @commands.command(
        name="spookyfact",
        aliases=("halloweenfact",),
        brief="Get the most recent Halloween fact",
    )
    async def get_random_fact(self, ctx: Context) -> None:
        """Reply with the most recent Halloween fact."""
        index, fact = self.random_fact()
        embed = self._build_embed(index, fact)
        await ctx.send(embed=embed)

    @staticmethod
    def _build_embed(index: int, fact: str) -> discord.Embed:
        """Builds a Discord embed from the given fact and its index."""
        emoji = random.choice(SPOOKY_EMOJIS)
        title = f"{emoji} Halloween Fact #{index + 1}"
        return discord.Embed(title=title, description=fact, color=PUMPKIN_ORANGE)

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command()
    async def halloweenify(self, ctx: Context) -> None:
        """Change your nickname into a much spookier one!"""
        async with ctx.typing():
            # Choose a random character from our list we loaded above and set apart the nickname and image url.
            character = random.choice(HALLOWEENIFY_DATA["characters"])
            nickname = "".join(nickname for nickname in character)
            image = "".join(character[nickname] for nickname in character)

            # Build up a Embed
            embed = discord.Embed()
            embed.colour = discord.Colour.dark_orange()
            embed.title = "Not spooky enough?"
            embed.description = (
                f"**{ctx.author.display_name}** wasn't spooky enough for you? That's understandable, "
                f"{ctx.author.display_name} isn't scary at all! "
                "Let me think of something better. Hmm... I got it!\n\n "
            )
            embed.set_image(url=image)

            if isinstance(ctx.author, discord.Member):
                try:
                    await ctx.author.edit(nick=nickname)
                    embed.description += f"Your new nickname will be: \n:ghost: **{nickname}** :jack_o_lantern:"

                except discord.Forbidden:  # The bot doesn't have enough permission
                    embed.description += (
                        f"Your new nickname should be: \n :ghost: **{nickname}** :jack_o_lantern: \n\n"
                        f"It looks like I cannot change your name, but feel free to change it yourself."
                    )

            else:  # The command has been invoked in DM
                embed.description += (
                    f"Your new nickname should be: \n :ghost: **{nickname}** :jack_o_lantern: \n\n"
                    f"Feel free to change it yourself, or invoke the command again inside the server."
                )

        await ctx.send(embed=embed)

    def generate_name(self, seeded_random: random.Random) -> str:
        """Generates a name (for either monster species or monster name)."""
        n_candidate_strings = seeded_random.randint(
            2, len(TEXT_OPTIONS["monster_type"])
        )
        return "".join(
            seeded_random.choice(TEXT_OPTIONS["monster_type"][i])
            for i in range(n_candidate_strings)
        )

    @commands.command(brief="Sends your monster bio!")
    async def monsterbio(self, ctx: Context) -> None:
        """Sends a description of a monster."""
        seeded_random = random.Random(
            ctx.author.id
        )  # Seed a local Random instance rather than the system one

        name = self.generate_name(seeded_random)
        species = self.generate_name(seeded_random)
        biography_text = seeded_random.choice(TEXT_OPTIONS["biography_text"])
        words = {"monster_name": name, "monster_species": species}
        for key, value in biography_text.items():
            if key == "text":
                continue

            options = seeded_random.sample(TEXT_OPTIONS[key], value)
            words[key] = " ".join(options)

        embed = discord.Embed(
            title=f"{name}'s Biography",
            color=seeded_random.choice([Colours.orange, Colours.purple]),
            description=biography_text["text"].format_map(words),
        )

        await ctx.send(embed=embed)

    @commands.group(name="monster", aliases=("mon",))
    async def monster_group(self, ctx: Context) -> None:
        """The base voting command. If nothing is called, then it will return an embed."""
        if ctx.invoked_subcommand is None:
            async with ctx.typing():
                default_embed = discord.Embed(
                    title="Monster Voting",
                    color=0xFF6800,
                    description="Vote for your favorite monster!",
                )
                default_embed.add_field(
                    name=".monster show monster_name(optional)",
                    value="Show a specific monster. If none is listed, it will give you an error with valid choices.",
                    inline=False,
                )
                default_embed.add_field(
                    name=".monster vote monster_name",
                    value="Vote for a specific monster. You get one vote, but can change it at any time.",
                    inline=False,
                )
                default_embed.add_field(
                    name=".monster leaderboard",
                    value="Which monster has the most votes? This command will tell you.",
                    inline=False,
                )
                default_embed.set_footer(
                    text=f"Monsters choices are: {', '.join(self.voter_registry)}"
                )

            await ctx.send(embed=default_embed)

    @monster_group.command(name="vote")
    async def monster_vote(self, ctx: Context, name: str = None) -> None:
        """
        Cast a vote for a particular monster.
        Displays a list of monsters that can be voted for if one is not specified.
        """
        if name is None:
            await ctx.invoke(self.monster_leaderboard)
            return

        async with ctx.typing():
            # Check to see if user used a numeric (leaderboard) index to vote
            try:
                idx = int(name)
                name = self.get_name_by_leaderboard_index(idx)
            except ValueError:
                name = name.lower()

            vote_embed = discord.Embed(name="Monster Voting", color=0xFF6800)

            m = self.voter_registry.get(name)
            if m is None:
                vote_embed.description = (
                    f"You cannot vote for {name} because it's not in the running."
                )
                vote_embed.add_field(
                    name="Use `.monster show {monster_name}` for more information on a specific monster",
                    value="or use `.monster vote {monster}` to cast your vote for said monster.",
                    inline=False,
                )
                vote_embed.add_field(
                    name="You may vote for or show the following monsters:",
                    value=", ".join(self.voter_registry.keys()),
                )
            else:
                self.cast_vote(ctx.author.id, name)
                vote_embed.add_field(
                    name="Vote successful!",
                    value=f"You have successfully voted for {m['full_name']}!",
                    inline=False,
                )
                vote_embed.set_thumbnail(url=m["image"])
                vote_embed.set_footer(
                    text="Please note that any previous votes have been removed."
                )
                self.json_write()

        await ctx.send(embed=vote_embed)

    @monster_group.command(name="show")
    async def monster_show(self, ctx: Context, name: str = None) -> None:
        """Shows the named monster. If one is not named, it sends the default voting embed instead."""
        if name is None:
            await ctx.invoke(self.monster_leaderboard)
            return

        async with ctx.typing():
            # Check to see if user used a numeric (leaderboard) index to vote
            try:
                idx = int(name)
                name = self.get_name_by_leaderboard_index(idx)
            except ValueError:
                name = name.lower()

            m = self.voter_registry.get(name)
            if not m:
                await ctx.send("That monster does not exist.")
                await ctx.invoke(self.monster_vote)
                return

            embed = discord.Embed(title=m["full_name"], color=0xFF6800)
            embed.add_field(name="Summary", value=m["summary"])
            embed.set_image(url=m["image"])
            embed.set_footer(
                text=f"To vote for this monster, type .monster vote {name}"
            )

        await ctx.send(embed=embed)

    @monster_group.command(name="leaderboard", aliases=("lb",))
    async def monster_leaderboard(self, ctx: Context) -> None:
        """Shows the current standings."""
        async with ctx.typing():
            vr = self.voter_registry
            top = sorted(vr, key=lambda k: len(vr[k]["votes"]), reverse=True)
            total_votes = sum(len(m["votes"]) for m in self.voter_registry.values())

            embed = discord.Embed(title="Monster Survey Leader Board", color=0xFF6800)
            for rank, m in enumerate(top):
                votes = len(vr[m]["votes"])
                percentage = ((votes / total_votes) * 100) if total_votes > 0 else 0
                embed.add_field(
                    name=f"{rank+1}. {vr[m]['full_name']}",
                    value=(
                        f"{votes} votes. {percentage:.1f}% of total votes.\n"
                        f"Vote for this monster by typing "
                        f"'.monster vote {m}'\n"
                        f"Get more information on this monster by typing "
                        f"'.monster show {m}'"
                    ),
                    inline=False,
                )

            embed.set_footer(
                text="You can also vote by their rank number. '.monster vote {number}' "
            )

        await ctx.send(embed=embed)

    @group(name="spookynamerate", invoke_without_command=True)
    async def spooky_name_rate(self, ctx: Context) -> None:
        """Get help on the Spooky Name Rate game."""
        await ctx.send(embed=Embed.from_dict(HELP_MESSAGE_DICT))

    @spooky_name_rate.command(name="list", aliases=("all", "entries"))
    async def list_entries(self, ctx: Context) -> None:
        """Send all the entries up till now in a single embed."""
        await ctx.send(embed=await self.get_responses_list(final=False))

    @spooky_name_rate.command(name="name")
    async def tell_name(self, ctx: Context) -> None:
        """Tell the current random name."""
        if not self.poll:
            await ctx.send(f"The name is **{self.name}**")
            return

        await ctx.send(
            f"The name ~~is~~ was **{self.name}**. The poll has already started, so you cannot "
            "add an entry."
        )

    @spooky_name_rate.command(name="add", aliases=("register",))
    async def add_name(self, ctx: Context, *, name: str) -> None:
        """Use this command to add/register your spookified name."""
        if self.poll:
            await ctx.send(
                "Sorry, the poll has started! You can try and participate in the next round though!"
            )
            return

        for data in (loads(user_data) for _, user_data in await self.messages.items()):
            if data["author"] == ctx.author.id:
                await ctx.send(
                    "But you have already added an entry! Type "
                    f"`$spookynamerate "
                    "delete` to delete it, and then you can add it again"
                )
                return

            if data["name"] == name:
                await ctx.send("TOO LATE. Someone has already added this name.")
                return

        msg = await (await self.get_channel()).send(
            f"{ctx.author.mention} added the name {name!r}!"
        )

        await self.messages.set(
            msg.id,
            dumps(
                {
                    "name": name,
                    "author": ctx.author.id,
                    "score": 0,
                }
            ),
        )

        for emoji in EMOJIS_VAL:
            await msg.add_reaction(emoji)

    @spooky_name_rate.command(name="delete")
    async def delete_name(self, ctx: Context) -> None:
        """Delete the user's name."""
        if self.poll:
            await ctx.send(
                "You can't delete your name since the poll has already started!"
            )
            return
        for message_id, data in await self.messages.items():
            data = loads(data)

            if ctx.author.id == data["author"]:
                await self.messages.delete(message_id)
                await ctx.send(f"Name deleted successfully ({data['name']!r})!")
                return

        await ctx.send(
            "But you don't have an entry... :eyes: Type `$spookynamerate add your entry`"
        )

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: User) -> None:
        """Ensures that each user adds maximum one reaction."""
        if user.bot or not await self.messages.contains(reaction.message.id):
            return

        async with self.checking_messages:  # Acquire the lock so that the dictionary isn't reset while iterating.
            if reaction.emoji in EMOJIS_VAL:
                # create a custom counter
                reaction_counter = defaultdict(int)
                for msg_reaction in reaction.message.reactions:
                    async for reaction_user in msg_reaction.users():
                        if reaction_user == self.bot.user:
                            continue
                        reaction_counter[reaction_user] += 1

                if reaction_counter[user] > 1:
                    await user.send(
                        "Sorry, you have already added a reaction, "
                        "please remove your reaction and try again."
                    )
                    await reaction.remove(user)
                    return

    @tasks.loop(hours=24.0)
    async def announce_name(self) -> None:
        """Announces the name needed to spookify every 24 hours and the winner of the previous game."""
        if not self.in_allowed_month():
            return

        channel = await self.get_channel()

        if self.first_time:
            await channel.send(
                "Okkey... Welcome to the **Spooky Name Rate Game**! It's a relatively simple game.\n"
                f"Everyday, a random name will be sent in #parrot "
                "and you need to try and spookify it!\nRegister your name using "
                f"`$spookynamerate add spookified name`"
            )

            await self.data.set("first_time", False)
            self.first_time = False

        else:
            if await self.messages.items():
                await channel.send(embed=await self.get_responses_list(final=True))
                self.poll = True
                if not self.debug:
                    await asyncio.sleep(2 * 60 * 60)  # sleep for two hours

            for message_id, data in await self.messages.items():
                data = loads(data)

                msg = await channel.fetch_message(message_id)
                score = 0
                for reaction in msg.reactions:
                    reaction_value = EMOJIS_VAL.get(
                        reaction.emoji, 0
                    )  # get the value of the emoji else 0
                    score += reaction_value * (
                        reaction.count - 1
                    )  # multiply by the num of reactions
                    # subtract one, since one reaction was done by the bot

                data["score"] = score
                await self.messages.set(message_id, dumps(data))

            # Sort the winner messages
            winner_messages = sorted(
                (
                    (msg_id, loads(usr_data))
                    for msg_id, usr_data in await self.messages.items()
                ),
                key=lambda x: x[1]["score"],
                reverse=True,
            )

            winners = []
            for i, winner in enumerate(winner_messages):
                winners.append(winner)
                if len(winner_messages) > i + 1:
                    if winner_messages[i + 1][1]["score"] != winner[1]["score"]:
                        break
                elif (
                    len(winner_messages) == (i + 1) + 1
                ):  # The next element is the last element
                    if winner_messages[i + 1][1]["score"] != winner[1]["score"]:
                        break

            # one iteration is complete
            await channel.send(
                "Today's Spooky Name Rate Game ends now, and the winner(s) is(are)..."
            )

            async with channel.typing():
                await asyncio.sleep(1)  # give the drum roll feel

                if not winners:  # There are no winners (no participants)
                    await channel.send("Hmm... Looks like no one participated! :cry:")
                    return

                score = winners[0][1]["score"]
                congratulations = (
                    "to all"
                    if len(winners) > 1
                    else PING.format(id=winners[0][1]["author"])
                )
                names = ", ".join(
                    f'{win[1]["name"]} ({PING.format(id=win[1]["author"])})'
                    for win in winners
                )

                # display winners, their names and scores
                await channel.send(
                    f"Congratulations {congratulations}!\n"
                    f"You have a score of {score}!\n"
                    f"Your name{ 's were' if len(winners) > 1 else 'was'}:\n{names}"
                )

                # Send random party emojis
                party = (
                    random.choice([":partying_face:", ":tada:"])
                    for _ in range(random.randint(1, 10))
                )
                await channel.send(" ".join(party))

            async with self.checking_messages:  # Acquire the lock to delete the messages
                await self.messages.clear()  # reset the messages

        # send the next name
        self.name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        await self.data.set("name", self.name)

        await channel.send(
            "Let's move on to the next name!\nAnd the next name is...\n"
            f"**{self.name}**!\nTry to spookify that... :smirk:"
        )

        self.poll = False  # accepting responses

    @announce_name.before_loop
    async def wait_till_scheduled_time(self) -> None:
        """Waits till the next day's 12PM if crossed it, otherwise waits till the same day's 12PM."""
        if self.debug:
            return

        now = datetime.utcnow()
        if now.hour < 12:
            twelve_pm = now.replace(hour=12, minute=0, second=0, microsecond=0)
            time_left = twelve_pm - now
            await asyncio.sleep(time_left.seconds)
            return

        tomorrow_12pm = now + timedelta(days=1)
        tomorrow_12pm = tomorrow_12pm.replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((tomorrow_12pm - now).seconds)

    async def get_responses_list(self, final: bool = False) -> Embed:
        """Returns an embed containing the responses of the people."""
        embed = Embed(color=Colour.red())
        if await self.messages.items():
            if final:
                embed.title = "Spooky Name Rate is about to end!"
                embed.description = (
                    "This Spooky Name Rate round is about to end in 2 hours! You can review "
                    "the entries below! Have you rated other's names?"
                )
            else:
                embed.title = "All the spookified names!"
                embed.description = "See a list of all the entries entered by everyone!"
        else:
            embed.title = "No one has added an entry yet..."

        for message_id, data in await self.messages.items():
            data = loads(data)

            embed.add_field(
                name=(
                    self.bot.get_user(data["author"])
                    or await self.bot.fetch_user(data["author"])
                ).name,
                value=f"{data['name']}",
            )

        return embed

    async def get_channel(self) -> Optional[TextChannel]:
        """Gets the parrot-channel after waiting until ready."""
        await self.bot.wait_until_ready()
        channel = discord.utils.get(self.bot.get_all_channels(), name="parrot")
        return channel

    @staticmethod
    def in_allowed_month() -> bool:
        """Returns whether running in the limited month."""
        return True

    def cog_check(self, ctx: Context) -> bool:
        """A command to check whether the command is being called in October."""
        if not self.in_allowed_month():
            raise commands.BadArgument("You can only use these commands in October!")
        return True

    def cog_unload(self) -> None:
        """Stops the announce_name task."""
        self.announce_name.cancel()

    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def spookyrating(self, ctx: Context, who: discord.Member = None) -> None:
        """
        Calculates the spooky rating of someone.
        Any user will always yield the same result, no matter who calls the command
        """
        if who is None:
            who = ctx.author

        # This ensures that the same result over multiple runtimes
        self.local_random.seed(who.id)
        spooky_percent = self.local_random.randint(1, 101)

        # We need the -1 due to how bisect returns the point
        # see the documentation for further detail
        # https://docs.python.org/3/library/bisect.html#bisect.bisect
        index = bisect.bisect(SPOOKY_DATA, (spooky_percent,)) - 1

        _, data = SPOOKY_DATA[index]

        embed = discord.Embed(
            title=data["title"],
            description=f"{who} scored {spooky_percent}%!",
            color=Colours.orange,
        )
        embed.add_field(name="A whisper from Satan", value=data["text"])
        embed.set_thumbnail(url=data["image"])

        await ctx.send(embed=embed)
