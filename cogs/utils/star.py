from __future__ import annotations

from discord.ext import commands, tasks
from cogs.meta.robopage import SimplePages

import discord
import time

from utilities.checks import is_mod
from utilities.database import parrot_db, cluster
from utilities.formats import plural
from utilities import time
import typing
import weakref
import re

from core import Parrot, Cog

starboard_entry = cluster["starboard_entry"]
starrer = cluster["starrer"]
server_config = parrot_db["server_config"]


class StarError(commands.CheckFailure):
    pass


def requires_starboard():
    async def predicate(ctx):
        if ctx.guild is None:
            return False

        cog = ctx.bot.get_cog("Stars")

        ctx.starboard = await cog.get_starboard(
            ctx.guild.id, collection=parrot_db["server_config"]
        )
        if ctx.starboard is None:
            raise StarError("\N{WARNING SIGN} Starboard channel not found.")

        return True

    return commands.check(predicate)


def MessageID(argument):
    try:
        return int(argument, base=10)
    except ValueError:
        raise StarError(
            f'"{argument}" is not a valid message ID. Use Developer Mode to get the Copy ID option.'
        )


class StarboardConfig:
    __slots__ = ("bot", "id", "channel_id", "threshold", "locked", "max_age")

    def __init__(self, *, guild_id: int, bot: Parrot, record=None):
        self.id = guild_id
        self.bot = bot

        if record:
            self.channel_id = record["channel_id"]
            self.threshold = record["threshold"]
            self.locked = record["locked"]

            self.max_age = record["max_age"]
        else:
            self.channel_id = None

    @property
    def channel(self):
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.channel_id)


