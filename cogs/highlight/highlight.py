from __future__ import annotations

import asyncio
import datetime
import logging
import re
from typing import Any, Literal

from pymongo import UpdateMany, UpdateOne
from pymongo.results import BulkWriteResult

import discord
from core import Cog, Context, Parrot, ParrotLinkView
from discord.ext import commands, tasks
from utilities.formats import plural

log = logging.getLogger("cogs.highlight.highlight")

CACHED_WORDS_HINT = dict[int, list[dict[str, str | int]]]
_CACHED_SETTINGS_HINT = dict[str, str | int | list[Any]]
CACHED_SETTINGS_HINT = dict[int, _CACHED_SETTINGS_HINT]
ENTITY_HINT = discord.Member | discord.User | discord.TextChannel | discord.CategoryChannel


def format_join(iterable, *, seperator=", ", last="or"):
    if len(iterable) == 0:
        return ""
    if len(iterable) == 1:
        return iterable[0]
    if len(iterable) == 2:
        return f"{iterable[0]} and {iterable[1]}"

    return f"{seperator.join(iterable[:-1])}{seperator}{last} {iterable[-1]}"


class JumpBackView(ParrotLinkView):
    def __init__(self, jump_url) -> None:
        super().__init__(url=jump_url, label="Jump Back")


