from __future__ import annotations
from itertools import zip_longest

from typing import Any, Dict, Optional, Tuple, Union

from cogs.meta.robopage import SimplePages
from cogs.utils import method as mt

from core import Parrot, Cog, Context
from discord.ext import commands, tasks
import discord

import datetime
import asyncio

from utilities.checks import is_mod
from utilities.formats import TabularData
from utilities.time import ShortTime
from utilities.converters import convert_bool
from utilities.rankcard import rank_card

from pymongo import ReturnDocument


class afkFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    ignore_channel: Tuple[discord.TextChannel, ...] = []
    _global: Optional[convert_bool] = commands.flag(name="global", default=False)
    _for: Optional[ShortTime] = commands.flag(name="for", default=None)
    text: Optional[str] = None
    after: Optional[ShortTime] = None


REACTION_EMOJI = ["\N{UPWARDS BLACK ARROW}", "\N{DOWNWARDS BLACK ARROW}"]

OTHER_REACTION = {
    "INVALID": {"emoji": "\N{WARNING SIGN}", "color": 0xFFFFE0},
    "ABUSE": {"emoji": "\N{DOUBLE EXCLAMATION MARK}", "color": 0xFFA500},
    "INCOMPLETE": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "DECLINE": {"emoji": "\N{CROSS MARK}", "color": 0xFF0000},
    "APPROVED": {"emoji": "\N{WHITE HEAVY CHECK MARK}", "color": 0x90EE90},
}


