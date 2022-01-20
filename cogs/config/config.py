from __future__ import annotations

from discord.ext import commands
import discord
import typing
import re

import json

from core import Parrot, Context, Cog
from datetime import datetime

from utilities.database import guild_update, gchat_update, parrot_db, telephone_update
from utilities.paginator import PaginationView
from utilities.checks import has_verified_role_ticket
from utilities.converters import convert_bool
from utilities.time import ShortTime

from .flags import AutoWarn, warnConfig

from cogs.ticket import method as mt
from cogs.config import method as mt_


with open(r"cogs/config/events.json") as f:
    events = json.load(f)

ct = parrot_db["telephone"]
csc = parrot_db["server_config"]
ctt = parrot_db["ticket"]
logs = parrot_db["logging"]


class BotConfig(Cog):
    """To config the bot. In the server"""

    def __init__(self, bot: Parrot):
        self.bot = bot

    async def log_in(self, guild: int):
        try:
            await logs.insert_one({"_id": guild})
        except Exception:
            pass

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
        data = await csc.find_one({"_id": ctx.guild.id})
        if not ctx.invoked_subcommand:
            data = await csc.find_one({"_id": ctx.guild.id})
            if data:
                role = ctx.guild.get_role(data.get("mod_role"))
                mod_log = ctx.guild.get_channel(data.get("action_log"))
                await ctx.reply(
                    f"Configuration of this server [server_config]\n\n"
                    f"`Prefix :` **{data['prefix']}**\n"
                    f"`ModRole:` **{role.name if role else 'None'} ({data.get('mod_role')})**\n"
                    f"`MogLog :` **{mod_log.mention if mod_log else 'None'} ({data.get('action_log')})**\n"
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
        await self.log_in(ctx.guild.id)
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
                    await logs.update_one({"_id": ctx.guild.id}, {"$set": post})
                    break
            else:
                return await ctx.reply(
                    f"{ctx.author.mention} can not register event (`{event.replace('_', ' ').title()}`) in {channel.mention}. This happens when channel has already 10 webhooks created."
                )
        else:
            webhook = await channel.create_webhook(
                name=self.bot.user.name,
                reason=f"On request from {ctx.author} | Reason: Setting Up Logging",
            )
            await logs.update_one(
                {"_id": ctx.guild.id}, {"$set": {str(event): str(webhook.url)}}
            )
        await ctx.reply(
            f"{ctx.author.mention} all `{event.replace('_', ' ').title()}` will be posted on {channel.mention}"
        )

    @config.command(aliases=["prefix"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def botprefix(self, ctx: Context, *, arg: str):
        """To set the prefix of the bot. Whatever prefix you passed, will be case sensitive. It is advised to keep a symbol as a prefix. Must not greater than 6 chars"""
        if len(arg) > 6:
            return await ctx.reply(
                f"{ctx.author.mention} length of prefix can not be more than 6 characters."
            )
        post = {"prefix": arg}
        await guild_update(ctx.guild.id, post)

        await ctx.reply(
            f"{ctx.author.mention} success! Prefix for **{ctx.guild.name}** is **{arg}**."
        )

    @config.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def warnadd(
        self, ctx: Context, count: int, action: str, duration: ShortTime = None
    ):
        """To configure the warn settings"""
        ACTIONS = [
            "ban",
            "tempban",
            "kick",
            "timeout",
            "mute",
            "block",
        ]
        if action.lower() not in ACTIONS:
            return await ctx.send(
                f"{ctx.author.mention} invalid action. Available actions: `{'`, `'.join(ACTIONS)}`"
            )

        if _ := await csc.find_one({"_id": ctx.guild.id, "warn_db.count": count}):
            return await ctx.send(
                f"{ctx.author.mention} warn count {count} already exists."
            )
        await csc.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "warn_auto": [
                        {
                            "count": count,
                            "action": action.lower(),
                            "duration": duration.dt.timestamp()
                            - datetime.utcnow().timestamp()
                            if duration
                            else None,
                        }
                    ]
                }
            },
        )

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
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"warn_auto": {**payload}}}
        )

    @config.command(aliases=["mute-role"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def muterole(self, ctx: Context, *, role: discord.Role = None):
        """To set the mute role of the server. By default role with name `Muted` is consider as mute role."""
        post = {"mute_role": role.id if role else None}
        await guild_update(ctx.guild.id, post)
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
        await guild_update(ctx.guild.id, post)
        if not role:
            return await ctx.reply(f"{ctx.author.mention} mod role reseted! or removed")
        await ctx.reply(
            f"{ctx.author.mention} success! Mod role for **{ctx.guild.name}** is **{role.name} ({role.id})**"
        )

    @config.command(aliases=["action-log", "modlog", "mod-log"])
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def actionlog(self, ctx: Context, *, channel: discord.TextChannel = None):
        """To set the action log, basically the mod log."""
        post = {"action_log": channel.id if channel else None}
        await guild_update(ctx.guild.id, post)
        if not channel:
            return await ctx.reply(
                f"{ctx.author.mention} action log reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! Action log for **{ctx.guild.name}** is **{channel.name} ({channel.id})**"
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
        c = parrot_db["global_chat"]
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
            if data := await c.find_one({"_id": ctx.guild.id}):
                await c.update_one(
                    {"_id": ctx.guild.id},
                    {"$set": {"channel_id": channel.id, "webhook": webhook.url}},
                )
            else:
                await c.insert_one(
                    {
                        "_id": ctx.guild.id,
                        "channel_id": channel.id,
                        "webhook": webhook.url,
                        "ignore-role": None,
                    }
                )
            await ctx.reply(f"{channel.mention} created successfully.")
        elif setting.lower() in ("ignore-role", "ignore_role", "ignorerole"):
            post = {"ignore-role": role.id if role else None}
            await gchat_update(ctx.guild.id, post)
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
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"counting": channel.id if channel else None}},
        )
        if channel:
            await ctx.reply(
                f"{ctx.author.mention} counting channel for the server is set to **{channel.name}**"
            )
        else:
            await ctx.reply(
                f"{ctx.author.mention} counting channel for the server is not removed"
            )

    @config.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def onewordchannel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To set the one word channel in the server"""
        await csc.update_one(
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

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antispam(self, ctx: Context, to_enable: convert_bool):
        """To toggle the spam protection in the server"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.spam.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection in the server is set to **{to_enable}**. "
            "Note: As per discord API it is allowed to send **5 messages** within **5 seconds** of interval in channel. "
            "Bot will be issuing warning if someone exceeds the limit."
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def spamignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the spam channel. Pass None to delete the setting"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.spam.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection won't be working in **{channel.name}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def spamremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the spam channel. Pass None to delete the setting"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.spam.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} spam protection will be working in **{channel.name}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antilinks(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the invite protection in the server"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.antilinks.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} anti links protection in the server is set to **{to_enable}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antilinksignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To whitelist the channel from anti links protection"""
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.antilinks.channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for links protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def antilinksremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove whitelisted channel from anti links protection"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.antilinks.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for links protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def whitelistlink(self, ctx: Context, *, link: str):
        """To whitelist a link."""
        try:
            re.compile(link)
        except re.error:
            return await ctx.reply(f"{ctx.author.mention} invalid regex expression")
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.antilinks.whitelist": link}}
        )
        await ctx.reply(
            f"{ctx.author.mention} **<{link}>** added for the whitelist link"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def blacklistlink(self, ctx: Context, *, link: str):
        """To remove whitelisted link."""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.antilinks.whitelist": link}}
        )
        await ctx.reply(
            f"{ctx.author.mention} **<{link}>** removed for the whitelist link"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityadd(self, ctx: Context, *, word: str):
        """To add profanity words. Can also work for regex. May take 1h to update"""
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.profanity.words": word.lower()}},
        )
        await ctx.reply(f"{ctx.author.mention} **||{word}||** added in the list")

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanitydel(self, ctx: Context, *, word: str):
        """To remove profanity word from list. Can also work for regex"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.profanity.words": word.lower()}}
        )
        await ctx.reply(f"{ctx.author.mention} **||{word}||** removed from the list")

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanity(self, ctx: Context, *, to_enable: convert_bool):
        """To add profanity words. Can also work for regex"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.profanity.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} profanity system in this server is set to **{to_enable}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from profanity"""
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"automod.profanity.channel": channel.id}},
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for profanity protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def profanityremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from profanity"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.profanity.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for profanity protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsprotection(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the caps protection in the server"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.caps.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} caps protection for this server is set to **{to_enable}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capslimit(self, ctx: Context, *, limit: int):
        """To toggle the caps protection in the server. It won't work if the limit is less than or equal to 0"""
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"automod.caps.limit": limit if limit > 0 else None}},
        )
        await ctx.reply(
            f"{ctx.author.mention} caps protection limit for this server is set to **{limit}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from caps protection"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.caps.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for caps protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def capsremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from caps protection"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.caps.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for caps protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiprotection(self, ctx: Context, *, to_enable: convert_bool):
        """To toggle the emoji protection in the server"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$set": {"automod.emoji.enable": to_enable}}
        )
        await ctx.reply(
            f"{ctx.author.mention} emoji protection for this server is set to **{to_enable}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojilimit(self, ctx: Context, *, limit: int):
        """To toggle the emoji protection in the server. It won't work if the limit is less than 0"""
        await csc.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"automod.emoji.limit": limit if limit > 0 else None}},
        )
        await ctx.reply(
            f"{ctx.author.mention} emoji protection limit for this server is set to **{limit}**"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiignore(self, ctx: Context, *, channel: discord.TextChannel):
        """To ignore the channel from emoji protection"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"automod.emoji.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} added **{channel.name}** in whitelist, for emoji protection"
        )

    @automod.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def emojiremove(self, ctx: Context, *, channel: discord.TextChannel):
        """To remove the ignored channel from emoji protection"""
        await csc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"automod.emoji.channel": channel.id}}
        )
        await ctx.reply(
            f"{ctx.author.mention} removed **{channel.name}** in whitelist, for emoji protection"
        )

    @commands.group(aliases=["telconfig"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def telsetup(self, ctx: Context):
        """To set the telephone phone line, in the server to call and receive the call from other server."""
        data = await ct.find_one({"_id": ctx.guild.id})
        if not data:
            await ct.insert_one(
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
            data = await ct.find_one({"_id": ctx.guild.id})
            if data:
                role = (
                    ctx.guild.get_role(data["pingrole"]).name
                    if data["pingrole"]
                    else None
                )
                channel = (
                    ctx.guild.get_channel(data["channel"]).name
                    if data["channel"]
                    else None
                )
                member = (
                    ctx.guild.get_member(data["memberping"]).name
                    if data["memberping"]
                    else None
                )
                await ctx.reply(
                    f"Configuration of this server [telsetup]\n\n"
                    f"`Channel   :` **{channel}**\n"
                    f"`Pingrole  :` **{role} ({data['pingrole'] or None})**\n"
                    f"`MemberPing:` **{member} ({data['memberping'] or None})**\n"
                    f"`Blocked   :` **{', '.join(data['blocked']) or None}**"
                )

    @telsetup.command(name="channel")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_channel(
        self, ctx: Context, *, channel: discord.TextChannel = None
    ):
        """To setup the telephone line in the channel."""
        await telephone_update(ctx.guild.id, "channel", channel.id if channel else None)
        if not channel:
            return await ctx.reply(
                f"{ctx.author.mention} global telephone line is reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **#{channel.name}** is now added to global telephone line."
        )

    @telsetup.command(name="pingrole")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_pingrole(self, ctx: Context, *, role: discord.Role = None):
        """To add the ping role. If other server call your server. Then the role will be pinged if set any"""
        await telephone_update(ctx.guild.id, "pingrole", role.id if role else None)
        if not role:
            return await ctx.reply(
                f"{ctx.author.mention} ping role reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **@{role.name}** will be now pinged when someone calls your server."
        )

    @telsetup.command(name="memberping")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_memberping(
        self, ctx: Context, *, member: discord.Member = None
    ):
        """To add the ping role. If other server call your server. Then the role will be pinged if set any"""
        await telephone_update(
            ctx.guild.id, "memberping", member.id if member else None
        )
        if not member:
            return await ctx.reply(
                f"{ctx.author.menton} member ping reseted! or removed"
            )
        await ctx.reply(
            f"{ctx.author.mention} success! **@{member.name}#{member.discriminator}** will be now pinged when someone calls your server."
        )

    @telsetup.command(name="block")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_block(self, ctx: Context, *, server: discord.Guild):
        """There are people who are really anonying, you can block them."""
        if server is ctx.guild:
            return await ctx.reply(f"{ctx.author.mention} can't block your own server")

        await ct.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"blocked": server.id}}
        )
        await ctx.reply(f"{ctx.author.mention} success! blocked: **{server.name}**")

    @telsetup.command(name="unblock")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def tel_config_unblock(self, ctx: Context, *, server: discord.Guild):
        """Now they understood their mistake. You can now unblock them."""
        if server is ctx.guild:
            return await ctx.reply(
                f"{ctx.author.mention} ok google, let the server admin get some rest"
            )
        await ct.update_one({"_id": ctx.guild.id}, {"$pull": {"blocked": server.id}})
        await ctx.reply(f"{ctx.author.mention} Success! unblocked: {server.id}")

    @commands.group(aliases=["ticketsetup"], invoke_without_command=True)
    @commands.check_any(
        commands.has_permissions(administrator=True), has_verified_role_ticket()
    )
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def ticketconfig(self, ctx: Context):
        """To config the Ticket Parrot Bot in the server"""
        data = await ctt.find_one({"_id": ctx.guild.id})
        if not data:
            await ctt.insert_one(
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
            data = await ctt.find_one({"_id": ctx.guild.id})

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

    @commands.group(aliases=["cmdc", "configcmd"])
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
        enable_disable = await self.bot.db("enable_disable")
        em_lis = []
        collection = enable_disable[f"{ctx.guild.id}"]
        async for data in collection.find({}):
            em = discord.Embed(
                title=f"Cmd/Cog: {data['_id']}",
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
            ).set_footer(text=f"{ctx.author}")
            em.description = f"""`Channel In :` {(str(data['channel_in']))}
`Channel Out:` {(str(data['channel_out']))}
`Role In    :` {(str(data['role_in']))}
`Role Out   :` {(str(data['role_out']))}

Server Wide?:{data['server']}"""
            em_lis.append(em)
        paginator = PaginationView(em_lis)
        await paginator.start(ctx)

    @cmdconfig.command()
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def clear(self, ctx: Context):
        """To clear all overrides"""
        enable_disable = await self.bot.db("enable_disable")
        collection = enable_disable[f"{ctx.guild.id}"]
        await collection.drop()
        await ctx.send(f"{ctx.author.mention} reseted everything!")

    @commands.command(name="autowarn")
    @commands.has_permissions(administrator=True)
    @Context.with_type
    async def autowarn(self, ctx: Context, action: str, *, flags: AutoWarn):
        """Autowarn management of the server"""
        PUNISH = [
            "timeout",
            "tempmute",
            "mute",
            "softban",
            "ban",
            "kick",
            "removerole",
            "addrole",
        ]
        ACTIONS = ["antilinks", "profanity", "spam", "emoji", "caps"]

        if action.lower() not in ACTIONS:
            await ctx.send(
                f"{ctx.author.mention} invalid event! Available event: **{'**, **'.join(ACTIONS)}**"
            )
            return
        data = {
            "enabled": flags.enable,
            "count": flags.count,  # NOTE: its just count
            "to_delete": flags.delete,
            "punish": {
                "type": flags.punish if flags.punish in PUNISH else None,
                "duration": datetime.utcnow().timestamp()
                - flags.duration.dt.timestamp()
                if flags.duration
                and flags.punish not in ("kick", "addrole", "removerole")
                else None,
            },
        }
        await csc.update_one(
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
