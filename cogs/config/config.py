from __future__ import annotations
import asyncio
from cogs.meta.robopage import SimplePages
from cogs.config import method as mt_
from cogs.ticket import method as mt

from discord.ext import commands
import discord
import typing
import re

import json

from core import Parrot, Context, Cog

from utilities.checks import has_verified_role_ticket
from utilities.converters import convert_bool
from utilities.time import ShortTime

from .flags import AutoWarn, warnConfig


with open(r"cogs/config/events.json") as f:
    events = json.load(f)


class Configuration(Cog):
    """To config the bot. In the server"""

    def __init__(self, bot: Parrot):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{GEAR}")

    @commands.group(
        name="config", aliases=["serverconfig"], invoke_without_command=True
    )
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def config(self, ctx: Context):
        """To config the bot, mod role, prefix, or you can disable the commands and cogs."""
        if not ctx.invoked_subcommand:
            if data := await self.bot.mongo.parrot_db.server_config.find_one(
                {"_id": ctx.guild.id}
            ):
                role = ctx.guild.get_role(data.get("mod_role", 0))
                mod_log = ctx.guild.get_channel(data.get("action_log", 0))
                mute_role = ctx.guild.get_role(data.get("mute_role", 0))
                suggestion_channel = ctx.guild.get_channel(
                    data.get("suggestion_channel", 0)
                )
                hub = ctx.guild.get_channel(data.get("hub", 0))
                vc = ctx.guild.get_channel(data.get("vc", 0))
                await ctx.reply(
                    f"Configuration of this server [server_config]\n\n"
                    f"`Prefix  :` **{data['prefix']}**\n"
                    f"`ModRole :` **{role.name if role else 'None'} ({data.get('mod_role')})**\n"
                    f"`MogLog  :` **{mod_log.mention if mod_log else 'None'} ({data.get('action_log')})**\n"
                    f"`MuteRole:` **{mute_role.name if mute_role else 'None'} {data.get('mute_role')}**\n"
                    f"`Premium :` **{'Enabled' if data.get('premium') else 'Disabled'}**\n\n"
                    f"`SuggestionChannel:` **{suggestion_channel.mention if suggestion_channel else 'None'} {data.get('suggestion_channel')}**\n"
                    f"`Hub     :` **{hub.mention if hub else 'None'} {data.get('hub')}**\n"
                    f"`VC(24/7):` **{vc.mention if vc else 'None'} {data.get('vc')}**\n"
                )

    @config.group(name="hub", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def setup_hub(
        self,
        ctx: Context,
    ):
        """To setup Hub like channel"""
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                connect=True, read_messages=True
            ),
            ctx.guild.me: discord.PermissionOverwrite(
                connect=True,
                read_messages=True,
                manage_channels=True,
                manage_permissions=True,
            ),
        }
        cat = await ctx.guild.create_category_channel(
            "The Hub",
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            overwrites=overwrites,
        )

        channel = await ctx.guild.create_voice_channel(
            "Hub - Join to create",
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            category=cat,
            user_limit=1,
        )

        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"hub": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} successfully created {channel.mention}! Enjoy"
        )

    @config.group(name="starboard", aliases=["star"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def starboard(
        self,
        ctx: Context,
    ):
        """To setup the starboard in your server"""
        if not ctx.invoked_subcommand:
            try:
                starboard_data = self.bot.server_config[ctx.guild.id]["starboard"]
            except KeyError:
                return await self.bot.invoke_help_command(ctx)
            channel = ctx.guild.get_channel(starboard_data.get("channel", 0))
            limit = starboard_data.get("limit")
            is_locked = starboard_data.get("is_locked")
            ignore_channel = ctx.guild.get_channel(
                starboard_data.get("ignore_channel", 0)
            )
            max_duration = starboard_data.get("max_duration")
            return await ctx.reply(
                f"Configuration of this server [starboard]\n\n"
                f"`Channel :` **{channel.mention if channel else 'None'} ({starboard_data.get('channel')})**\n"
                f"`Limit   :` **{limit}**\n"
                f"`Locked  :` **{is_locked}**\n"
                f"`Ignore  :` **{ignore_channel.mention if ignore_channel else 'None'} {starboard_data.get('ignore_channel')}**\n"
                f"`Duration:` **{max_duration}**\n"
            )

    @starboard.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def starboard_channel(
        self, ctx: Context, *, channel: typing.Optional[discord.TextChannel] = None
    ):
        """To setup the channel"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"starboard.channel": channel.id if channel else None}},
        )
        if channel:
            return await ctx.reply(
                f"{ctx.author.mention} set the starboard channel to {channel.mention}"
            )
        await ctx.send(f"{ctx.author.mention} removed the starboard channel")

    @starboard.command(name="maxage", aliases=["maxduration"])
    @commands.has_permissions(administrator=True)
    async def starboard_max_age(self, ctx: Context, *, duration: ShortTime):
        """To set the max duration"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "starboard.max_duration": ctx.message.created_at.timestamp()
                    - duration.dt.timestamp()
                }
            },
        )
        await ctx.reply(
            f"{ctx.author.mention} set the max duration to **{ctx.message.created_at.timestamp() - duration.dt.timestamp()}** seconds"
        )

    @starboard.command(name="ignore", aliases=["ignorechannel"])
    @commands.has_permissions(administrator=True)
    async def starboard_add_ignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To add ignore list"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"starboard.ignore_channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} added {channel.mention} to the ignore list"
        )

    @starboard.command(name="unignore", aliases=["unignorechannel"])
    @commands.has_permissions(administrator=True)
    async def starboard_remove_ignore(
        self, ctx: Context, *, channel: discord.TextChannel
    ):
        """To remove the channel from ignore list"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"starboard.ignore_channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed {channel.mention} from the ignore list"
        )

    @starboard.command(name="threshold", aliases=["limit"])
    @commands.has_permissions(administrator=True)
    async def starboard_limit(self, ctx: Context, limit: int = 3):
        """To set the starboard limit"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard.limit": limit}}
        )
        await ctx.reply(f"{ctx.author.mention} set starboard limit to **{limit}**")

    @starboard.command(name="lock", aliases=["locked"])
    @commands.has_permissions(administrator=True)
    async def starboard_lock(self, ctx: Context, toggle: convert_bool = False):
        """To lock the starboard channel"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"starboard.is_locked": toggle}}
        )
        await ctx.reply(
            f"{ctx.author.mention} starboard channel is now {'locked' if toggle else 'unlocked'}"
        )

    @config.command(aliases=["log"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(
        manage_channels=True, manage_webhooks=True, view_audit_log=True
    )
    async def logging(
        self, ctx: Context, event: str, *, channel: discord.TextChannel = None
    ):
        """To setup the logging feature of the server. This logging is not mod log or Ticket log"""
        channel = channel or ctx.channel
        if event not in events:
            return await ctx.reply(
                f"{ctx.author.mention} invalid event. Available events `{'`, `'.join(events)}`"
            )
        hooks = await channel.webhooks()
        if len(hooks) >= 10:
            for hook in hooks:
                if hook.user.id == self.bot.user.id:  # bot created that
                    webhook = hook
                    post = {str(event): str(webhook.url)}
                    await self.bot.mongo.parrot_db.logging.update_one(
                        {"_id": ctx.guild.id}, {"$set": post}, upsert=True
                    )
                    break
            else:
                return await ctx.reply(
                    f"{ctx.author.mention} can not register event (`{event.replace('_', ' ').title()}`) in {channel.mention}. This happens when channel has already 10 webhooks created."
                )
        else:
            webhook = await channel.create_webhook(
                name=self.bot.user.name,
                reason=f"On request from {ctx.author} ({ctx.author.id}) | Reason: Setting Up Logging",
            )
            await self.bot.mongo.parrot_db.logging.update_one(
                {"_id": ctx.guild.id},
                {"$set": {str(event): str(webhook.url)}},
                upsert=True,
            )
        await ctx.reply(
            f"{ctx.author.mention} all `{event.replace('_', ' ').title()}` will be posted on {channel.mention}"
        )

    @config.command(aliases=["prefix"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def botprefix(self, ctx: Context, *, arg: str):
        """
        To set the prefix of the bot. Whatever prefix you passed, will be case sensitive.
        It is advised to keep a symbol as a prefix. Must not greater than 6 chars
        """
        # if len(arg) > 6:
        #     return await ctx.reply(
        #         f"{ctx.author.mention} length of prefix can not be more than 6 characters."
        #     )
        post = {"prefix": arg}
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": post}
        )

        await ctx.reply(
            f"{ctx.author.mention} success! Prefix for **{ctx.guild.name}** is **{arg}**."
        )

    @config.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def suggestchannel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To configure the suggestion channel. If no channel is provided it will remove the channel"""
        if channel:
            await self.bot.mongo.parrot_db.server_config.update_one(
                {"_id": ctx.guild.id}, {"$set": {"suggestion_channel": channel.id}}
            )
            await ctx.reply(
                f"{ctx.author.mention} set suggestion channel to {channel.mention}"
            )
            return
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"suggestion_channel": None}}
        )
        await ctx.reply(f"{ctx.author.mention} removed suggestion channel")

    @config.command(name="24/7", aliases=["vc247", "247vc"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def vc_247(
        self, ctx: Context, *, channel: typing.Optional[discord.VoiceChannel] = None
    ):
        """To set 24/7 VC"""
        if channel:
            await self.bot.mongo.parrot_db.server_config.update_one(
                {"_id": ctx.guild.id}, {"$set": {"vc": channel.id}}
            )
            await ctx.reply(
                f"{ctx.author.mention} set 24/7 vc channel to **{channel.name}**"
            )
            try:
                await channel.connect()
            except Exception as e:
                await ctx.send(f"{ctx.author.mention} something wrong: **{e}**")
            return
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"vc": None}}
        )
        await ctx.reply(f"{ctx.author.mention} removed vc channel")
        if ctx.guild.me.voice:
            await ctx.guild.me.edit(voice_channel=None)

    @config.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def warnadd(
        self, ctx: Context, count: int, action: str, duration: str = None
    ):
        """To configure the warn settings in server"""
        ACTIONS = [
            "ban",
            "tempban",
            "kick",
            "timeout",
            "mute",
        ]
        if action.lower() not in ACTIONS:
            return await ctx.send(
                f"{ctx.author.mention} invalid action. Available actions: `{'`, `'.join(ACTIONS)}`"
            )
        if duration:
            _ = ShortTime(duration)
        if _ := await self.bot.mongo.parrot_db.server_config.find_one(
            {"_id": ctx.guild.id, "warn_auto.count": count}
        ):
            return await ctx.send(
                f"{ctx.author.mention} warn count {count} already exists."
            )
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "warn_auto": {
                        "count": count,
                        "action": action.lower(),
                        "duration": duration if duration else None,
                    }
                }
            },
        )
        await ctx.send(f"{ctx.author.mention} updated")

    @config.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def warndel(self, ctx: Context, *, flags: warnConfig):
        """To configure the warn settings"""
        ACTIONS = [
            "ban",
            "tempban",
            "kick",
            "timeout",
            "mute",
            "block",
        ]
        payload = {}
        if flags.action:
            if flags.action.lower() not in ACTIONS:
                return await ctx.send(
                    f"{ctx.author.mention} invalid action. Available actions: `{'`, `'.join(ACTIONS)}`"
                )
            payload["action"] = flags.action.lower()
        if flags.count:
            payload["count"] = flags.count
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"warn_auto": {**payload}}}
        )
        await ctx.send(f"{ctx.author.mention} updated")

    @config.command(aliases=["mute-role"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def muterole(self, ctx: Context, *, role: discord.Role = None):
        """To set the mute role of the server. By default role with name `Muted` is consider as mute role."""
        post = {"mute_role": role.id if role else None}
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": post}
        )
        if not role:
            return await ctx.reply(
                f"{ctx.author.mention} mute role reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! Mute role for **{ctx.guild.name}** is **{role.name} ({role.id})**"
        )

    @config.command(aliases=["mod-role"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def modrole(self, ctx: Context, *, role: discord.Role = None):
        """To set mod role of the server. People with mod role can accesss the Moderation power of Parrot. By default the mod functionality works on the basis of permission"""
        post = {"mod_role": role.id if role else None}
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": post}
        )
        if not role:
            return await ctx.reply(f"{ctx.author.mention} mod role reseted! or removed")
        await ctx.reply(
            f"{ctx.author.mention} success! Mod role for **{ctx.guild.name}** is **{role.name} ({role.id})**"
        )

    @config.command(aliases=["g-setup", "g_setup"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(
        manage_channels=True, manage_webhooks=True, manage_roles=True
    )
    @Context.with_type
    async def gsetup(
        self,
        ctx: Context,
        setting: str = None,
        *,
        role: typing.Optional[discord.Role] = None,
    ):
        """This command will connect your server with other servers which then connected to #global-chat must try this once"""
        c = self.bot.mongo.parrot_db.global_chat
        if not setting:

            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True
                ),
                ctx.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True
                ),
            }
            channel = await ctx.guild.create_text_channel(
                "global-chat",
                topic="Hmm. Please be calm, be very calm",
                overwrites=overwrites,
            )
            webhook = await channel.create_webhook(
                name="GlobalChat",
                reason=f"Action requested by {ctx.author.name} ({ctx.author.id})",
            )
            await c.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"channel_id": channel.id, "webhook": webhook.url}},
                upsert=True,
            )
            return await ctx.reply(
                f"{ctx.author.mention} success! Global chat is now setup {channel.mention}"
            )

        if setting.lower() in ("ignore-role", "ignore_role", "ignorerole", "ignore"):
            post = {"ignore-role": role.id if role else None}
            await self.bot.mongo.parrot_db.global_chat.update_one(
                {"_id": ctx.guild.id}, {"$set": post}, upsert=True
            )
            if not role:
                return await ctx.reply(
                    f"{ctx.author.mention} ignore role reseted! or removed"
                )
            await ctx.reply(
                f"{ctx.author.mention} success! **{role.name} ({role.id})** will be ignored from global chat!"
            )

    @config.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def countchannel(self, ctx: Context, *, channel: discord.TextChannel = None):
        """To set the counting channel in the server"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"counting": channel.id if channel else None}},
        )
        if channel:
            await ctx.reply(
                f"{ctx.author.mention} counting channel for the server is set to **{channel.mention} ({channel.id})**"
            )
        else:
            await ctx.reply(
                f"{ctx.author.mention} counting channel for the server is not removed"
            )

    @config.group(name="leveling", aliases=["lvl"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling(self, ctx: Context, toggle: convert_bool = True):
        """To configure leveling"""
        if not ctx.invoked_subcommand:
            await self.bot.mongo.parrot_db.server_config.update_one(
                {"_id": ctx.guild.id}, {"$set": {"leveling.enable": toggle}}
            )
            await ctx.reply(
                f"{ctx.author.mention} set leveling system to: **{toggle}**"
            )

    @leveling.command(name="channel")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_channel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To configure leveling channel"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"leveling.channel": channel.id if channel else None}},
        )
        if channel:
            await ctx.reply(
                f"{ctx.author.mention} all leveling like annoucement will posted in {channel.mention}"
            )
            return
        await ctx.reply(
            f"{ctx.author.mention} reset annoucement channel for the leveling"
        )

    @leveling.group(name="ignore", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_ignore_set(
        self,
        ctx: Context,
    ):
        """To configure the ignoring system of leveling"""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @leveling_ignore_set.command(
        name="role",
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_ignore_role(self, ctx: Context, *, role: discord.Role):
        """To configure leveling ignore role"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"leveling.ignore_role": role.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} all leveling for role will be ignored **{role.name}**"
        )
        return

    @leveling_ignore_set.command(
        name="channel",
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_ignore_channel(
        self, ctx: Context, *, channel: discord.TextChannel
    ):
        """To configure leveling ignore channel"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"leveling.ignore_channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} all leveling will be ignored in **{channel.mention}**"
        )

    @leveling.group(name="unignore", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_unignore_set(
        self,
        ctx: Context,
    ):
        """To configure the ignoring system of leveling"""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @leveling_unignore_set.command(
        name="role",
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_unignore_role(self, ctx: Context, *, role: discord.Role):
        """To configure leveling unignore role"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"leveling.ignore_role": role.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{role.name}** from ignore list. (If existed)"
        )

    @leveling_unignore_set.command(
        name="channel",
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def leveling_unignore_channel(
        self, ctx: Context, *, channel: discord.TextChannel
    ):
        """To configure leveling ignore channel"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"leveling.ignore_channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.mention}** from ignore list. (If existed)"
        )

    @leveling.command(name="addreward")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def level_reward_add(
        self, ctx: Context, level: int, *, role: discord.Role = None
    ):
        """To add the level reward"""
        if _ := await self.bot.mongo.parrot_db.server_config.find_one(
            {"_id": ctx.guild.id, "leveling.reward": level}
        ):
            return await ctx.send(
                f"{ctx.author.mention} conflit in adding {level}. It already exists with reward of role ID: **{_['role']}**"
            )
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "leveling.reward": {"lvl": level, "role": role.id if role else None}
                }
            },
        )
        if not role:
            await ctx.reply(f"{ctx.author.mention} reset the role on level **{level}**")
            return
        await ctx.reply(
            f"{ctx.author.mention} set role {role.name} at level **{level}**"
        )

    @leveling.command(name="removereward")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def level_reward_remove(self, ctx: Context, level: int):
        """To remove the level reward"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"leveling.reward": {"lvl": level}}}
        )
        await ctx.reply(
            f"{ctx.author.mention} updated/removed reward at level: **{level}**"
        )

    @config.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def onewordchannel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To set the one word channel in the server"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"oneword": channel.id if channel else None}},
        )
        if channel:
            await ctx.reply(
                f"{ctx.author.mention} one word channel for the server is set to **{channel.name}**"
            )
        else:
            await ctx.reply(
                f"{ctx.author.mention} one word channel for the server is not removed"
            )

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def automod(self, ctx: Context):
        """To configure the automoderation"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @automod.group(name="spam", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def automod_spam(self, ctx: Context, to_enable: convert_bool):
        """To toggle the spam protection in the server"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)
            return
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.spam.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection in the server is set to **{to_enable}**. "
            "Note: As per discord API it is allowed to send **5 messages** within **5 seconds** of interval in channel. "
            "Bot will be issuing warning if someone exceeds the limit."
        )

    @automod_spam.command(name="ignore")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def spam_ignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the spam channel."""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.spam.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection won't be working in **{channel.name}**"
        )

    @automod_spam.command(name="remove")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def spam_remove(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the spam channel."""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.spam.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection will be working in **{channel.name}**"
        )

    @automod.group(name="links")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def automod_links(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the invite protection in the server"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.antilinks.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} anti links protection in the server is set to **{to_enable}**"
        )

    @automod_links.command(name="ignore")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antilinks_ignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the channel from anti links protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.antilinks.channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for links protection"
        )

    @automod_links.command(name="remove")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antilinksremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove whitelisted channel from anti links protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.antilinks.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for links protection"
        )

    @automod_links.command(name="whitelist")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def whitelistlink(self, ctx: Context, *, link: str):
        """To whitelist a link."""
        try:
            re.compile(link)
        except re.error:
            return await ctx.reply(f"{ctx.author.mention} invalid regex expression")
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.antilinks.whitelist": link}}
        )
        await ctx.reply(
            f"{ctx.author.mention} **<{link}>** added for the whitelist link"
        )

    @automod_links.command(name="blacklist")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def blacklistlink(self, ctx: Context, *, link: str):
        """To remove whitelisted link."""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.antilinks.whitelist": link}}
        )
        await ctx.reply(
            f"{ctx.author.mention} **<{link}>** removed for the whitelist link"
        )

    @automod.group(name="profanity", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanity(self, ctx: Context, *, to_enable: convert_bool):
        """To add profanity words. Can also work for regex"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.profanity.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} profanity system in this server is set to **{to_enable}**"
        )

    @profanity.command(name="add")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityadd(self, ctx: Context, *, word: str):
        """To add profanity words. Can also work for regex. May take 1h to update"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.profanity.words": word.lower()}},
        )
        await ctx.reply(f"{ctx.author.mention} **||{word}||** added in the list")

    @profanity.command(name="del", aliases=["delete"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanitydel(self, ctx: Context, *, word: str):
        """To remove profanity word from list. Can also work for regex"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.profanity.words": word.lower()}}
        )
        await ctx.reply(f"{ctx.author.mention} **||{word}||** removed from the list")

    @profanity.command(name="ignore")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from profanity"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.profanity.channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for profanity protection"
        )

    @profanity.command(name="remove")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from profanity"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.profanity.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for profanity protection"
        )

    @automod.group(name="caps", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsprotection(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the caps protection in the server"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.caps.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} caps protection for this server is set to **{to_enable}**"
        )

    @capsprotection.command(name="limit")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capslimit(self, ctx: Context, *, limit: int):
        """To toggle the caps protection in the server. It won't work if the limit is less than or equal to 0"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"automod.caps.limit": limit if limit > 0 else None}},
        )
        await ctx.reply(
            f"{ctx.author.mention} caps protection limit for this server is set to **{limit}**"
        )

    @capsprotection.command(name="ignore")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from caps protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.caps.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for caps protection"
        )

    @capsprotection.command(name="remove")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from caps protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.caps.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for caps protection"
        )

    @automod.group(name="emoji", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiprotection(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the emoji protection in the server"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.emoji.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} emoji protection for this server is set to **{to_enable}**"
        )

    @emojiprotection.command(name="limit")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojilimit(self, ctx: Context, *, limit: int):
        """To toggle the emoji protection in the server. It won't work if the limit is less than 0"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"automod.emoji.limit": limit if limit > 0 else None}},
        )
        await ctx.reply(
            f"{ctx.author.mention} emoji protection limit for this server is set to **{limit}**"
        )

    @emojiprotection.command(name="ignore")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from emoji protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.emoji.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for emoji protection"
        )

    @emojiprotection.command(name="remove")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from emoji protection"""
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.emoji.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for emoji protection"
        )

    @config.group(aliases=["tel"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def telephone(self, ctx: Context):
        """To set the telephone phone line, in the server to call and receive the call from other server."""
        data = await self.bot.mongo.parrot_db.telephone.find_one({"_id": ctx.guild.id})
        if not data:
            await self.bot.mongo.parrot_db.telephone.insert_one(
                {
                    "_id": ctx.guild.id,
                    "channel": None,
                    "pingrole": None,
                    "is_line_busy": False,
                    "memberping": None,
                    "blocked": [],
                }
            )
        if not ctx.invoked_subcommand:
            data = await self.bot.mongo.parrot_db.telephone.find_one(
                {"_id": ctx.guild.id}
            )
            if data:
                role = (
                    ctx.guild.get_role(data["pingrole"]).name
                    if data.get("pingrole")
                    else None
                )
                channel = (
                    ctx.guild.get_channel(data["channel"]).name
                    if data.get("channel")
                    else None
                )
                member = (
                    await self.bot.get_or_fetch_member(ctx.guild, data["memberping"])
                    if data.get("memberping")
                    else None
                )
                await ctx.reply(
                    f"Configuration of this server [telsetup]\n\n"
                    f"`Channel   :` **{channel}**\n"
                    f"`Pingrole  :` **{role} ({data['pingrole'] or None})**\n"
                    f"`MemberPing:` **{member} ({data['memberping'] or None})**\n"
                    f"`Blocked   :` **{', '.join(data['blocked']) or None}**"
                )

    @telephone.command(name="channel")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_channel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To setup the telephone line in the channel."""
        await self.bot.mongo.parrot_db.telephone(
            ctx.guild.id, {"$set": {"channel": channel.id if channel else None}}
        )
        if not channel:
            return await ctx.reply(
                f"{ctx.author.mention} global telephone line is reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **#{channel.name}** is now added to global telephone line."
        )

    @telephone.command(name="pingrole")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_pingrole(self, ctx: Context, *, role: discord.Role = None):
        """To add the ping role. If other server call your server. Then the role will be pinged if set any"""
        await self.bot.mongo.parrot_db.telephone(
            ctx.guild.id, {"$set": {"pingrole": role.id if role else None}}
        )
        if not role:
            return await ctx.reply(
                f"{ctx.author.mention} ping role reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **@{role.name}** will be now pinged when someone calls your server."
        )

    @telephone.command(name="memberping")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_memberping(
        self, ctx: Context, *, member: discord.Member = None
    ):
        """To add the ping role. If other server call your server. Then the role will be pinged if set any"""
        await self.bot.mongo.parrot_db.telephone(
            ctx.guild.id, {"$set": {"memberping": member.id if member else None}}
        )
        if not member:
            return await ctx.reply(
                f"{ctx.author.menton} member ping reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **@{member.name}#{member.discriminator}** will be now pinged when someone calls your server."
        )

    @telephone.command(name="block")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_block(self, ctx: Context, *, server: discord.Guild):
        """There are people who are really anonying, you can block them."""
        if server is ctx.guild:
            return await ctx.reply(f"{ctx.author.mention} can't block your own server")

        await self.bot.mongo.parrot_db.telephone.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"blocked": server.id}}
        )
        await ctx.reply(f"{ctx.author.mention} success! blocked: **{server.name}**")

    @telephone.command(name="unblock")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_unblock(self, ctx: Context, *, server: discord.Guild):
        """Now they understood their mistake. You can now unblock them."""
        if server is ctx.guild:
            return await ctx.reply(
                f"{ctx.author.mention} ok google, let the server admin get some rest"
            )
        await self.bot.mongo.parrot_db.telephone.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"blocked": server.id}}
        )
        await ctx.reply(f"{ctx.author.mention} Success! unblocked: {server.id}")

    @commands.group(aliases=["ticketsetup"], invoke_without_command=True)
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def ticketconfig(self, ctx: Context):
        """To config the Ticket Parrot Bot in the server"""
        data = await self.bot.mongo.parrot_db.ticket.find_one({"_id": ctx.guild.id})
        if not data:
            await self.bot.mongo.parrot_db.ticket.insert_one(
                {
                    "_id": ctx.guild.id,
                    "ticket_counter": 0,
                    "valid_roles": [],
                    "pinged_roles": [],
                    "ticket_channel_ids": [],
                    "verified_roles": [],
                    "message_id": None,
                    "log": None,
                    "category": None,
                    "channel_id": None,
                }
            )
        if not ctx.invoked_subcommand:
            data = await self.bot.mongo.parrot_db.ticket.find_one({"_id": ctx.guild.id})

            ticket_counter = data["ticket_counter"]
            valid_roles = (
                ", ".join(ctx.guild.get_role(n).name for n in data["valid_roles"])
                if data.get("valid_roles")
                else None
            )
            pinged_roles = (
                ", ".join(ctx.guild.get_role(n).name for n in data["pinged_roles"])
                if data.get("pinged_roles")
                else None
            )
            current_active_channel = (
                ", ".join(
                    ctx.guild.get_channel(n).name for n in data["ticket_channel_ids"]
                )
                if data.get("ticket_channel_ids")
                else None
            )
            verified_roles = (
                ", ".join(ctx.guild.get_role(n).name for n in data["verified_roles"])
                if data.get("verified_roles")
                else None
            )
            category = (
                ctx.guild.get_channel(data["category"])
                if data.get("category")
                else None
            )
            await ctx.reply(
                f"Configuration of this server [ticket]\n\n"
                f"`Total Ticket made  :` **{ticket_counter}**\n"
                f"`Valid Roles (admin):` **{valid_roles}**\n"
                f"`Pinged Roles       :` **{pinged_roles}**\n"
                f"`Active Channel     :` **{current_active_channel}**\n"
                f"`Verifed Roles (mod):` **{verified_roles}**\n"
                f"`Category Channel   :` **{category}**"
            )

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def auto(
        self, ctx: Context, channel: discord.TextChannel = None, *, message: str = None
    ):
        """Automatic ticket making system. On reaction basis"""
        channel = channel or ctx.channel
        message = message or "React to \N{ENVELOPE} to create ticket"
        await mt._auto(ctx, channel, message)

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def setcategory(self, ctx: Context, *, channel: discord.CategoryChannel):
        """Where the new ticket will created? In category or on the TOP."""
        await mt._setcategory(ctx, channel)

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def setlog(self, ctx: Context, *, channel: discord.TextChannel):
        """Where the tickets action will logged? To config the ticket log."""
        await mt._setlog(ctx, channel)

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def addaccess(self, ctx: Context, *, role: discord.Role):
        """
        This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.

        Parrot Ticket `Admin-Level` role or Administrator permission for the user.
        """
        await mt._addaccess(ctx, role)

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def delaccess(self, ctx: Context, *, role: discord.Role):
        """
        This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.

        Parrot Ticket `Admin-Level` role or Administrator permission for the user.
        """
        await mt._delaccess(ctx, role)

    @ticketconfig.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def addadminrole(self, ctx: Context, *, role: discord.Role):
        """This command gives all users with a specific role access to the admin-level commands for the bot,
        such as `Addpingedrole` and `Addaccess`."""
        await mt._addadimrole(ctx, role)

    @ticketconfig.command(hidden=False)
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def addpingedrole(self, ctx: Context, *, role: discord.Role):
        """This command adds a role to the list of roles that are pinged when a new ticket is created.
        This command can only be run if you have an admin-level role for this bot."""
        await mt._addpingedrole(ctx, role)

    @ticketconfig.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def deladminrole(self, ctx: Context, *, role: discord.Role):
        """This command removes access for all users with the specified role to the admin-level commands for the bot,
        such as `Addpingedrole` and `Addaccess`."""
        await mt._deladminrole(ctx, role)

    @ticketconfig.command()
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def delpingedrole(self, ctx: Context, *, role: discord.Role):
        """This command removes a role from the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot."""
        await mt._delpingedrole(ctx, role)

    @config.group(
        name="command",
        aliases=[
            "cmd",
        ],
    )
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def cmdconfig(self, ctx: Context):
        """Command Management of the server"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @cmdconfig.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def enable(
        self,
        ctx: Context,
        command: commands.clean_content,
        target: typing.Union[discord.TextChannel, discord.Role] = None,
        force: str = None,
    ):
        """To enable the command"""
        cmd = self.bot.get_command(command)
        cog = self.bot.get_cog(command)
        if cmd is not None:
            await mt_._enable(self.bot, ctx, cmd.qualified_name, target, force)
        elif cog is not None:
            await mt_._enable(self.bot, ctx, cog.qualified_name, target, force)
        elif command == "all":
            await mt_._enable(self.bot, ctx, "all", target, force)
        else:
            await ctx.send(
                f"{ctx.author.mention} {command} is nither command nor any category"
            )

    @cmdconfig.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def disable(
        self,
        ctx: Context,
        command: commands.clean_content,
        target: typing.Union[discord.TextChannel, discord.Role] = None,
        force: str = None,
    ):
        """To disable the command"""
        cmd = self.bot.get_command(command)
        cog = self.bot.get_cog(command)
        if cmd is not None:
            await mt_._disable(self.bot, ctx, cmd.qualified_name, target, force)
        elif cog is not None:
            await mt_._disable(self.bot, ctx, cog.qualified_name, target, force)
        elif command == "all":
            await mt_._disable(self.bot, ctx, "all", target, force)
        else:
            await ctx.send(
                f"{ctx.author.mention} {command} is nither command nor any category"
            )

    @cmdconfig.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def list(self, ctx: Context):
        """To view what all configuation are being made with command"""
        enable_disable = self.bot.mongo.enable_disable
        em_lis = []
        collection = enable_disable[f"{ctx.guild.id}"]
        async for data in collection.find({}):
            main = f"> Command/Cog: {data['_id']}"
            if data.get("channel_in"):
                main += f"\n`Channel In :` <#{'>, <#'.join([(str(c) for c in data['channel_in'])])}>"
            if data.get("channel_out"):
                main += f"\n`Channel Out:` <#{'>, <#'.join([(str(c) for c in data['channel_out'])])}>"
            if data.get("role_in"):
                main += f"\n`Role In    :` <@&{'>, <@&'.join([(str(c) for c in data['role_in'])])}>"
            if data.get("role_out"):
                main += f"\n`Role In    :` <@&{'>, <@&'.join([(str(c) for c in data['role_out'])])}>"
            if data.get("server"):
                main += f"`\nServer Wide?:` {data['server']}"

        if not em_lis:
            return await ctx.send(
                f"{ctx.author.mention} no commands/category overwrite found"
            )
        p = SimplePages(em_lis, ctx=ctx, per_page=3)
        await p.start()

    @cmdconfig.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def clear(self, ctx: Context):
        """To clear all overrides"""
        enable_disable = self.bot.mongo.enable_disable
        collection = enable_disable[f"{ctx.guild.id}"]
        await collection.drop()
        await ctx.send(f"{ctx.author.mention} reseted everything!")

    @commands.command(name="autowarn")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def autowarn(self, ctx: Context, action: str, *, flags: AutoWarn):
        """Autowarn management of the server"""
        PUNISH = [
            "ban",
            "tempban",
            "kick",
            "timeout",
            "mute",
            "block",
        ]
        ACTIONS = ["antilinks", "profanity", "spam", "emoji", "caps"]

        if action.lower() not in ACTIONS:
            await ctx.send(
                f"{ctx.author.mention} invalid event! Available event: **{'**, **'.join(ACTIONS)}**"
            )
            return
        _ = ShortTime(flags.duration)  # flake8: noqa

        data = {
            "enable": flags.enable,
            "count": flags.count,
            "to_delete": flags.delete,
            "punish": {
                "type": flags.punish.lower()
                if str(flags.punish).lower() in PUNISH
                else None,
                "duration": flags.duration
                if str(flags.punish).lower() not in ("kick", "ban")
                else None,
            },
        }
        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {"$set": {f"automod.{action.lower()}.autowarn": data}},
        )
        await ctx.send(
            f"""{ctx.author.mention} configuration you set:
`Warn Enabed`: {data.get('enabled')}
`Warn Count `: {data.get('warn_count')}
`To delete  `: {data.get('to_delete')}
`Punish Type`: {data['punish']['type']}
`Duration   `: {data['punish']['duration']}
"""
        )

    @config.group(name="serverstats", aliases=["sstats"])
    @commands.has_permissions(administrator=True)
    async def serverstats(self, ctx: Context):
        """Creates Fancy counters that everyone can see"""
        if ctx.invoked_subcommand is None:
            return await self.bot.invoke_help_command(ctx)

    @serverstats.command(name="create")
    @commands.has_permissions(administrator=True)
    async def serverstats_create(
        self,
        ctx: Context,
    ):
        """Creates a server stats counter"""
        AVAILABLE_COUNTER = [
            "bots",
            "members",
            "channels",
            "voice",
            "text",
            "categories",
            "emojis",
            "roles",
            "role",
        ]
        AVAILABLE_TYPE = [
            "voice",
            "text",
            "category",
        ]
        PAYLOAD = {}
        OP = "$set"

        QUES = [
            f"What type of counter you want to setup? (`{'`, `'.join(AVAILABLE_COUNTER)}`)",
            f"What type of channel you want? (`{'`, `'.join(AVAILABLE_TYPE)}`)",
            r"What should be the format of the channel? Example: `Total Channels {}`, `{} Roles in total`. Only the `{}` will be replaced with the counter value.",
        ]

        async def wait_for_response() -> typing.Optional[str]:
            def check(m: discord.Message) -> bool:
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
                return msg.content.lower()
            except asyncio.TimeoutError:
                raise commands.BadArgument(
                    f"{ctx.author.mention} You took too long to respond!"
                )

        await ctx.send(f"{ctx.author.mention} {QUES[0]}")
        counter = await wait_for_response()

        if counter not in AVAILABLE_COUNTER:
            return await ctx.send(
                f"{ctx.author.mention} invalid counter! Available counter: `{'`, `'.join(AVAILABLE_COUNTER)}`"
            )
        if counter == "role":
            OP = "$addToSet"
            await ctx.send(
                f"{ctx.author.mention} Enter the role name/ID or you can even mention it"
            )
            role = await wait_for_response()
            try:
                role = await commands.RoleConverter().convert(ctx, role)
            except commands.BadArgument:
                return await ctx.send(
                    f"{ctx.author.mention} invalid role! Please enter a valid role name/ID"
                )
            else:
                PAYLOAD["role_id"] = role.id

        await ctx.send(f"{ctx.author.mention} {QUES[1]}")
        channel_type = await wait_for_response()
        if channel_type not in AVAILABLE_TYPE:
            return await ctx.send(
                f"{ctx.author.mention} invalid channel type! Available channel type: `{'`, `'.join(AVAILABLE_TYPE)}`"
            )
        PAYLOAD[f"{counter}.channel_type"] = channel_type

        await ctx.send(f"{ctx.author.mention} {QUES[2]}")
        _format = await wait_for_response()
        if r"{}" not in _format:
            return await ctx.send(
                f"{ctx.author.mention} invalid format! Please provide a valid format."
            )
        PAYLOAD[f"{counter}.template"] = _format

        channel = 0
        try:
            if channel_type == "text":
                channel = await ctx.guild.create_text_channel(
                    _format.format(counter),
                    position=0,
                    reason=f"Action requested by {ctx.author} ({ctx.author.id})",
                )
            elif channel_type == "voice":
                channel = await ctx.guild.create_voice_channel(
                    _format.format(counter),
                    position=0,
                    reason=f"Action requested by {ctx.author} ({ctx.author.id})",
                )
            elif channel_type == "category":
                channel = await ctx.guild.create_category(
                    _format.format(counter),
                    position=0,
                    reason=f"Action requested by {ctx.author} ({ctx.author.id})",
                )
        except (ValueError, IndexError):
            return await ctx.send(
                f"{ctx.author.mention} invalid format! Please provide a valid format."
            )
        PAYLOAD[f"{counter}.channel_id"] = (
            channel.id if isinstance(channel, discord.abc.Messageable) else channel
        )

        await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id},
            {
                OP: {f"stats_channels.{k}": v for k, v in PAYLOAD.items()}
                if counter != "role"
                else {"role": PAYLOAD}
            },
            upsert=True,
        )

        await ctx.send(
            f"{ctx.author.mention} counter created at #{channel.name} ({channel.mention})"
        )

    @serverstats.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def serverstats_delete(
        self,
        ctx: Context,
        counter: str,
    ):
        """Deletes a server stats counter"""
        AVAILABLE = [
            "bots",
            "members",
            "channels",
            "voice",
            "text",
            "categories",
            "emojis",
            "roles",
        ]
        if counter.lower() not in AVAILABLE:
            return await ctx.send(
                f"{ctx.author.mention} invalid counter! Available counter: `{'`, `'.join(AVAILABLE)}`"
            )
        if data := await self.bot.mongo.parrot_db.server_config.update_one(
            {"_id": ctx.guild.id, "stats_channels": {"$exists": True}},
            {
                "$set": {
                    f"stats_channels.{counter}.channel_id": None,
                    f"stats_channels.{counter}.channel_type": None,
                    f"stats_channels.{counter}.template": None,
                }
            },
        ):
            await ctx.send(f"{ctx.author.mention} counter deleted")
