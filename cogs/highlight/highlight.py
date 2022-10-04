from __future__ import annotations
import asyncio
import re
from typing import TYPE_CHECKING, Dict, List, Optional, TypeAlias, Union

from discord.ext import commands
import discord

from core import Parrot, Context, Cog

if TYPE_CHECKING:
    from pymongo.collection import Collection
    from pymongo.results import UpdateResult

    MongoCollection: TypeAlias = Collection


class Highlight(Cog):
    """Manage your highlights and hashtags"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self._highlight_collection: MongoCollection = self.bot.mongo["highlight"][
            "highlight"
        ]
        self._hashtag_collection: MongoCollection = self.bot.mongo["highlight"][
            "hashtag"
        ]

        self.__caching_highlight: Dict[int, List[str]] = {}
        self.__caching_hashtag: Dict[str, List[int]] = {}

    @commands.group(invoke_without_command=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def highlight(self, ctx: Context):
        """Highlight commands"""
        if ctx.invoked_subcommand is None:
            await ctx.bot.invoke_help_command(ctx)

    @highlight.command()
    async def add(self, ctx: Context, *, word: str):
        """Add a word to highlight"""
        await ctx.message.delete(delay=3)
        if len(word) < 3:
            return await ctx.send(
                f"{ctx.author.mention} Word must be at least 3 characters long"
            )

        data_changed: UpdateResult = await self._highlight_collection.update_one(
            {"_id": ctx.author.id},
            {"$addToSet": {"words": word}},
            upsert=True,
        )
        if data_changed.modified_count:
            await ctx.send(f"{ctx.author.mention} Word added to highlight list")
        else:
            await ctx.send(f"{ctx.author.mention} Word already in highlight list")

    @highlight.command()
    async def remove(self, ctx: Context, *, word: str):
        """Remove a word from highlight"""
        await ctx.message.delete(delay=3)
        if len(word) < 3:
            return await ctx.send(
                f"{ctx.author.mention} Word must be at least 3 characters long"
            )

        data_changed: UpdateResult = await self._highlight_collection.update_one(
            {"_id": ctx.author.id},
            {"$pull": {"words": word}},
        )
        if data_changed.modified_count:
            await ctx.send(f"{ctx.author.mention} Word removed from highlight list")
        else:
            await ctx.send(f"{ctx.author.mention} Word not in highlight list")

    @highlight.command(name="list")
    async def _list(self, ctx: Context):
        """List all words in highlight"""
        await ctx.message.delete(delay=3)
        data: dict = await self._highlight_collection.find_one({"_id": ctx.author.id})
        if not data:
            return await ctx.send(
                f"{ctx.author.mention} You have no words in highlight list"
            )

        await ctx.paginate(data["words"])

    @highlight.command()
    async def clear(self, ctx: Context):
        """Clear all words in highlight"""
        await ctx.message.delete(delay=3)
        data_changed: UpdateResult = await self._highlight_collection.update_one(
            {"_id": ctx.author.id}, {"$set": {"words": []}}
        )
        if data_changed.modified_count:
            await ctx.send(f"{ctx.author.mention} Highlight list cleared")
        else:
            await ctx.send(f"{ctx.author.mention} Highlight list already empty")

    @highlight.command(name="ignore")
    async def ignore_role_channel(
        self, ctx: Context, *, target: Union[discord.Role, discord.TextChannel]
    ):
        """Ignore a role or channel"""
        await ctx.message.delete(delay=3)
        if isinstance(target, discord.Role):
            data_changed: UpdateResult = await self._highlight_collection.update_one(
                {"_id": ctx.author.id},
                {"$addToSet": {"ignored_roles": target.id}},
                upsert=True,
            )
            if data_changed.modified_count:
                await ctx.send(f"{ctx.author.mention} Role added to ignored list")
            else:
                await ctx.send(f"{ctx.author.mention} Role already in ignored list")
        elif isinstance(target, discord.TextChannel):
            data_changed: UpdateResult = await self._highlight_collection.update_one(
                {"_id": ctx.author.id},
                {"$addToSet": {"ignored_channels": target.id}},
                upsert=True,
            )
            if data_changed.modified_count:
                await ctx.send(f"{ctx.author.mention} Channel added to ignored list")
            else:
                await ctx.send(f"{ctx.author.mention} Channel already in ignored list")

    @highlight.command(name="unignore")
    async def unignore_role_channel(
        self, ctx: Context, *, target: Union[discord.Role, discord.TextChannel]
    ):
        """Unignore a role or channel"""
        await ctx.message.delete(delay=3)
        if isinstance(target, discord.Role):
            data_changed: UpdateResult = await self._highlight_collection.update_one(
                {"_id": ctx.author.id},
                {"$pull": {"ignored_roles": target.id}},
            )
            if data_changed.modified_count:
                await ctx.send(f"{ctx.author.mention} Role removed from ignored list")
            else:
                await ctx.send(f"{ctx.author.mention} Role not in ignored list")
        elif isinstance(target, discord.TextChannel):
            data_changed: UpdateResult = await self._highlight_collection.update_one(
                {"_id": ctx.author.id},
                {"$pull": {"ignored_channels": target.id}},
            )
            if data_changed.modified_count:
                await ctx.send(
                    f"{ctx.author.mention} Channel removed from ignored list"
                )
            else:
                await ctx.send(f"{ctx.author.mention} Channel not in ignored list")

    @highlight.command(name="ignorelist")
    async def ignore_list(self, ctx: Context):
        """List all ignored roles and channels"""
        await ctx.message.delete(delay=3)
        data: dict = await self._highlight_collection.find_one({"_id": ctx.author.id})
        if not data:
            return await ctx.send(
                f"{ctx.author.mention} You have no ignored roles or channels"
            )

        ignored_roles: List[str] = []
        ignored_channels: List[str] = []
        for role_id in data.get("ignored_roles", []):
            if role := ctx.guild.get_role(role_id):
                ignored_roles.append(role.name)
        for channel_id in data.get("ignored_channels", []):
            if channel := self.bot.get_channel(channel_id):
                ignored_channels.append(channel.name)

        if ignored_roles:
            await ctx.paginate(ignored_roles)
        if ignored_channels:
            await ctx.paginate(ignored_channels)

    @commands.group(invoke_without_command=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hashtag(self, ctx: Context):
        """Hashtag commands"""
        if ctx.invoked_subcommand is None:
            await ctx.bot.invoke_help_command(ctx)

    @hashtag.command(name="follow")
    async def follow_hashtag(self, ctx: Context, hashtag: str):
        """Follow a hashtag"""
        if hashtag.startswith("#"):
            hashtag = hashtag[1:]
        await ctx.message.delete(delay=3)
        data_changed: UpdateResult = await self._hashtag_collection.update_one(
            {"_id": hashtag},
            {"$addToSet": {"followers": ctx.author.id}},
            upsert=True,
        )
        if data_changed.modified_count:
            await ctx.send(f"{ctx.author.mention} You are now following **#{hashtag}**")
        else:
            await ctx.send(
                f"{ctx.author.mention} You are already following **#{hashtag}**"
            )

    @hashtag.command(name="unfollow")
    async def unfollow_hashtag(self, ctx: Context, hashtag: str):
        """Unfollow a hashtag"""
        if hashtag.startswith("#"):
            hashtag = hashtag[1:]
        await ctx.message.delete(delay=3)
        data_changed: UpdateResult = await self._hashtag_collection.update_one(
            {"_id": hashtag},
            {"$pull": {"followers": ctx.author.id}},
        )
        if data_changed.modified_count:
            await ctx.send(
                f"{ctx.author.mention} You are no longer following **#{hashtag}**"
            )
        else:
            await ctx.send(f"{ctx.author.mention} You are not following **#{hashtag}**")

    @hashtag.command(name="create")
    async def create_hashtag(self, ctx: Context, hashtag: str):
        """Create a hashtag"""
        if hashtag.startswith("#"):
            hashtag = hashtag[1:]
        await ctx.message.delete(delay=3)
        if data := await self._hashtag_collection.find_one({"_id": hashtag}):
            return await ctx.send(f"{ctx.author.mention} **#{hashtag}** already exists")
        await self._hashtag_collection.insert_one(
            {"_id": hashtag, "followers": [], "messages": [], "owner": ctx.author.id}
        )
        await ctx.send(f"{ctx.author.mention} **#{hashtag}** created")

    @hashtag.command(name="delete")
    async def delete_hashtag(self, ctx: Context, hashtag: str):
        """Delete a hashtag"""
        if hashtag.startswith("#"):
            hashtag = hashtag[1:]
        await ctx.message.delete(delay=3)
        if data := await self._hashtag_collection.find_one({"_id": hashtag}):
            if data["owner"] != ctx.author.id:
                return await ctx.send(
                    f"{ctx.author.mention} You do not own **#{hashtag}**"
                )
            await self._hashtag_collection.delete_one({"_id": hashtag})
            await ctx.send(f"{ctx.author.mention} **#{hashtag}** deleted")
        else:
            await ctx.send(f"{ctx.author.mention} **#{hashtag}** does not exist")

    @hashtag.command(name="list")
    async def list_hashtags(self, ctx: Context):
        """List all hashtags"""
        await ctx.message.delete(delay=3)
        hashtags: List[str] = []
        async for document in self._hashtag_collection.find():
            hashtags.append(f"**#{document['_id']}**")
        await ctx.paginate(hashtags)

    @hashtag.command(name="info")
    async def info_hashtag(self, ctx: Context, hashtag: str):
        """Get info about a hashtag"""
        if hashtag.startswith("#"):
            hashtag = hashtag[1:]
        await ctx.message.delete(delay=3)
        if data := await self._hashtag_collection.find_one({"_id": hashtag}):
            embed = discord.Embed(
                title=f"**#{hashtag}**",
                description=f"Owner: <@{data['owner']}>",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Followers", value=len(data["followers"]))
            embed.add_field(name="Messages", value=len(data["messages"]))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{ctx.author.mention} **#{hashtag}** does not exist")

    def isin(self, phrase: str, sentence: str) -> bool:
        word = re.escape(phrase)
        pattern = rf"\b{word}\b"
        return re.search(pattern, sentence) is not None

    def word(self, list_of_phrase: List[str], sentence: str) -> bool:
        for phrase in list_of_phrase:
            word = re.escape(phrase)
            pattern = rf"\b{word}\b"
            if re.search(pattern, sentence) is not None:
                return word

    @Cog.listener("on_message")
    async def on_message_highlight(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return

        words: List[str] = self.__caching_highlight.get(message.author.id, [])
        if not words:
            data: dict = await self._highlight_collection.find_one(
                {"_id": message.author.id}
            )
            if not data:
                return
            words = data["words"]

        for word in words:
            if not self.isin(word, message.content):
                continue

            try:
                await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == message.author
                    and message.channel == m.channel,
                    timeout=10,
                )
            except asyncio.TimeoutError:
                content: str = re.sub(rf"\b{word}\b", f"**{word}**", message.content)
                description = f"Your word **{word}** was mentioned in {message.channel.mention} by {message.author.mention}"
                description += f"\n\n[{message.created_at}] {message.author}: {content}"
                embed: discord.Embed = (
                    discord.Embed(
                        title="Your word was mentioned",
                        description=description,
                        color=discord.Color.blurple(),
                        url=message.jump_url,
                    )
                    .set_author(
                        name=message.author.display_name,
                        icon_url=message.author.display_avatar.url,
                    )
                    .set_footer(
                        text=message.guild.name,
                        icon_url=getattr(message.guild.icon, "url", None),
                    )
                )
                try:
                    return await message.author.send(embed=embed)
                except discord.Forbidden:
                    pass
            break

    @Cog.listener("on_message")
    async def on_message_hashtag(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return

        for hastag in self.__caching_hashtag:
            if not self.isin(hastag, message.content):
                continue

            users: List[int] = self.__caching_hashtag[hastag]
            if not users:
                data: dict = await self._hashtag_collection.find_one({"_id": hastag})
                if not data:
                    continue
                users = data["followers"]

            try:
                await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author.id in users
                    and message.channel == m.channel,
                    timeout=10,
                )
            except asyncio.TimeoutError:

                async def __internal_function(
                    bot: Parrot, user_id: int, **kwargs
                ) -> discord.Message:
                    try:
                        user: discord.User = await bot.getch(
                            bot.get_user, bot.fetch_user, user_id
                        )
                        return await user.send(**kwargs)
                    except discord.Forbidden:
                        pass

                content: str = re.sub(
                    rf"\b{hastag}\b", f"**{hastag}**", message.content
                )
                description = f"Your hashtag **{hastag}** was mentioned in {message.channel.mention} by {message.author.mention}"
                description += f"\n\n[{message.created_at}] {message.author}: {content}"
                embed: discord.Embed = (
                    discord.Embed(
                        title="Your hashtag was mentioned",
                        description=description,
                        color=discord.Color.blurple(),
                        url=message.jump_url,
                    )
                    .set_author(
                        name=message.author.display_name,
                        icon_url=message.author.display_avatar.url,
                    )
                    .set_footer(
                        text=message.guild.name,
                        icon_url=getattr(message.guild.icon, "url", None),
                    )
                )
                await asyncio.wait(
                    *[
                        __internal_function(self.bot, user_id, embed=embed)
                        for user_id in users
                    ],
                    return_when=asyncio.ALL_COMPLETED,
                )
            break