class Highlight(Cog):
    """Highlight words and get notified when they are said."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._highlight_batch = []
        self._batch_lock = asyncio.Lock()

        self.cached_words: CACHED_WORDS_HINT = {}
        self.cached_settings: CACHED_SETTINGS_HINT = {}
        self.bulk_insert_loop.start()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{ELECTRIC TORCH}")

    def _partial_settings(self, user_id: int) -> dict:
        return {"user_id": user_id, "disabled": False, "blocked_users": [], "blocked_channels": []}

    async def get_user_settings(self, user_id: int) -> _CACHED_SETTINGS_HINT:
        try:
            maybe_partial = self._partial_settings(user_id)
            return maybe_partial | self.cached_settings[user_id]
        except KeyError:
            pass

        find_one_data = await self.bot.user_collections_ind.find_one(
            {"_id": user_id, "highlight_settings": {"$exists": True}},
        )
        if find_one_data is None:
            return {
                "user_id": user_id,
                "disabled": False,
                "blocked_users": [],
                "blocked_channels": [],
            }

        self.cached_settings[user_id] = find_one_data["highlight_settings"]

        user_id = find_one_data["highlight_settings"].get("user_id", user_id)
        disabled = find_one_data["highlight_settings"].get("disabled", False)
        blocked_users = find_one_data["highlight_settings"].get("blocked_users", [])
        blocked_channels = find_one_data["highlight_settings"].get("blocked_channels", [])
        return {
            "user_id": user_id,
            "disabled": disabled,
            "blocked_users": blocked_users,
            "blocked_channels": blocked_channels,
        }

    async def cog_unload(self):
        log.info("Stopping bulk insert loop")
        self.bulk_insert_loop.stop()
        await self.bulk_insert()

    async def cog_load(self):
        log.info("Getting all the highlight settings")
        async for data in self.bot.user_collections_ind.find({"highlight_settings": {"$exists": True}}):
            self.cached_settings[data["_id"]] = data["highlight_settings"]

        log.info("Getting all the highlight words")
        async for data in self.bot.user_collections_ind.find({"highlight_words": {"$exists": True}}):
            self.cached_words[data["_id"]] = data["highlight_words"]

    @commands.Cog.listener("on_message")
    async def check_highlights(self, message: discord.Message):
        await self.bot.wait_until_ready()
        if not message.guild or message.author.bot:
            return

        notified_users = []
        possible_words = []

        for _id, words in self.cached_words.items():
            possible_words.extend({**word, "user_id": _id} for word in words if word["guild_id"] == message.guild.id)

        # Go through all possible messages
        for possible_word in possible_words:
            # Use regex to check if the highlight word is in the message
            # And avoid any false positives
            escaped = re.escape(possible_word["word"])
            match = re.match(
                rf"(.*)({escaped})(.*)",
                message.content,
                re.IGNORECASE | re.DOTALL | re.MULTILINE,
            )

            # If there's a match and the user wasn't already notified
            if match and possible_word["user_id"] not in notified_users:
                notified_users.append(possible_word["user_id"])
                self.bot.dispatch("highlight", message, possible_word, match[1])

    # The following three listeners send a user activity to the on_highlight_trigger function
    # This way the user has time to indicate that they saw the message and we do not need to highlight them
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()
        self.bot.dispatch("user_activity", message.channel, message.author)

    @commands.Cog.listener()
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: discord.User,
        when: datetime.datetime,
    ):
        self.bot.dispatch("user_activity", channel, user)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        self.bot.dispatch("user_activity", reaction.message.channel, user)

    @commands.Cog.listener()
    async def on_highlight(self, message: discord.Message, word: dict[str, str | int], text: str):
        assert message.guild is not None

        member: discord.Member | None = await self.bot.get_or_fetch_member(
            message.guild,
            word["user_id"],
        )

        if member is None:
            log.info("Unknown user ID %s (guild ID %s)", word["user_id"], word["guild_id"])
            return

        # Wait for any activity
        try:
            await self.bot.wait_for(
                "user_activity",
                check=lambda channel, user: message.channel == channel and user == member,
                timeout=15,
            )
            return
        except asyncio.TimeoutError:
            pass

        # Don't highlight if they were already pinged
        # Don't highlight if they can't even see the channel
        # Don't highlight if it's a command
        if (
            member in message.mentions
            or member not in getattr(message.channel, "members", [])
            or (await self.bot.get_context(message)).valid
        ):
            return

        settings = await self.get_user_settings(member.id)

        # Don't highlight if the user themsel
        # Don't highlight if they blocked the trigger author or channel
        # Don't highlight if they blocked the entire category

        assert isinstance(message.channel, discord.abc.GuildChannel)

        if (
            member.id == message.author.id
            or settings["disabled"]
            or (
                message.channel.id in settings.get("blocked_channels", [])  # type: ignore
                or message.author.id in settings.get("blocked_users", [])  # type: ignore
                or (
                    message.channel.category
                    and message.channel.category.id in settings.get("blocked_channels", [])  # type: ignore
                )
            )
        ):
            return

        # Prepare highlight message
        initial_description = (
            f"In {message.channel.mention} for `{(message.guild.name)}`"
            f"you were highlighted with the word **{(word['word'])}**\n\n"
        )

        em = (
            discord.Embed(
                description="",
                timestamp=message.created_at,
                color=discord.Color.blurple(),
            )
            .set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url,
            )
            .set_footer(text="Triggered")
        )

        def esc(string: str) -> str:
            st = discord.utils.escape_markdown(string)
            st = string.replace(f"{word['word']}", f"**{word['word']}**")
            return st

        if len(message.content) > 2000:
            content = esc(message.content)[:2000]
        else:
            content = esc(message.content)

        timestamp = int(message.created_at.timestamp())
        em.description = f"<t:{timestamp}:T> `@{str(message.author):<15}`: {content}"

        # Add some history
        try:
            async for ms in message.channel.history(limit=3, before=message):
                content = esc(ms.content)
                timestamp = int(ms.created_at.timestamp())

                text = f"<t:{timestamp}:T> `@{str(ms.author):<15}`: {esc(content)}\n"

                if len(initial_description + em.description + text) <= 4096:
                    em.description = text + em.description
        except discord.HTTPException:
            pass

        em.description = initial_description + em.description

        # Send the highlight message
        try:
            await member.send(embed=em, view=JumpBackView(message.jump_url))
            log.info(
                "Sent highlight DM to user ID %s (guild ID %s)",
                member.id,
                message.guild.id,
            )

            self._highlight_batch.append(
                UpdateOne(
                    {"_id": word["user_id"]},
                    {
                        "$addToSet": {
                            "highlighted_messages": {
                                "guild_id": message.guild.id,
                                "channel_id": message.channel.id,
                                "message_id": message.id,
                                "author_id": message.author.id,
                                "user_id": word["user_id"],
                                "word": word["word"],
                                "invoked_at": message.created_at.isoformat(),
                                "content": message.content,
                            },
                        },
                    },
                    upsert=True,
                ),
            )
        except discord.Forbidden:
            log.warning("Forbidden to DM user ID %s (guild ID %s)", member.id, message.guild.id)

    @commands.group(name="highlight")
    async def highlight(self, ctx: Context):
        """Manage your highlight settings.

        Highlighting allows you to be notified when someone mentions a particular word in a message.
        That word can be anything, as it is set by you.

        You can also disable highlighting for a particular server, channel, or user.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @highlight.command(name="add")
    async def add(self, ctx: Context, *, word: str):
        """Add a word to your highlight word list.

        You will be notified when someone mentions this word in a message.

        **Examples:**
        - `[p]highlight add discord`
        """
        try:
            await ctx.author.send()
        except discord.HTTPException as exc:
            if exc.code == 50007:
                await ctx.send(
                    "You need to have DMs enabled for highlight notifications to work.",
                    delete_after=5,
                )

        word = word.lower()

        if discord.utils.escape_mentions(word) != word:
            await ctx.send("Your highlight word cannot contain any mentions.", delete_after=5)
        elif len(word) < 3:
            await ctx.send(
                "Your highlight word must contain at least 3 characters.",
                delete_after=5,
            )
        else:
            data = await self.bot.user_collections_ind.update_one(
                {"_id": ctx.author.id},
                {
                    "$addToSet": {"highlight_words": {"guild_id": ctx.guild.id, "word": word}},
                },
                upsert=True,
            )
            if data.modified_count == 0:
                await ctx.send(
                    f":x: You already have `{word}` in your highlight list.",
                    delete_after=5,
                )
                return

            if self.cached_words.get(ctx.author.id) is None:
                self.cached_words[ctx.author.id] = []

            self.cached_words[ctx.author.id].append({"user_id": ctx.author.id, "guild_id": ctx.guild.id, "word": word})
            await ctx.send(
                f":white_check_mark: Added `{word}` to your highlight list.",
                delete_after=5,
            )

    @highlight.command(
        name="remove",
        aliases=["delete", "rm", "del"],
    )
    async def remove(self, ctx: Context, *, word: str):
        """Remove a word from your highlight word list.

        **Examples:**
        - `[p]highlight remove discord`
        """
        word = word.lower()

        result_data = await self.bot.user_collections_ind.update_one(
            {"_id": ctx.author.id},
            {"$pull": {"highlight_words": {"guild_id": ctx.guild.id, "word": word}}},
            upsert=True,
        )

        if result_data.modified_count == 0:
            await ctx.send(
                "This word is not registered as a highlight word.",
                delete_after=5,
            )
        else:
            await ctx.send(
                f":white_check_mark: Removed `{word}` from your highlight list.",
                delete_after=5,
            )

        # Remove word from the cache, so we don't trigger deleted highlights
        self.cached_words[ctx.author.id].remove({"user_id": ctx.author.id, "guild_id": ctx.guild.id, "word": word})

    @highlight.command(
        name="show",
        aliases=["words", "list", "ls"],
    )
    async def show(self, ctx: Context):
        """See all your highlight words.

        **Examples:**
        - `[p]highlight show`
        """
        ls = self.cached_words.get(ctx.author.id, [])

        words = [word["word"] for word in ls if word["guild_id"] == ctx.guild.id and word["word"]]
        if not ls:
            await ctx.send(
                "You have no highlight words in this server.",
                delete_after=10,
            )
        else:
            em = discord.Embed(title="Highlight Words", color=discord.Color.blurple())
            em.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

            em.description = "`" + "`, `".join([str(i) for i in words]) + "`"

            await ctx.send(embed=em, delete_after=10)

    @highlight.command(name="clear")
    async def clear(self, ctx: Context, toggle: Literal["--all", "--guild-only"] = "--guild-only"):
        """Clear your highlight words in this server.

        **Examples:**
        - `[p]highlight clear`
        - `[p]highlight clear --all`
        - `[p]highlight clear --guild-only`
        """
        if toggle == "--all":
            result = await self.bot.user_collections_ind.update_one(
                {"_id": ctx.author.id},
                {"$set": {"highlight_words": []}},
                upsert=True,
            )
        elif toggle == "--guild-only":
            result = await self.bot.user_collections_ind.update_one(
                {"_id": ctx.author.id},
                {"$pull": {"highlight_words": {"guild_id": ctx.guild.id}}},
                upsert=True,
            )

        if result.modified_count == 0:
            await ctx.send(
                "You have no highlight words in this server to delete.",
                delete_after=5,
            )
            return

        await ctx.send(
            ":white_check_mark: Your highlight list has been cleared in this server.",
            delete_after=5,
        )

        # Remove words from the cache, so we don't trigger deleted highlights
        if toggle == "--all":
            self.cached_words[ctx.author.id] = []
        elif toggle == "--guild-only":
            self.cached_words[ctx.author.id] = [
                word for word in self.cached_words[ctx.author.id] if word["guild_id"] != ctx.guild.id
            ]

    @highlight.command(
        name="import",
        usage="<server ID>",
    )
    async def transfer(self, ctx: Context, from_guild: discord.Guild | int):
        """Import your highlight words from another server.

        **Examples:**
        - `[p]highlight import 1234567890`
        """
        if not self.cached_words.get(ctx.author.id):
            await ctx.send("You have no highlight words to import.", delete_after=5)
            return

        if getattr(from_guild, "id", from_guild) == ctx.guild.id:
            return await ctx.send(
                "You cannot import words from this guild, it must be another guild.",
                delete_after=5,
            )
        # {
        #   "_id": ...,
        #   "highlight_words": [
        #       {
        #           "guild_id": ...,
        #           "word": ...
        #       }
        #   ]
        # }

        # change guild_id to ctx.guild.id if guild_id == from_guild
        operations = [
            UpdateMany(
                {"_id": ctx.author.id, "highlight_words.guild_id": from_guild},
                {
                    "$set": {"highlight_words.$[elem].guild_id": ctx.guild.id},
                },
                array_filters=[{"elem.guild_id": from_guild}],
            ),
            UpdateOne(
                {"_id": ctx.author.id},
                {
                    "$addToSet": {
                        "highlight_words": {
                            "$each": [
                                word for word in self.cached_words.get(ctx.author.id, []) if word["guild_id"] == from_guild
                            ],
                        },
                    },
                },
            ),
        ]
        data: BulkWriteResult = await self.bot.user_collections_ind.bulk_write(operations)

        if data.modified_count == 0:
            return await ctx.send(
                "You have no highlight words in that server to import.",
                delete_after=5,
            )

        words_in_current_guild = [
            word["word"] for word in self.cached_words.get(ctx.author.id, []) if word["guild_id"] == ctx.guild.id
        ]
        to_transfer = []
        for word in self.cached_words.get(ctx.author.id, []):
            if word["guild_id"] == from_guild and word["word"] not in words_in_current_guild:
                word["guild_id"] = ctx.guild.id
                to_transfer.append(word)

        if to_transfer:
            await ctx.send(
                f":white_check_mark: Imported {plural(len(to_transfer))} from that server.",
                delete_after=5,
            )
        else:
            await ctx.send("You have no words to transfer from this server.", delete_after=5)

        for transfered in to_transfer:
            self.cached_words[ctx.author.id].append(transfered)

    async def do_block(
        self,
        user_id: int,
        entity: ENTITY_HINT,
    ) -> str:
        settings = await self.get_user_settings(user_id)

        if isinstance(entity, discord.User | discord.Member):
            if entity.id in settings["blocked_users"]:
                return "This user is already blocked."
            await self.bot.user_collections_ind.update_one(
                {"_id": user_id},
                {"$addToSet": {"highlight_settings.blocked_users": entity.id}},
                upsert=True,
            )
            return f":no_entry_sign: Blocked `{entity}`."

        elif isinstance(entity, discord.TextChannel | discord.CategoryChannel):
            if entity.id in settings["blocked_channels"]:
                return "This channel is already blocked."

            await self.bot.user_collections_ind.update_one(
                {"_id": user_id},
                {"$addToSet": {"highlight_settings.blocked_channels": entity.id}},
                upsert=True,
            )
            return f":no_entry_sign: Blocked {entity.mention}."

    async def do_unblock(self, user_id: int, entity: ENTITY_HINT) -> str:
        settings = await self.get_user_settings(user_id)

        if isinstance(entity, discord.User | discord.Member):
            if entity.id not in settings["blocked_users"]:
                return "This user is not blocked."

            await self.bot.user_collections_ind.update_one(
                {"_id": user_id},
                {"$pull": {"highlight_settings.blocked_users": entity.id}},
                upsert=True,
            )
            return f":white_check_mark: Unblocked `{entity}`."

        elif isinstance(entity, discord.TextChannel | discord.CategoryChannel):
            if entity.id not in settings["blocked_channels"]:
                return "This channel is not blocked."
            await self.bot.user_collections_ind.update_one(
                {"_id": user_id},
                {"$pull": {"highlight_settings.blocked_channels": entity.id}},
                upsert=True,
            )
            return f":white_check_mark: Unblocked {entity.mention}."

    async def get_entity(self, ctx: Context, entity: ENTITY_HINT) -> ENTITY_HINT | None:
        converters: list = [
            commands.MemberConverter,
            commands.UserConverter,
            commands.TextChannelConverter,
            commands.CategoryChannelConverter,
        ]

        for converter in converters:
            try:
                return await converter().convert(ctx, str(entity))
            except commands.BadArgument:
                pass

    # Block and unblock text commands
    @highlight.command(
        name="block",
        usage="<user or channel>",
        aliases=["ignore", "mute"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def block(self, ctx: Context, *, entity: discord.Member | discord.TextChannel):
        """Block a user or channel.

        This will prevent the bot from sending any highlight messages in the specified channel or from the specified user.

        **Examples:**
        - `[p]highlight block @user`
        - `[p]highlight block #channel`
        """
        converted_entity = await self.get_entity(ctx, entity)

        if not converted_entity or (
            isinstance(converted_entity, discord.TextChannel) and ctx.author not in converted_entity.members
        ):
            return await ctx.send(f"User or channel `{entity}` not found.", delete_after=5)

        result = await self.do_block(ctx.author.id, converted_entity)
        await ctx.send(result, delete_after=5)

    @highlight.command(
        name="unblock",
        usage="<user or channel>",
        aliases=["unmute"],
        invoke_without_command=True,
    )
    async def unblock(self, ctx: Context, *, entity: discord.Member | discord.TextChannel):
        """Unblock a user or channel.

        **Examples:**
        - `[p]highlight unblock @user`
        - `[p]highlight unblock #channel`"""
        converted_entity = await self.get_entity(ctx, entity)

        if not converted_entity:
            return await ctx.send(f"User or channel `{entity}` not found.", delete_after=5)

        result = await self.do_unblock(ctx.author.id, converted_entity)
        await ctx.send(result, delete_after=5)

    @highlight.group(
        name="blocked",
        invoke_without_command=True,
    )
    async def blocked(self, ctx: Context):
        """Show your blocked list.

        **Examples:**
        - `[p]highlight blocked`
        """
        settings = await self.get_user_settings(ctx.author.id)

        em = discord.Embed(description="", color=discord.Color.blurple())
        em.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        users = []
        for user_id in settings["blocked_users"]:
            user = await self.bot.fetch_user(user_id)
            guilds = [
                f"`{guild.name}`" for guild in self.bot.guilds if user in guild.members and ctx.author in guild.members
            ]

            if user and guilds:
                users.append(f"{user.mention} - {format_join(guilds, last='and')}")

        if users:
            em.add_field(name="Blocked Users", value="\n".join(users), inline=False)

        channels = []
        for channel_id in settings["blocked_channels"]:
            channel = self.bot.get_channel(channel_id)

            if channel and ctx.author in channel.guild.members:
                channels.append(f"{channel.mention} - `{channel.guild.name}`")

        if channels:
            em.add_field(name="Blocked Channels", value="\n".join(channels), inline=False)

        if settings["disabled"]:
            em.description = ":no_entry_sign: Highlight is currently disabled.\n\n"

        if not channels and not users:
            em.description += "No users or channels are blocked."

        await ctx.send(embed=em, delete_after=10)

    @blocked.command(name="clear")
    async def blocked_clear(self, ctx: Context):
        """Clear your blocked list.

        **Examples:**
        - `[p]highlight blocked clear`
        """
        data = await self.bot.user_collections_ind.update_one(
            {"_id": ctx.author.id},
            {
                "$set": {
                    "highlight_settings.blocked_users": [],
                    "highlight_settings.blocked_channels": [],
                },
            },
            upsert=True,
        )

        if data.modified_count == 0:
            return await ctx.send(
                f"{ctx.author.mention} You don't have any blocked users or channels.",
                delete_after=5,
            )

        await ctx.send(":white_check_mark: Your blocked users and channels have been cleared.")

    @highlight.command(name="enable")
    async def enable(self, ctx: Context):
        """Enable highlight for yourself.

        **Examples:**
        - `[p]highlight enable`
        """
        settings = await self.get_user_settings(ctx.author.id)
        if not settings["disabled"]:
            return await ctx.send("You already have highlight enabled.", delete_after=5)

        await self.bot.user_collections_ind.update_one(
            {"_id": ctx.author.id},
            {"$set": {"highlight_settings.disabled": False}},
            upsert=True,
        )

        await ctx.send(
            ":white_check_mark: Highlight has been enabled.",
            delete_after=5,
            ephemeral=True,
        )

    @highlight.command(name="disable", aliases=["dnd"])
    async def disable(self, ctx: Context):
        """Disable highlight for yourself.

        **Examples:**
        - `[p]highlight disable`
        """
        settings = await self.get_user_settings(ctx.author.id)
        if settings["disabled"]:
            return await ctx.send("You already have highlight disabled.", delete_after=5)

        await self.bot.user_collections_ind.update_one(
            {"_id": ctx.author.id},
            {"$set": {"highlight_settings.disabled": True}},
            upsert=True,
        )
        await ctx.send(
            ":no_entry_sign: Highlight has been disabled until you enable it again.",
            delete_after=5,
        )

    @add.before_invoke
    @remove.before_invoke
    @show.before_invoke
    @clear.before_invoke
    @transfer.before_invoke
    @block.before_invoke
    @unblock.before_invoke
    @blocked.before_invoke
    @blocked_clear.before_invoke
    @enable.before_invoke
    @disable.before_invoke
    async def ensure_privacy(self, ctx: Context):
        await ctx.message.delete(delay=0)

    async def bulk_insert(self):
        if self._highlight_batch:
            await self.bot.user_collections_ind.bulk_write(self._highlight_batch)
            self._highlight_batch = []

    @tasks.loop(seconds=20)
    async def bulk_insert_loop(self):
        async with self._batch_lock:
            await self.bulk_insert()

    @bulk_insert_loop.before_loop
    async def before_bulk_insert_loop(self):
        if not self.bot.is_ready():
            log.info("Waiting to start bulk insert loop")
            await self.bot.wait_until_ready()

        log.info("Starting bulk insert loop")
