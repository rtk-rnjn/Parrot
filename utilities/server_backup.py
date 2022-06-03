from __future__ import annotations
import asyncio

from typing import Any, Dict

import discord

from core import Parrot


class BooleanArgs:
    def __init__(self, args):
        self._args = {}
        self.all = False

        for arg in args:
            arg = arg.lower()

            if arg in ("-", "!*"):
                self.all = False
                self._args = {}

            if arg in ("+", "*"):
                self.all = True

            if arg.startswith("!"):
                self._args[arg.strip("!")] = False

            else:
                self._args[arg] = True

    def get(self, item):
        return self.all or self._args.get(item, False)

    def __getattr__(self, item):
        return self.get(item)


class Backup:
    def __init__(
        self,
        bot: Parrot,
        guild: discord.Guild,
    ) -> None:
        self.bot = bot
        self.guild = guild
        self.data = {}

    def __dict__(self) -> Dict[str, Any]:
        return self.data

    def _overwrite_to_json(self, overwrites) -> Dict[str, Any]:
        try:
            return {
                str(target.id): overwrite._values
                for target, overwrite in overwrites.items()
            }
        except Exception:
            return {}

    async def _save_channels(self):
        for category in self.guild.categories:
            try:
                self.data["categories"].append(
                    {
                        "id": str(category.id),
                        "name": category.name,
                        "position": category.position,
                        "overwrites": self._overwrite_to_json(category.overwrites),
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

        for tchannel in self.guild.text_channels:
            try:
                self.data["text_channels"].append(
                    {
                        "name": tchannel.name,
                        "position": tchannel.position,
                        "category": None
                        if tchannel.category is None
                        else str(tchannel.category.id),
                        "id": str(tchannel.id),
                        "overwrites": self._overwrite_to_json(tchannel.overwrites),
                        "topic": tchannel.topic,
                        "slowmode_delay": tchannel.slowmode_delay,
                        "nsfw": tchannel.is_nsfw(),
                        "messages": [],
                        "webhooks": [
                            {
                                "channel": str(webhook.channel.id),
                                "name": webhook.name,
                                "avatar": str(webhook.avatar_url),
                                "url": webhook.url,
                            }
                            for webhook in await tchannel.webhooks()
                        ],
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

        for vchannel in self.guild.voice_channels:
            try:
                self.data["voice_channels"].append(
                    {
                        "id": str(vchannel.id),
                        "name": vchannel.name,
                        "position": vchannel.position,
                        "category": None
                        if vchannel.category is None
                        else str(vchannel.category.id),
                        "overwrites": self._overwrite_to_json(vchannel.overwrites),
                        "bitrate": vchannel.bitrate,
                        "user_limit": vchannel.user_limit,
                        "rtc_region": str(vchannel.rtc_region),
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

        for schannel in self.guild.stage_channels:
            try:
                self.data["stage_channels"].append(
                    {
                        "id": str(schannel.id),
                        "name": schannel.name,
                        "position": schannel.position,
                        "category": None
                        if schannel.category is None
                        else str(schannel.category.id),
                        "overwrites": self._overwrite_to_json(schannel.overwrites),
                        "bitrate": schannel.bitrate,
                        "user_limit": schannel.user_limit,
                        "rtc_region": str(schannel.rtc_region),
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

    async def _save_roles(self):
        for role in self.guild.roles:
            try:
                if role.managed:
                    continue

                self.data["roles"].append(
                    {
                        "id": str(role.id),
                        "default": role.is_default(),
                        "name": role.name,
                        "permissions": role.permissions.value,
                        "color": role.color.value,
                        "hoist": role.hoist,
                        "position": role.position,
                        "mentionable": role.mentionable,
                        "icon": role.icon.url if role.icon else None,
                        "unicode_emoji": role.unicode_emoji
                        if role.unicode_emoji
                        else None,
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

    async def _save_members(self):
        if self.guild.large:
            await self.bot.request_offline_members(self.guild)

        async for member in self.guild.fetch_members(limit=1000):
            try:
                self.data["members"].append(
                    {
                        "id": str(member.id),
                        "name": member.name,
                        "discriminator": member.discriminator,
                        "nick": member.nick,
                        "roles": [
                            str(role.id)
                            for role in member.roles[1:]
                            if not role.managed
                        ],
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(0)

    async def _save_bans(self):
        for reason, user in await self.guild.bans():
            try:
                self.data["bans"].append({"user": str(user.id), "reason": reason})
            except Exception:
                pass

            await asyncio.sleep(0)

    async def save(
        self,
    ):
        self.data = {
            "id": str(self.guild.id),
            "name": self.guild.name,
            "icon_url": str(self.guild.icon.url),
            "owner": str(self.guild.owner_id),
            "member_count": self.guild.member_count,
            "system_channel": str(self.guild.system_channel),
            "afk_timeout": self.guild.afk_timeout,
            "afk_channel": None
            if self.guild.afk_channel is None
            else str(self.guild.afk_channel.id),
            "mfa_level": str(self.guild.mfa_level.value),
            "verification_level": str(self.guild.verification_level),
            "explicit_content_filter": str(self.guild.explicit_content_filter),
            "large": self.guild.large,
            "banner": self.guild.banner.url if self.guild.banner else None,
            "text_channels": [],
            "voice_channels": [],
            "stage_channels": [],
            "categories": [],
            "roles": [],
            "members": [],
            "bans": [],
            "premium_progress_bar_enabled": self.guild.premium_progress_bar_enabled,
        }

        execution_order = [
            self._save_roles,
            self._save_channels,
            self._save_members,
            self._save_bans,
        ]

        for method in execution_order:
            try:
                await method()
            except Exception:
                pass

        return self.data


class BackupLoader:
    def __init__(self, bot: Parrot, data):
        self.data = data
        self.bot = bot
        self.id_translator = {}
        self.options = BooleanArgs([])
        self.semaphore = asyncio.Semaphore(2)

    async def _overwrites_from_json(self, json):
        overwrites = {}
        for union_id, overwrite in json.items():
            try:
                union = await self.bot.get_or_fetch_member(self.guild, int(union_id))
            except discord.NotFound:
                roles = list(
                    filter(
                        lambda r: r.id == self.id_translator.get(union_id),
                        self.guild.roles,
                    )
                )
                if len(roles) == 0:
                    continue

                union = roles[0]

            overwrites[union] = discord.PermissionOverwrite(**overwrite)

        return overwrites

    def _translate_mentions(self, text):
        if not text:
            return text

        formats = ["<#%s>", "<@&%s>"]
        for key, value in self.id_translator.items():
            for _format in formats:
                text = text.replace(_format % str(key), _format % str(value))

        return text

    async def run_tasks(self, coros, wait=True):
        async def executor(_coro):
            try:
                await _coro

            except Exception:
                pass

            finally:
                self.semaphore.release()

        tasks = []
        for coro in coros:
            await self.semaphore.acquire()
            tasks.append(self.bot.loop.create_task(executor(coro)))

        if wait and tasks:
            await asyncio.wait(tasks)

    async def _prepare_guild(self):
        if self.options.roles:
            existing_roles = list(
                filter(
                    lambda r: not r.managed
                    and self.guild.me.top_role.position > r.position,
                    self.guild.roles,
                )
            )
            difference = len(self.data["roles"]) - len(existing_roles)
            for role in existing_roles:
                if difference < 0:
                    try:
                        await role.delete(reason=self.reason)
                    except Exception:
                        pass

                    else:
                        difference += 1

                else:
                    break

        if self.options.channels:
            for channel in self.guild.channels:
                try:
                    await channel.delete(reason=self.reason)
                except Exception:
                    pass

    async def _load_settings(self):
        await self.guild.edit(
            name=self.data["name"],
            afk_channel=self.guild.get_channel(
                self.id_translator.get(self.data["afk_channel"])
            ),
            afk_timeout=self.data["afk_timeout"],
            # verification_level=discord.VerificationLevel(self.data["verification_level"]),
            system_channel=self.guild.get_channel(
                self.id_translator.get(self.data["system_channel"])
            ),
            reason=self.reason,
        )

    async def _load_roles(self):
        existing_roles = list(
            reversed(
                list(
                    filter(
                        lambda r: not r.managed
                        and not r.is_default()
                        and self.guild.me.top_role.position > r.position,
                        self.guild.roles,
                    )
                )
            )
        )
        for role in reversed(self.data["roles"]):
            try:
                if role["default"]:
                    await self.guild.default_role.edit(
                        permissions=discord.Permissions(role["permissions"])
                    )
                    new_role = self.guild.default_role
                else:
                    kwargs = {
                        "name": role["name"],
                        "hoist": role["hoist"],
                        "mentionable": role["mentionable"],
                        "color": discord.Color(role["color"]),
                        "permissions": discord.Permissions.none(),
                        "reason": self.reason,
                    }

                    if role["unicode_emoji"]:
                        kwargs["unicode_emoji"] = role["unicode_emoji"]

                    if len(existing_roles) == 0:
                        try:
                            new_role = await asyncio.wait_for(
                                self.guild.create_role(**kwargs), 10
                            )
                        except asyncio.TimeoutError:
                            # Probably hit the 24h rate limit. Just skip roles
                            break
                    else:
                        new_role = existing_roles.pop(0)
                        await new_role.edit(**kwargs)

                self.id_translator[role["id"]] = new_role.id
            except Exception:
                pass

    async def _load_role_permissions(self):
        tasks = []
        for role in self.data["roles"]:
            to_edit = self.guild.get_role(self.id_translator.get(role["id"]))
            if to_edit:
                tasks.append(
                    to_edit.edit(permissions=discord.Permissions(role["permissions"]))
                )

        await self.run_tasks(tasks)

    async def _load_categories(self):
        for category in self.data["categories"]:
            try:
                created = await self.guild.create_category_channel(
                    name=category["name"],
                    overwrites=await self._overwrites_from_json(category["overwrites"]),
                    reason=self.reason,
                )
                self.id_translator[category["id"]] = created.id
            except Exception:
                pass

    async def _load_text_channels(self):
        for tchannel in self.data["text_channels"]:
            try:
                created = await self.guild.create_text_channel(
                    name=tchannel["name"],
                    overwrites=await self._overwrites_from_json(tchannel["overwrites"]),
                    category=discord.Object(
                        self.id_translator.get(tchannel["category"])
                    ),
                    reason=self.reason,
                )

                self.id_translator[tchannel["id"]] = created.id
                await created.edit(
                    topic=self._translate_mentions(tchannel["topic"]),
                    nsfw=tchannel["nsfw"],
                )
            except Exception:
                pass

    async def _load_voice_channels(self):
        for vchannel in self.data["voice_channels"]:
            try:
                created = await self.guild.create_voice_channel(
                    name=vchannel["name"],
                    overwrites=await self._overwrites_from_json(vchannel["overwrites"]),
                    category=discord.Object(
                        self.id_translator.get(vchannel["category"])
                    ),
                    reason=self.reason,
                )
                await created.edit(
                    bitrate=vchannel["bitrate"], user_limit=vchannel["user_limit"]
                )
                self.id_translator[vchannel["id"]] = created.id
            except Exception:
                pass

    async def _load_channels(self):
        await self._load_categories()
        await self._load_text_channels()
        await self._load_voice_channels()

    async def _load_bans(self):

        tasks = [
            self.guild.ban(user=discord.Object(int(ban["user"])), reason=ban["reason"])
            for ban in self.data["bans"]
        ]
        await self.run_tasks(tasks)

    async def _load_members(self):
        async def edit_member(member, member_data):
            roles = [
                discord.Object(self.id_translator.get(role))
                for role in member_data["roles"]
                if role in self.id_translator
            ]

            if self.guild.me.top_role.position > member.top_role.position:
                try:
                    if member != self.guild.owner:
                        await member.edit(
                            nick=member_data.get("nick"),
                            roles=[r for r in member.roles if r.managed] + roles,
                            reason=self.reason,
                        )

                except discord.Forbidden:
                    try:
                        await member.edit(
                            roles=[r for r in member.roles if r.managed] + roles,
                            reason=self.reason,
                        )

                    except discord.Forbidden:
                        await member.add_roles(*roles)

            else:
                await member.add_roles(*roles)

        tasks = []
        default_data = {"nick": None, "roles": []}
        async for member in self.guild.fetch_members(limit=self.guild.member_count):
            fits = list(
                filter(lambda m: m["id"] == str(member.id), self.data["members"])
            )
            if fits:
                tasks.append(edit_member(member, fits[0]))

            else:
                tasks.append(edit_member(member, default_data))

        await self.run_tasks(tasks)

    async def load(self, guild, loader: discord.User, options: BooleanArgs = None):
        self.options = options or self.options
        self.guild = guild
        self.loader = loader
        self.reason = f"Backup loaded by {loader}"

        try:
            await self._prepare_guild()
        except Exception:
            pass

        steps = [
            ("roles", self._load_roles),
            ("channels", self._load_channels),
            ("settings", self._load_settings),
            ("bans", self._load_bans),
            ("members", self._load_members),
            ("roles", self._load_role_permissions),
        ]
        for option, coro in steps:
            if self.options.get(option):
                try:
                    await coro()
                except Exception:
                    pass