class Stars(Cog):
    """A starboard to upvote posts obviously"""

    def __init__(self, bot: Parrot):
        self.bot = bot

        # cache message objects to save Discord some HTTP requests.
        self._message_cache = {}
        self.clean_message_cache.start()

        # if it's in this set,
        self._about_to_be_deleted = set()

        self._locks = weakref.WeakValueDictionary()
        self.spoilers = re.compile(r"\|\|(.+?)\|\|")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{WHITE MEDIUM STAR}")

    def cog_unload(self):
        self.clean_message_cache.cancel()

    @tasks.loop(hours=1.0)
    async def clean_message_cache(self):
        self._message_cache.clear()

    # @cache.cache()
    async def get_starboard(self, guild_id, *, collection=None) -> StarboardConfig:
        collection = collection or parrot_db["server_config"]
        if data := await collection.find_one(
            {"_id": guild_id, "starboard": {"$exists": True}}
        ):
            return StarboardConfig(guild_id=guild_id, bot=self.bot, record=data)
        post = {"channel_id": None, "threshold": None, "locked": True, "max_age": None}
        await collection.update_one({"_id": guild_id}, {"$set": {"starboard": post}})
        return StarboardConfig(guild_id=guild_id, bot=self.bot, record=post)

    def star_emoji(self, stars):
        if 5 > stars >= 0:
            return "\N{WHITE MEDIUM STAR}"
        if 10 > stars >= 5:
            return "\N{GLOWING STAR}"
        if 25 > stars >= 10:
            return "\N{DIZZY SYMBOL}"
        return "\N{SPARKLES}"

    def star_gradient_colour(self, stars):
        p = stars / 13
        if p > 1.0:
            p = 1.0

        red = 255
        green = int((194 * p) + (253 * (1 - p)))
        blue = int((12 * p) + (247 * (1 - p)))
        return (red << 16) + (green << 8) + blue

    def is_url_spoiler(self, text, url):
        spoilers = self.spoilers.findall(text)
        for spoiler in spoilers:
            if url in spoiler:
                return True
        return False

    def get_emoji_message(self, message: discord.Message, stars):
        emoji = self.star_emoji(stars)

        if stars > 1:
            content = f"{emoji} **{stars}** {message.channel.mention} ID: {message.id}"
        else:
            content = f"{emoji} {message.channel.mention} ID: {message.id}"

        embed = discord.Embed(description=message.content)
        if message.embeds:
            data = message.embeds[0]
            if data.type == "image" and not self.is_url_spoiler(
                message.content, data.url
            ):
                embed.set_image(url=data.url)

        if message.attachments:
            file = message.attachments[0]
            spoiler = file.is_spoiler()
            if not spoiler and file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                embed.set_image(url=file.url)
            elif spoiler:
                embed.add_field(
                    name="Attachment",
                    value=f"||[{file.filename}]({file.url})||",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Attachment",
                    value=f"[{file.filename}]({file.url})",
                    inline=False,
                )

        ref = message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            embed.add_field(
                name="Replying to...",
                value=f"[{ref.resolved.author}]({ref.resolved.jump_url})",
                inline=False,
            )

        embed.add_field(
            name="Original", value=f"[Jump!]({message.jump_url})", inline=False
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.display_avatar.url
        )
        embed.timestamp = message.created_at
        embed.colour = self.star_gradient_colour(stars)
        return content, embed

    async def get_message(
        self,
        channel: typing.Union[discord.TextChannel, discord.Thread],
        message_id: int,
    ) -> typing.Optional[discord.Message]:
        try:
            return self._message_cache[message_id]
        except KeyError:
            try:
                o = discord.Object(id=message_id + 1)
                pred = lambda m: m.id == message_id
                # don't wanna use get_message due to poor rate limit (1/1s) vs (50/1s)
                msg = await channel.history(limit=1, before=o).next()

                if msg.id != message_id:
                    return None

                self._message_cache[message_id] = msg
                return msg
            except Exception:
                return None

    async def reaction_action(self, fmt, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel_or_thread(payload.channel_id)
        if not isinstance(channel, (discord.Thread, discord.TextChannel)):
            return

        method = getattr(self, f"{fmt}_message")

        user = payload.member or (
            await self.bot.get_or_fetch_member(guild, payload.user_id)
        )
        if user is None or user.bot:
            return

        try:
            await method(channel, payload.message_id, payload.user_id)
        except StarError:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, discord.TextChannel):
            return

        starboard = await self.get_starboard(channel.guild.id)
        if starboard.channel is None or starboard.channel.id != channel.id:
            return

        await server_config.update_one(
            {"_id": channel.guild.id}, {"$set": {"starboard": {}}}
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return
        await self.reaction_action("star", payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return
        await self.reaction_action("unstar", payload)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        collection = starboard_entry[f"{payload.guild_id}"]
        if payload.message_id in self._about_to_be_deleted:
            self._about_to_be_deleted.discard(payload.message_id)
            return

        starboard = await self.get_starboard(payload.guild_id)
        if not starboard.channel:
            return
        if starboard.channel is None or starboard.channel.id != payload.channel_id:
            return
        await collection.delete_one({"bot_message_id": payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        collection = starboard_entry[f"{payload.guild_id}"]
        if payload.message_ids <= self._about_to_be_deleted:
            # see comment above
            self._about_to_be_deleted.difference_update(payload.message_ids)
            return

        starboard = await self.get_starboard(payload.guild_id)
        if not starboard.channel:
            return
        if starboard.channel is None or starboard.channel.id != payload.channel_id:
            return
        for msg_id in payload.message_ids:
            await collection.delete_one({"bot_message_id": msg_id})

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        collection = starboard_entry[f"{payload.guild_id}"]
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel_or_thread(payload.channel_id)
        if channel is None or not isinstance(
            channel, (discord.Thread, discord.TextChannel)
        ):
            return

        starboard = await self.get_starboard(channel.guild.id, collection=collection)
        if not starboard.channel:
            return

        data = await collection.find_one({"bot_message_id": payload.message_id})
        await collection.delete_one({"bot_message_id": payload.message_id})

        if data[payload.message_id] is None:
            return

        bot_message_id = payload[0]
        msg = await self.get_message(starboard.channel, bot_message_id)
        if msg is not None:
            await msg.delete()

    async def star_message(
        self,
        channel: typing.Union[discord.TextChannel, discord.Thread],
        message_id: int,
        starrer_id: int,
    ) -> None:

        await self._star_message(channel, message_id, starrer_id, db=starboard_entry)

    async def _star_message(
        self, channel: discord.TextChannel, message_id: int, starrer_id: int, *, db
    ) -> None:
        guild_id = channel.guild.id

        collection = db[f"{guild_id}"]
        collection_starrer = starrer["starrer"]

        starboard = await self.get_starboard(guild_id)
        if not starboard.channel:
            raise StarError("\N{WARNING SIGN} Starboard channel not found.")

        if starboard.locked:
            raise StarError("\N{NO ENTRY SIGN} Starboard is locked.")
        starboard_channel = starboard.channel
        if channel.is_nsfw() and not starboard_channel.is_nsfw():
            raise StarError(
                "\N{NO ENTRY SIGN} Cannot star NSFW in non-NSFW starboard channel."
            )

        if channel.id == starboard_channel.id:

            if data := await collection.find_one({"bot_message_id": message_id}):
                ch = channel.guild.get_channel_or_thread(data["channel_id"])
            else:
                raise StarError("Could not find message in the starboard.")

            if ch is None:
                raise StarError("Could not find original channel.")

            return await self._star_message(ch, data["message_id"], starrer_id, db=db)

        if not starboard_channel.permissions_for(
            starboard_channel.guild.me
        ).send_messages:
            raise StarError(
                "\N{NO ENTRY SIGN} Cannot post messages in starboard channel."
            )

        msg = await self.get_message(channel, message_id)

        if msg is None:
            raise StarError(
                "\N{BLACK QUESTION MARK ORNAMENT} This message could not be found."
            )

        if msg.author.id == starrer_id:
            raise StarError("\N{NO ENTRY SIGN} You cannot star your own message.")

        empty_message = len(msg.content) == 0 and len(msg.attachments) == 0
        if empty_message or msg.type not in (
            discord.MessageType.default,
            discord.MessageType.reply,
        ):
            raise StarError("\N{NO ENTRY SIGN} This message cannot be starred.")

        oldest_allowed = discord.utils.utcnow().timestamp() - starboard.max_age
        if msg.created_at < oldest_allowed:
            raise StarError("\N{NO ENTRY SIGN} This message is too old.")
        post = {
            "_id": guild_id,
            "message_id": message_id,
            "channel_id": channel.id,
            "author_id": msg.author.id,
        }
        try:
            await collection.insert_one(post)
        except Exception:
            pass
        try:
            await collection_starrer.insert_one(
                {"author_id": starrer_id, "entry_id": message_id}
            )
        except Exception:
            pass

        counter = 0
        async for i in collection_starrer.find({"entry_id": message_id}):
            counter += 1

        if counter < starboard.threshold:
            return

        content, embed = self.get_emoji_message(msg, counter)

        data = await collection.find_one({"message_id": message_id})
        try:
            bot_message_id = data["bot_messag_id"]
        except KeyError:
            bot_message_id = None

        if bot_message_id is None:
            new_msg = await starboard_channel.send(content, embed=embed)
            await collection.update_one(
                {"message_id": message_id}, {"$set": {"bot_message_id": new_msg.id}}
            )
        else:
            new_msg = await self.get_message(starboard_channel, bot_message_id)
            if new_msg is None:
                await collection.delete_one({"message_id": message_id})
            else:
                await new_msg.edit(content=content, embed=embed)

    async def unstar_message(
        self,
        channel: typing.Union[discord.TextChannel, discord.Thread],
        message_id: int,
        starrer_id: int,
    ) -> None:
        await self._unstar_message(channel, message_id, starrer_id, db=starboard_entry)

    async def _unstar_message(
        self,
        channel: typing.Union[discord.TextChannel, discord.Thread],
        message_id: int,
        starrer_id: int,
        *,
        db,
    ) -> None:
        guild_id = channel.guild.id
        starboard = await self.get_starboard(guild_id)
        starboard_channel = starboard.channel
        collection_starrer = starrer["starrer"]
        collection = db[f"{guild_id}"]
        if starboard_channel is None:
            raise StarError("\N{WARNING SIGN} Starboard channel not found.")

        if starboard.locked:
            raise StarError("\N{NO ENTRY SIGN} Starboard is locked.")

        if channel.id == starboard_channel.id:
            if not (data := await collection.find_one({"bot_message_id": message_id})):
                raise StarError("Could not find message in the starboard.")
            ch = channel.guild.get_channel_or_thread(data["channel_id"])
            if ch is None:
                raise StarError("Could not find original channel.")

            return await self._unstar_message(
                ch, data["message_id"], starrer_id, collection=collection
            )

        if not starboard_channel.permissions_for(
            starboard_channel.guild.me
        ).send_messages:
            raise StarError(
                "\N{NO ENTRY SIGN} Cannot edit messages in starboard channel."
            )
        temp = await collection.find_one({"message_id": message_id})

        data = await collection_starrer.delete_one(
            {"starrer_id": starrer_id, "entry_id": message_id}
        )
        data_ = await collection.delete_one({"message_id": message_id})
        if not data_:
            raise StarError("\N{NO ENTRY SIGN} You have not starred this message.")

        counter = 0
        async for i in collection_starrer.find({"entry_id": message_id}):
            counter += 1

        if counter == 0:
            await collection.delete_one({"message_id": message_id})
        try:
            bot_message_id = temp["bot_message_id"]
        except KeyError:
            bot_message_id = None

        if bot_message_id is None:
            return

        bot_message = await self.get_message(starboard_channel, bot_message_id)
        if bot_message is None:
            return

        if counter < starboard.threshold:
            self._about_to_be_deleted.add(bot_message_id)
            if counter:
                await collection.update_one(
                    {"message_id": message_id}, {"$set": {"bot_message_id": None}}
                )

            await bot_message.delete()
        else:
            msg = await self.get_message(channel, message_id)
            if msg is None:
                raise StarError(
                    "\N{BLACK QUESTION MARK ORNAMENT} This message could not be found."
                )

            content, embed = self.get_emoji_message(msg, counter)
            await bot_message.edit(content=content, embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_guild=True))
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def starboard(self, ctx, *, name="starboard"):
        """
        Sets up the starboard for this server. This creates a new channel with the specified name and makes it into the server's "starboard". If no name is passed in then it defaults to "starboard". You must have Manage Server permission to use this.
        """
        # bypass the cache just in case someone used the star
        # reaction earlier before having it set up, or they
        # decided to use the ?star command
        self.get_starboard.invalidate(self, ctx.guild.id)

        starboard = await self.get_starboard(
            ctx.guild.id, collection=parrot_db["server_config"]
        )
        if starboard.channel is not None:
            return await ctx.reply(
                f"{ctx.author.mention} this server already has a starboard ({starboard.channel.mention})."
            )

        if hasattr(starboard, "locked"):
            try:
                confirm = await ctx.prompt(
                    "Apparently, a previously configured starboard channel was deleted. Is this true?"
                )
            except RuntimeError as e:
                await ctx.reply(
                    f"Something not right. Report this to developers\n```py\n{e}```"
                )
            else:
                if confirm:
                    await server_config.update_one(
                        {"_id": ctx.guild.id}, {"$set": {"starboard": {}}}
                    )
                else:
                    return await ctx.reply(
                        "Aborting starboard creation. Join the bot support server for more questions."
                    )
        overwrites = {
            ctx.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                read_message_history=True,
            ),
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, read_message_history=True
            ),
        }

        reason = (
            f"{ctx.author} (ID: {ctx.author.id}) has created the starboard channel."
        )

        try:
            channel = await ctx.guild.create_text_channel(
                name=name, overwrites=overwrites, reason=reason
            )
        except discord.Forbidden:
            return await ctx.reply(
                "\N{NO ENTRY SIGN} I do not have permissions to create a channel."
            )
        except discord.HTTPException:
            return await ctx.reply(
                "\N{NO ENTRY SIGN} This channel name is bad or an unknown error happened."
            )

        try:
            await server_config.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"starboard": {"channel_id": channel.id}}},
            )
        except:
            await channel.delete(reason="Failure to commit to create the ")
            await ctx.reply(
                "Could not create the channel due to an internal error. Join the bot support server for help."
            )
        else:
            self.get_starboard.invalidate(self, ctx.guild.id)
            await ctx.reply(f"\N{GLOWING STAR} Starboard created at {channel.mention}.")

    @starboard.command(name="info")
    @requires_starboard()
    async def starboard_info(self, ctx):
        """Shows meta information about the starboard."""
        starboard = ctx.starboard
        channel = starboard.channel
        data = []

        if channel is None:
            data.append("Channel: #deleted-channel")
        else:
            data.append(f"Channel: {channel.mention}")
            data.append(f"NSFW: {channel.is_nsfw()}")

        data.append(f"Locked: {starboard.locked}")
        data.append(f"Limit: {plural(starboard.threshold):star}")
        data.append(f"Max Age: {plural(starboard.max_age.days):day}")
        await ctx.reply("\n".join(data))

    @commands.group(invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(manage_messages=True)
    async def star(self, ctx, message: MessageID):
        """
        Stars a message via message ID. To star a message you should right click on the on a message and then click "Copy ID". You must have Developer Mode enabled to get that functionality. It is recommended that you react to a message with \N{WHITE MEDIUM STAR} instead.
        You can only star a message once.
        """
        try:
            await self.star_message(ctx.channel, message, ctx.author.id)
        except StarError as e:
            await ctx.reply(e)
        else:
            await ctx.message.delete()

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def unstar(self, ctx, message: MessageID):
        """Unstars a message via message ID. To unstar a message you should right click on the on a message and then click "Copy ID". You must have Developer Mode enabled to get that functionality."""
        try:
            await self.unstar_message(ctx.channel, message, ctx.author.id, verify=True)
        except StarError as e:
            return await ctx.reply(e)
        else:
            await ctx.message.delete()

    @star.command(name="show")
    @requires_starboard()
    async def star_show(self, ctx, message: MessageID):
        """
        Shows a starred message via its ID. To get the ID of a message you should right click on the message and then click "Copy ID". You must have Developer Mode enabled to get that functionality. You can only use this command once per 10 seconds.
        """
        collection = starboard_entry[f"{ctx.guild.id}"]
        if data := await collection.find_one({"message_id": message}):
            bot_message_id = data["bot_message_id"]
        elif data := await collection.find_one({"bot_message_id": message}):
            bot_message_id = data["bot_message_id"]
        else:
            return await ctx.reply(
                f"{ctx.author.mention} this message has not been starred."
            )
        record = data
        bot_message_id = record["bot_message_id"]
        if not bot_message_id:
            # "fast" path, just redirect the message
            msg = await self.get_message(ctx.starboard.channel, bot_message_id)
            if msg is not None:
                embed = msg.embeds[0] if msg.embeds else None
                return await ctx.reply(msg.content, embed=embed)
            # somehow it got deleted, so just delete the entry
            await collection.delete_one({"message_id": message})
        # slow path, try to fetch the content
        channel = ctx.guild.get_channel_or_thread(record["channel_id"])
        if channel is None:
            return await ctx.reply(
                f"{ctx.author.mention} the message's channel has been deleted."
            )

        msg = await self.get_message(channel, record["message_id"])
        if msg is None:
            return await ctx.reply(
                f"{ctx.author.mention} the message has been deleted."
            )

        content, embed = self.get_emoji_message(msg, record["Stars"])
        await ctx.reply(content, embed=embed)

    @star.command(name="who")
    @requires_starboard()
    async def star_who(self, ctx, message: MessageID):
        """Show who starred a message. The ID can either be the starred message ID or the message ID in the starboard channel."""
        collection = starboard_entry[f"{ctx.guild.id}"]
        if data := await collection.find_one({"message_id": message}):
            pass
        if not data:
            data = await collection.find_one({"bot_message_id": message})

        records = [data]

        if records is None:
            return await ctx.reply(
                f"{ctx.author.mention} no one starred this message or this is an invalid message ID."
            )

        members = [
            str(member)
            async for member in self.bot.resolve_member_ids(ctx.guild, records)
        ]

        p = SimplePages(entries=members, per_page=20, ctx=ctx)
        base = format(plural(len(records)), "star")
        if len(records) > len(members):
            p.embed.title = f"{base} ({len(records) - len(members)} left server)"
        else:
            p.embed.title = base

        await p.start()

    def records_to_value(self, records, fmt=None, default="None!"):
        if not records:
            return default

        emoji = 0x1F947  # :first_place:
        fmt = fmt or (lambda o: o)
        return "\n".join(
            f'{chr(emoji + i)}: {fmt(r["ID"])} ({plural(r["Stars"]):star})'
            for i, r in enumerate(records)
        )

    @star.command(name="lock")
    @commands.check_any(is_mod(), commands.has_permissions(manage_guild=True))
    @requires_starboard()
    async def star_lock(self, ctx):
        """
        Locks the starboard from being processed. This is a moderation tool that allows you to temporarily disable the starboard to aid in dealing with star spam. When the starboard is locked, no new entries are added to the starboard as the bot will no longer listen to reactions or star/unstar commands. To unlock the starboard, use the unlock subcommand. To use this command you need Manage Server permission.
        """
        if ctx.starboard.needs_migration:
            return await ctx.reply(
                f"{ctx.author.mention} your starboard requires migration!"
            )
        await server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard": {"locked": True}}}
        )
        self.get_starboard.invalidate(self, ctx.guild.id)

        await ctx.reply(f"{ctx.author.mention} starboard is now locked.")

    @star.command(name="unlock")
    @commands.check_any(is_mod(), commands.has_permissions(manage_guild=True))
    @requires_starboard()
    async def star_unlock(self, ctx):
        """Unlocks the starboard for re-processing.
        To use this command you need Manage Server permission.
        """
        await server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard": {"locked": False}}}
        )
        self.get_starboard.invalidate(self, ctx.guild.id)
        await ctx.reply(f"{ctx.author.mention} starboard is now unlocked.")

    @star.command(name="limit", aliases=["threshold"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_guild=True))
    @requires_starboard()
    async def star_limit(self, ctx, stars: int):
        """Sets the minimum number of stars required to show up. When this limit is set, messages must have this number or more to show up in the starboard channel. You cannot have a negative number and the maximum star limit you can set is 100. Note that messages that previously did not meet the limit but now do will still not show up in the starboard until starred again. You must have Manage Server permissions to use this."""
        if ctx.starboard.needs_migration:
            return await ctx.reply("Your starboard requires migration!")
        stars = min(max(stars, 1), 100)
        await server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard": {"threshold": stars}}}
        )
        self.get_starboard.invalidate(self, ctx.guild.id)

        await ctx.reply(
            f"{ctx.author.mention} messages now require {plural(stars):star} to show up in the starboard."
        )

    @star.command(name="age")
    @commands.check_any(is_mod(), commands.has_permissions(manage_guild=True))
    @requires_starboard()
    async def star_age(self, ctx, *, age: time.ShortTime):
        """
        Sets the maximum age of a message valid for starring. By default, the maximum age is 7 days. Any message older than this specified age is invalid of being starred. To set the limit you must specify a number followed by a unit. The valid units are "days", "weeks", "months", or "years". They do not have to be pluralized. The default unit is "days". The number cannot be negative, and it must be a maximum of 35. If the unit is years then the cap is 10 years. You cannot mix and match units. You must have Manage Server permissions to use this.
        """
        seconds = age.dt.timestamp()
        if seconds >= 31622400:
            return await ctx.reply(
                f"{ctx.author.mention} maximum age can not be more than 1 year"
            )

        await server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard": {"max_age": seconds}}}
        )
        self.get_starboard.invalidate(self, ctx.guild.id)
        await ctx.reply(f"{ctx.author.mention} starboard max age is set to {age}")


def setup(bot):
    bot.add_cog(Stars(bot))