class Utils(Cog):
    """Utilities for server, UwU"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.react_collection = bot.mongo.parrot_db["reactions"]
        self.collection = bot.mongo.parrot_db["timers"]
        self.lock = asyncio.Lock()
        self.message: Dict[int, Dict[str, Any]] = {}
        self.reminder_task.start()

    # async def setup_hook(self) -> None:
    #     self.reminder_task.start()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="sparkles_", id=892435276264259665)

    async def create_timer(
        self,
        *,
        expires_at: float,
        created_at: float = None,
        content: str = None,
        message: discord.Message,
        dm_notify: bool = False,
        is_todo: bool = False,
        **kw,
    ):
        """|coro|

        Master Function to register Timers.

        Parameters
        ----------
        expires_at: :class:`float`
            Timer exprire timestamp
        created_at: :class:`float`
            Timer created timestamp
        content: :class:`str`
            Content of the Timer
        message: :class:`discord.Message`
            Message Object
        dm_notify: :class:`bool`
            To notify the user or not
        is_todo: :class:`bool`
            To provide whether the timer related to `TODO`
        """
        embed: Dict[str, Any] = kw.get("embed_like") or kw.get("embed")
        mod_action: Dict[str, Any] = kw.get("mod_action")
        cmd_exec_str: str = kw.get("cmd_exec_str")

        post = {
            "_id": message.id,
            "expires_at": expires_at,
            "created_at": created_at or message.created_at.timestamp(),
            "content": content,
            "embed": embed,
            "messageURL": message.jump_url,
            "messageAuthor": message.author.id,
            "messageChannel": message.channel.id,
            "dm_notify": dm_notify,
            "is_todo": is_todo,
            "mod_action": mod_action,
            "cmd_exec_str": cmd_exec_str,
            "extra": kw.get("extra"),
            **kw,
        }
        await self.collection.insert_one(post)

    async def delete_timer(self, **kw):
        collection = self.collection
        await collection.delete_one(kw)

    @commands.group(aliases=["remind"], invoke_without_command=True)
    @Context.with_type
    async def remindme(
        self, ctx: Context, age: ShortTime, *, task: commands.clean_content = None
    ):
        """To make reminders as to get your tasks done on time"""
        if not ctx.invoked_subcommand:
            seconds = age.dt.timestamp()
            text = (
                f"{ctx.author.mention} alright, you will be mentioned in {ctx.channel.mention} at **<t:{int(seconds)}>**."
                f"To delete your reminder consider typing ```\n{ctx.clean_prefix}remind delete {ctx.message.id}```"
            )
            try:
                await ctx.reply(f"{ctx.author.mention} check your DM", delete_after=5)
                await ctx.author.send(text)
            except discord.Fobidden:
                await ctx.reply(text)
            await self.create_timer(
                expires_at=seconds,
                created_at=ctx.message.created_at.timestamp(),
                content=task or "...",
                message=ctx.message,
            )

    @remindme.command(name="list")
    @Context.with_type
    async def _list(self, ctx: Context):
        """To get all your reminders"""
        ls = []
        async for data in self.collection.find({"messageAuthor": ctx.author.id}):
            ls.append(
                f"<t:{int(data['expires_at'])}:R>\n> [{data['content']}]({data['messageURL']})"
            )
        if not ls:
            return await ctx.send(f"{ctx.author.mention} you don't have any reminders")
        p = SimplePages(ls, ctx=ctx, per_page=4)
        await p.start()

    @remindme.command(name="del", aliases=["delete"])
    @Context.with_type
    async def delremind(self, ctx: Context, message: int):
        """To delete the reminder"""
        await self.delete_timer(_id=message)
        await ctx.reply(f"{ctx.author.mention} deleted reminder of ID: **{message}**")

    @remindme.command(name="dm")
    @Context.with_type
    async def remindmedm(
        self, ctx: Context, age: ShortTime, *, task: commands.clean_content = None
    ):
        """Same as remindme, but you will be mentioned in DM. Make sure you have DM open for the bot"""
        seconds = age.dt.timestamp()
        text = (
            f"{ctx.author.mention} alright, you will be mentioned in your DM (Make sure you have your DM open for this bot) "
            f"within **<t:{int(seconds)}>**. To delete your reminder consider typing ```\n{ctx.clean_prefix}remind delete {ctx.message.id}```"
        )
        try:
            await ctx.reply(f"{ctx.author.mention} check your DM", delete_after=5)
            await ctx.author.send(text)
        except discord.Fobidden:
            await ctx.reply(text)
        await self.create_timer(
            expires_at=seconds,
            created_at=ctx.message.created_at.timestamp(),
            content=task or "...",
            message=ctx.message,
            dm_notify=True,
        )

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def tag(self, ctx: Context, *, tag: str = None):
        """Tag management, or to show the tag"""
        if not ctx.invoked_subcommand and tag is not None:
            await mt._show_tag(
                self.bot,
                ctx,
                tag,
                ctx.message.reference.resolved if ctx.message.reference else None,
            )

    @tag.command(name="create", aliases=["add"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_create(self, ctx: Context, tag: str, *, text: str):
        """To create tag. All tag have unique name"""
        await mt._create_tag(self.bot, ctx, tag, text)

    @tag.command(name="delete", aliases=["del"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_delete(self, ctx: Context, *, tag: str):
        """To delete tag. You must own the tag to delete"""
        await mt._delete_tag(self.bot, ctx, tag)

    @tag.command(name="editname")
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_name(self, ctx: Context, tag: str, *, name: str):
        """To edit the tag name. You must own the tag to edit"""
        await mt._name_edit(self.bot, ctx, tag, name)

    @tag.command(name="edittext")
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_text(self, ctx: Context, tag: str, *, text: str):
        """To edit the tag text. You must own the tag to edit"""
        await mt._text_edit(self.bot, ctx, tag, text)

    @tag.command(name="owner", aliases=["info"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_owner(self, ctx: Context, *, tag: str):
        """To check the tag details."""
        await mt._view_tag(self.bot, ctx, tag)

    @tag.command(name="snipe", aliases=["steal", "claim"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_claim(self, ctx: Context, *, tag: str):
        """To claim the ownership of the tag, if the owner of the tag left the server"""
        await mt._claim_owner(self.bot, ctx, tag)

    @tag.command(name="togglensfw", aliases=["nsfw", "tnsfw"])
    @commands.bot_has_permissions(embed_links=True)
    async def toggle_nsfw(self, ctx: Context, *, tag: str):
        """To enable/disable the NSFW of a Tag."""
        await mt._toggle_nsfw(self.bot, ctx, tag)

    @tag.command(name="give", aliases=["transfer"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_tranfer(self, ctx: Context, tag: str, *, member: discord.Member):
        """To transfer the ownership of tag you own to other member"""
        await mt._transfer_owner(self.bot, ctx, tag, member)

    @tag.command(name="all")
    @commands.bot_has_permissions(embed_links=True)
    async def tag_all(self, ctx: Context):
        """To show all tags"""
        await mt._show_all_tags(self.bot, ctx)

    @tag.command(name="mine")
    @commands.bot_has_permissions(embed_links=True)
    async def tag_mine(self, ctx: Context):
        """To show those tag which you own"""
        await mt._show_tag_mine(self.bot, ctx)

    @tag.command(name="raw")
    @commands.bot_has_permissions(embed_links=True)
    async def tag_raw(self, ctx: Context, *, tag: str):
        """To show the tag in raw format"""
        await mt._show_raw_tag(self.bot, ctx, tag)

    @commands.command()
    @commands.has_permissions(manage_messages=True, add_reactions=True)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @Context.with_type
    async def quickpoll(self, ctx: Context, *questions_and_choices: str):
        """
        To make a quick poll for making quick decision. 'Question must be in quotes' and Options, must, be, seperated, by, commans.
        Not more than 10 options. :)
        """

        def to_emoji(c):
            base = 0x1F1E6
            return chr(base + c)

        if len(questions_and_choices) < 3:
            return await ctx.send("Need at least 1 question with 2 choices.")
        if len(questions_and_choices) > 21:
            return await ctx.send("You can only have up to 20 choices.")

        question = questions_and_choices[0]
        choices = [(to_emoji(e), v) for e, v in enumerate(questions_and_choices[1:])]

        await ctx.message.delete(delay=0)

        body = "\n".join(f"{key}: {c}" for key, c in choices)
        poll = await ctx.send(f"**Poll: {question}**\n\n{body}")
        await ctx.bulk_add_reactions(poll, *[emoji for emoji, _ in choices])

    @commands.group(name="todo", invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def todo(self, ctx: Context):
        """For making the TODO list"""
        if not ctx.invoked_subcommand:
            await mt._list_todo(self.bot, ctx)

    @todo.command(name="show")
    @commands.bot_has_permissions(embed_links=True)
    async def todu_show(self, ctx: Context, *, name: str):
        """To show the TODO task you created"""
        await mt._show_todo(self.bot, ctx, name)

    @todo.command(name="create")
    @commands.bot_has_permissions(embed_links=True)
    async def todo_create(self, ctx: Context, name: str, *, text: str):
        """To create a new TODO"""
        await mt._create_todo(self.bot, ctx, name, text)

    @todo.command(name="editname")
    @commands.bot_has_permissions(embed_links=True)
    async def todo_editname(self, ctx: Context, name: str, *, new_name: str):
        """To edit the TODO name"""
        await mt._update_todo_name(self.bot, ctx, name, new_name)

    @todo.command(name="edittext")
    @commands.bot_has_permissions(embed_links=True)
    async def todo_edittext(self, ctx: Context, name: str, *, text: str):
        """To edit the TODO text"""
        await mt._update_todo_text(self.bot, ctx, name, text)

    @todo.command(name="delete")
    @commands.bot_has_permissions(embed_links=True)
    async def delete_todo(self, ctx: Context, *, name: str):
        """To delete the TODO task"""
        await mt._delete_todo(self.bot, ctx, name)

    @todo.command(name="settime", aliases=["set-time"])
    @commands.bot_has_permissions(embed_links=True)
    async def settime_todo(self, ctx: Context, name: str, *, deadline: ShortTime):
        """To set timer for your Timer"""
        await mt._set_timer_todo(self.bot, ctx, name, deadline.dt.timestamp())

    @commands.group(invoke_without_command=True)
    async def afk(self, ctx: Context, *, text: commands.clean_content = None):
        """To set AFK

        AFK will be removed once you message.
        If provided permissions, bot will add `[AFK]` as the prefix in nickname.
        The deafult AFK is on Server Basis
        """
        try:
            nick = f"[AFK] {ctx.author.display_name}"
            if len(nick) <= 32:  # discord limitation
                await ctx.author.edit(nick=nick, reason=f"{ctx.author} set their AFK")
        except discord.Forbidden:
            pass
        if not ctx.invoked_subcommand:
            if text and text.split(" ")[0].lower() in (
                "global",
                "till",
                "ignore",
                "after",
                "custom",
            ):
                return
            post = {
                "_id": ctx.message.id,
                "messageURL": ctx.message.jump_url,
                "messageAuthor": ctx.author.id,
                "guild": ctx.guild.id,
                "channel": ctx.channel.id,
                "pings": [],
                "at": ctx.message.created_at.timestamp(),
                "global": False,
                "text": text or "AFK",
                "ignoredChannel": [],
            }
            await ctx.send(f"{ctx.author.mention} AFK: {text or 'AFK'}")
            await self.bot.mongo.parrot_db.afk.insert_one({**post})
            self.bot.afk.add(ctx.author.id)

    @afk.command(name="global")
    async def _global(self, ctx: Context, *, text: commands.clean_content = None):
        """To set the AFK globally (works only if the bot can see you)"""
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await self.bot.mongo.parrot_db.afk.insert_one({**post})
        await ctx.send(f"{ctx.author.mention} AFK: {text or 'AFK'}")
        self.bot.afk.add(ctx.author.id)

    @afk.command(name="for")
    async def afk_till(
        self, ctx: Context, till: ShortTime, *, text: commands.clean_content = None
    ):
        """To set the AFK time"""
        if till.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await self.bot.mongo.parrot_db.afk.insert_one({**post})
        self.bot.afk.add(ctx.author.id)
        await ctx.send(
            f"{ctx.author.mention} AFK: {text or 'AFK'}\n> Your AFK status will be removed {discord.utils.format_dt(till.dt, 'R')}"
        )
        await self.create_timer(
            expires_at=till.dt.timestamp(),
            created_at=ctx.message.created_at.timestamp(),
            extra={"name": "REMOVE_AFK", "main": {**post}},
            message=ctx.message,
        )

    @afk.command(name="after")
    async def afk_after(
        self, ctx: Context, after: ShortTime, *, text: commands.clean_content = None
    ):
        """To set the AFK future time"""
        if after.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await ctx.send(
            f"{ctx.author.mention} AFK: {text or 'AFK'}\n> Your AFK status will be set {discord.utils.format_dt(after.dt, 'R')}"
        )
        await self.create_timer(
            expires_at=after.dt.timestamp(),
            created_at=ctx.message.created_at.timestamp(),
            extra={"name": "SET_AFK", "main": {**post}},
            message=ctx.message,
        )

    @afk.command(name="custom")
    async def custom_afk(self, ctx: Context, *, flags: afkFlags):
        """To set the custom AFK"""
        payload = {
            "text": flags.text or "AFK",
            "ignoredChannel": (
                [c.id for c in flags.ignore_channel] if flags.ignore_channel else []
            ),
            "global": flags._global,
            "at": ctx.message.created_at.timestamp(),
            "guild": ctx.guild.id,
            "messageAuthor": ctx.author.id,
            "messageURL": ctx.message.jump_url,
            "channel": ctx.channel.id,
            "_id": ctx.message.id,
            "pings": [],
        }

        if flags.after and flags._for:
            return await ctx.send(
                f"{ctx.author.mention} can not have both `after` and `for` argument"
            )

        if flags.after:
            await self.create_timer(
                expires_at=flags.after.dt.timestamp(),
                created_at=ctx.message.created_at.timestamp(),
                extra={"name": "SET_AFK", "main": {**payload}},
                message=ctx.message,
            )
            await ctx.send(
                f"{ctx.author.mention} AFK: {flags.text or 'AFK'}\n> Your AFK status will be set {discord.utils.format_dt(flags.after.dt, 'R')}"
            )
            return
        if flags._for:
            await self.create_timer(
                expires_at=flags._for.dt.timestamp(),
                created_at=ctx.message.created_at.timestamp(),
                extra={"name": "REMOVE_AFK", "main": {**payload}},
                message=ctx.message,
            )
            await self.bot.mongo.parrot_db.afk.insert_one({**payload})
            self.bot.afk.add(ctx.author.id)
            await ctx.send(
                f"{ctx.author.mention} AFK: {flags.text or 'AFK'}\n> Your AFK status will be removed {discord.utils.format_dt(flags._for.dt, 'R')}"
            )
            return
        await self.bot.mongo.parrot_db.afk.insert_one({**payload})
        self.bot.afk.add(ctx.author.id)
        await ctx.send(f"{ctx.author.mention} AFK: {flags.text or 'AFK'}")

    @tasks.loop(seconds=3)
    async def reminder_task(self):
        async with self.lock:
            async for data in self.collection.find(
                {"expires_at": {"$lte": datetime.datetime.utcnow().timestamp()}}
            ):
                cog = self.bot.get_cog("EventCustom")
                await self.collection.delete_one({"_id": data["_id"]})
                await cog.on_timer_complete(**data)

    @reminder_task.before_loop
    async def before_reminder_task(self):
        await self.bot.wait_until_ready()

    @commands.command(aliases=["level"])
    @commands.bot_has_permissions(attach_files=True)
    async def rank(self, ctx: Context, *, member: discord.Member = None):
        """To get the level of the user"""
        member = member or ctx.author
        try:
            self.bot.server_config[ctx.guild.id]["leveling"]["enabled"]
        except KeyError:
            return await ctx.send(
                f"{ctx.author.mention} leveling system is disabled in this server"
            )
        else:
            collection = self.bot.mongo.leveling[f"{member.guild.id}"]
            if data := await collection.find_one_and_update(
                {"_id": member.id},
                {"$inc": {"xp": 0}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            ):
                level = int((data["xp"] // 42) ** 0.55)
                xp = self.__get_required_xp(level + 1)
                rank = await self.__get_rank(collection=collection, member=member)
                file = await rank_card(
                    level,
                    rank,
                    member,
                    current_xp=data["xp"],
                    custom_background="#000000",
                    xp_color="#FFFFFF",
                    next_level_xp=xp,
                )
                await ctx.reply(file=file)
                return
            if ctx.author.id == member.author.id:
                return await ctx.reply(
                    f"{ctx.author.mention} you don't have any xp yet. Consider sending some messages"
                )
            return await ctx.reply(
                f"{ctx.author.mention} **{member}** don't have any xp yet."
            )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def lb(self, ctx: Context, *, limit: Optional[int] = None):
        """To display the Leaderboard"""
        limit = limit or 10
        collection = self.bot.mongo.leveling[f"{ctx.guild.id}"]
        entries = await self.__get_entries(
            collection=collection, limit=limit, guild=ctx.guild
        )
        pages = SimplePages(entries, ctx=ctx, per_page=10)
        await pages.start()

    def __get_required_xp(self, level: int) -> int:
        xp = 0
        while True:
            xp += 12
            lvl = int((xp // 42) ** 0.55)
            if lvl == level:
                return int(xp)

    async def __get_rank(self, *, collection, member: discord.Member):
        countr = 0

        # you can't use `enumerate`
        async for data in collection.find({}, sort=[("xp", -1)]):
            countr += 1
            if data["_id"] == member.id:
                return countr

    async def __get_entries(self, *, collection, limit: int, guild: discord.Guild):
        ls = []
        async for data in collection.find({}, limit=limit, sort=[("xp", -1)]):
            if member := await self.bot.get_or_fetch_member(guild, data["_id"]):
                ls.append(f"{member} (`{member.id}`)")
        return ls

    async def __fetch_suggestion_channel(
        self, guild: discord.Guild
    ) -> Optional[discord.TextChannel]:
        try:
            ch_id: Optional[int] = self.bot.server_config[guild.id][
                "suggestion_channel"
            ]
        except KeyError:
            raise commands.BadArgument("No suggestion channel is setup")
        else:
            if not ch_id:
                raise commands.BadArgument("No suggestion channel is setup")
            ch: Optional[discord.TextChannel] = self.bot.get_channel(ch_id)
            if ch is None:
                await self.bot.wait_until_ready()
                ch: discord.TextChannel = await self.bot.fetch_channel(ch_id)

            return ch

    async def get_or_fetch_message(
        self, msg_id: int, *, channel: discord.TextChannel = None
    ) -> Optional[discord.Message]:
        try:
            self.message[msg_id]
        except KeyError:
            return await self.__fetch_message_from_channel(message=msg_id, channel=channel)
        else:
            return self.message[msg_id]["message"]

    async def __fetch_message_from_channel(
        self, *, message: int, channel: discord.TextChannel
    ):
        async for msg in channel.history(
            limit=1,
            before=discord.Object(message + 1),
            after=discord.Object(message - 1),
        ):
            if msg:
                payload = {
                    "message_author": msg.author,
                    "message": msg,
                    "message_downvote": self.__get_emoji_count_from__msg(
                        msg, emoji="\N{DOWNWARDS BLACK ARROW}"
                    ),
                    "message_upvote": self.__get_emoji_count_from__msg(
                        msg, emoji="\N{UPWARDS BLACK ARROW}"
                    ),
                }
                self.message[message] = payload
                return msg

    def __get_emoji_count_from__msg(
        self,
        msg: discord.Message,
        *,
        emoji: Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        for reaction in msg.reactions:
            if str(reaction.emoji) == str(emoji):
                return reaction.count

    async def __suggest(
        self, content: Optional[str] = None, *, embed: discord.Embed, ctx: Context
    ) -> discord.Message:

        channel = await self.__fetch_suggestion_channel(ctx.guild)
        msg: discord.Message = await channel.send(content, embed=embed)

        payload = {
            "message_author": msg.author,
            "message_downvote": 0,
            "message_upvote": 0,
            "message": msg,
        }
        self.message[msg.id] = payload

        await ctx.bulk_add_reactions(msg, *REACTION_EMOJI)
        await msg.create_thread(name=f"Suggestion {ctx.author}")
        return msg

    async def __notify_on_suggestion(
        self, ctx: Context, *, message: discord.Message
    ) -> None:
        jump_url: str = message.jump_url
        _id: int = message.id
        content = (
            f"{ctx.author.mention} you suggestion being posted.\n"
            f"To delete the suggestion typing `{ctx.clean_prefix}suggest delete {_id}`\n"
            f"> {jump_url}"
        )
        try:
            await ctx.author.send(content)
        except discord.Forbidden:
            pass

    async def __notify_user(
        self,
        ctx: Context,
        user: discord.Member,
        *,
        message: discord.Message,
        remark: str,
    ) -> None:
        remark = remark or "No remark was given"

        content = (
            f"{user.mention} you suggestion of ID: {message.id} had being updated.\n"
            f"By: {ctx.author} (`{ctx.author.id}`)\n"
            f"Remark: {remark}\n"
            f"> {message.jump_url}"
        )
        try:
            await ctx.author.send(content)
        except discord.Forbidden:
            pass

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    async def suggest(self, ctx: Context, *, suggestion: commands.clean_content):
        """Suggest something. Abuse of the command may result in required mod actions"""

        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                description=suggestion, timestamp=ctx.message.created_at, color=0xADD8E6
            )
            embed.set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(
                text=f"Author ID: {ctx.author.id}", icon_url=ctx.guild.icon.url
            )
            msg = await self.__suggest(ctx=ctx, embed=embed)
            await self.__notify_on_suggestion(ctx, message=msg)
            await ctx.message.delete(delay=0)

    @suggest.command(name="delete")
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(read_message_history=True)
    async def suggest_delete(self, ctx: Context, *, messageID: int):
        """To delete the suggestion you suggested"""

        msg: Optional[discord.Message] = await self.get_or_fetch_message(messageID)
        if not msg:
            return await ctx.send(
                f"Can not find message of ID `{messageID}`. Probably already deleted, or `{messageID}` is invalid"
            )

        if msg.author.id != self.bot.user.id:
            return await ctx.send(f"Invalid `{messageID}`")

        if ctx.channel.permissions_for(ctx.author).manage_messages:
            await msg.delete(delay=0)
            await ctx.send("Done", delete_after=5)
            return

        if int(msg.embeds[0].footer.text.split(":")[1]) != ctx.author.id:
            return await ctx.send("You don't own that 'suggestion'")

        await msg.delete(delay=0)
        await ctx.send("Done", delete_after=5)

    @suggest.command(name="stats")
    @commands.cooldown(1, 60, commands.BucketType.member)
    async def suggest_status(self, ctx: Context, *, messageID: int):
        """To get the statistics os the suggestion"""

        msg: Optional[discord.Message] = await self.get_or_fetch_message(messageID)
        if not msg:
            return await ctx.send(
                f"Can not find message of ID `{messageID}`. Probably already deleted, or `{messageID}` is invalid"
            )
        PAYLOAD: Dict[str, Any] = self.message[msg.id]

        if msg.author.id != self.bot.user.id:
            return await ctx.send(f"Invalid `{messageID}`")

        table = TabularData()

        upvoter = [PAYLOAD["message_downvote"]]
        downvoter = [PAYLOAD["message_upvote"]]

        table.set_columns(["Upvote", "Downvote"])
        ls = list(zip_longest(upvoter, downvoter, fillvalue=""))
        table.add_rows(ls)

        # conflict = [i for i in upvoter if i in downvoter]

        embed = discord.Embed()
        embed.description = f"```\n{table.render()}```"
        # if conflict:
        #     embed.add_field(name=f"Conflit in Reaction: {len(conflict)}", value=", ".join([str(i) for i in conflict]))
        if msg.content:
            embed.add_field(name="Flagged", value=msg.content)
        await ctx.send(content=msg.jump_url, embed=embed)

    @suggest.command(name="note", aliases=["remark"])
    @commands.check_any(commands.has_permissions(manage_messages=True), is_mod())
    async def add_note(self, ctx: Context, messageID: int, *, remark: str):
        """To add a note in suggestion embed"""
        msg: Optional[discord.Message] = await self.get_or_fetch_message(messageID)
        if not msg:
            return await ctx.send(
                f"Can not find message of ID `{messageID}`. Probably already deleted, or `{messageID}` is invalid"
            )

        if msg.author.id != self.bot.user.id:
            return await ctx.send(f"Invalid `{messageID}`")

        embed: discord.Embed = msg.embeds[0]
        embed.clear_fields()
        embed.add_field(name="Remark", value=remark[:250])
        await msg.edit(content=msg.content, embed=embed)

        user_id = int(embed.footer.text.split(":")[1])
        user = ctx.guild.get_member(user_id)
        await self.__notify_user(ctx, user, message=msg, remark=remark)

        await ctx.send("Done", delete_after=5)

    @suggest.command(name="clear", aliases=["cls"])
    @commands.check_any(commands.has_permissions(manage_messages=True), is_mod())
    async def clear_suggestion_embed(
        self, ctx: Context, messageID: int, *, remark: str
    ):
        """To remove all kind of notes and extra reaction from suggestion embed"""
        msg: Optional[discord.Message] = await self.get_or_fetch_message(messageID)
        if not msg:
            return await ctx.send(
                f"Can not find message of ID `{messageID}`. Probably already deleted, or `{messageID}` is invalid"
            )

        if msg.author.id != self.bot.user.id:
            return await ctx.send(f"Invalid `{messageID}`")

        embed: discord.Embed = msg.embeds[0]
        embed.clear_fields()
        embed.color = 0xADD8E6
        await msg.edit(embed=embed, content=None)

        for reaction in msg.reactions:
            if str(reaction.emoji) not in REACTION_EMOJI:
                await msg.clear_reaction(reaction.emoji)

        await ctx.send("Done", delete_after=5)

    @suggest.command(name="flag")
    @commands.check_any(commands.has_permissions(manage_messages=True), is_mod())
    async def suggest_flag(self, ctx: Context, messageID: int, flag: str):
        """To flag the suggestion.

        Avalibale Flags :-
        - INVALID
        - ABUSE
        - INCOMPLETE
        - DECLINE
        - APPROVED
        """
        msg: Optional[discord.Message] = await self.get_or_fetch_message(messageID)
        if not msg:
            return await ctx.send(
                f"Can not find message of ID `{messageID}`. Probably already deleted, or `{messageID}` is invalid"
            )

        if msg.author.id != self.bot.user.id:
            return await ctx.send(f"Invalid `{messageID}`")

        flag = flag.upper()
        try:
            payload: Dict[str, Union[int, str]] = OTHER_REACTION[flag]
        except KeyError:
            return await ctx.send("Invalid Flag")

        embed: discord.Embed = msg.embeds[0]
        embed.color = payload["color"]

        user_id = int(embed.footer.text.split(":")[1])
        user: discord.Member = ctx.guild.get_member(user_id)
        await self.__notify_user(ctx, user, message=msg, remark="")

        content = f"Flagged: {flag} | {payload['emoji']}"
        await msg.edit(content=content, embed=embed)
        await ctx.send("Done", delete_after=5)

    @Cog.listener(name="on_raw_message_delete")
    async def suggest_msg_delete(self, payload) -> None:
        if payload.message_id in self.message:
            del self.message[payload.message_id]

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.author.bot and message.guild is None:
            return

        ls = await self.bot.mongo.parrot_db.server_config.find_one(
            {"_id": message.guild.id, "suggestion_channel": message.channel.id}
        )
        if not ls:
            return

        if message.channel.id != ls["suggestion_channel"]:
            return

        await self.__parse_mod_action(message)

        context: Context = await self.bot.get_context(message, cls=Context)
        await self.suggest(context, suggestion=message.content)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await mt.add_reactor(self.bot, payload)

        if payload.message_id not in self.message:
            return

        if str(payload.emoji) not in REACTION_EMOJI:
            return

        if str(payload.emoji) == "\N{UPWARDS BLACK ARROW}":
            self.message[payload.message_id]["message_upvote"] += 1
        if str(payload.emoji) == "\N{DOWNWARDS BLACK ARROW}":
            self.message[payload.message_id]["message_downvote"] += 1

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await mt.remove_reactor(self.bot, payload)

        if payload.message_id not in self.message:
            return

        if str(payload.emoji) not in REACTION_EMOJI:
            return

        if str(payload.emoji) == "\N{UPWARDS BLACK ARROW}":
            self.message[payload.message_id]["message_upvote"] -= 1
        if str(payload.emoji) == "\N{DOWNWARDS BLACK ARROW}":
            self.message[payload.message_id]["message_downvote"] -= 1

    async def __parse_mod_action(self, message: discord.Message) -> None:
        if not self.__is_mod(message.author):
            return

        if message.content.upper() in OTHER_REACTION:
            context: Context = await self.bot.get_context(message, cls=Context)
            # cmd: commands.Command = self.bot.get_command("suggest flag")

            msg: Union[
                discord.Message, discord.DeletedReferencedMessage
            ] = message.reference.resolved

            if not isinstance(msg, discord.discord.Message):
                return

            if msg.author.id != self.bot.user.id:
                return

            # await context.invoke(cmd, msg.id, message.content.upper())
            await self.suggest_flag(context, msg.id, message.content.upper())

    def __is_mod(self, member: discord.Member) -> bool:
        try:
            role_id = self.bot.server_config[member.guild.id]["mod_role"]
            if role_id is None:
                perms: discord.Permissions = member.guild_permissions
                if any([perms.manage_guild, perms.manage_messages]):
                    return True
            return member._roles.has(role_id)
        except KeyError:
            return False

    @commands.group(name="giveaway", aliases=["gw"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: Context):
        """To create giveaway"""
        if not ctx.invoked_subcommand:
            post = await mt._make_giveaway(ctx)
            await self.create_timer(**post)

    @giveaway.command(name="drop")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_drop(
        self,
        ctx: Context,
        duration: ShortTime,
        winners: Optional[int] = 1,
        *,
        prize: str = None,
    ):
        """To create giveaway in quick format"""
        post = await mt._make_giveaway_drop(
            ctx, duration=duration, winners=winners, prize=prize
        )
        await self.create_timer(**post)

    @giveaway.command(name="end")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_end(self, ctx: Context, messageID: int):
        """To end the giveaway"""
        if data := await self.bot.mongo.parrot_db.giveaway.find_one_and_update(
            {"message_id": messageID, "status": "ONGOING"}, {"$set": {"status": "END"}}
        ):

            await self.collection.delete_one({"_id": messageID})

            member_ids = await mt.end_giveaway(self.bot, **data)
            if not member_ids:
                return await ctx.send(f"{ctx.author.mention} no winners!")

            joiner = ">, <@".join([str(i) for i in member_ids])

            await ctx.send(
                f"Congrats <@{joiner}> you won {data.get('prize')}\n"
                f"> https://discord.com/channels/{data.get('guild_id')}/{data.get('giveaway_channel')}/{data.get('message_id')}"
            )

    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_reroll(self, ctx: Context, messageID: int, winners: int = 1):
        """To end the giveaway"""
        if data := await self.bot.mongo.parrot_db.giveaway.find_one(
            {"message_id": messageID}
        ):

            if data["status"] == "ONGOING":
                return await ctx.send(
                    f"{ctx.author.mention} can not reroll the ongoing giveaway"
                )

            data["winners"] = winners

            member_ids = await mt.end_giveaway(self.bot, **data)

            if not member_ids:
                return await ctx.send(f"{ctx.author.mention} no winners!")

            joiner = ">, <@".join([str(i) for i in member_ids])

            await ctx.send(
                f"Contragts <@{joiner}> you won {data.get('prize')}\n"
                f"> https://discord.com/channels/{data.get('guild_id')}/{data.get('giveaway_channel')}/{data.get('message_id')}"
            )
            return
        await ctx.send(
            f"{ctx.author.mention} no giveaway found on message ID: `{messageID}`"
        )
