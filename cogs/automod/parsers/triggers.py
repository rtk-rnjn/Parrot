from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot
    from events.on_msg import OnMsg

import re

from discord.utils import maybe_coroutine

from discord import Member, Message
from discord.ext import commands
from utilities.regex import INVITE_RE, LINKS_RE

OPERATRORS = {
    "all": all,
    "any": any,
}


class Trigger:
    def __init__(self, bot: Parrot, data: list[dict], operator: str = "all") -> None:
        self.bot = bot
        self.data = data

        self.cd_x_user_messages_in_y_seconds = None
        self.cd_x_channel_messages_in_y_seconds = None

        self.cd_user_x_mentions_in_y_seconds = None
        self.cd_channel_x_mentions_in_y_seconds = None

        self.cd_x_user_attachments_in_y_seconds = None
        self.cd_x_channel_attachments_in_y_seconds = None

        self.cd_x_user_links_in_y_seconds = None
        self.cd_x_channel_links_in_y_seconds = None

        self.operator = OPERATRORS[operator]

        self.build_cooldowns()

    def __repr__(self) -> str:
        return f"<Trigger data={self.data}>"

    async def check(self, **kw) -> bool:
        if not self.data:
            return False
        ls = []
        for tgr in self.data:
            func = getattr(self, tgr["type"])
            value = await maybe_coroutine(func, **kw, **tgr)
            ls.append(value)

        return self.operator(ls)

    def build_cooldowns(self) -> None:
        for tgr in self.data:
            if tgr["type"] == "cd_x_user_messages_in_y_seconds":
                self.cd_x_user_messages_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_user_messages_in_y_seconds"]["messages"],
                    tgr["cd_x_user_messages_in_y_seconds"]["within"],
                    commands.BucketType.member,
                )
            if tgr["type"] == "cd_x_channel_messages_in_y_seconds":
                self.cd_x_channel_messages_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_channel_messages_in_y_seconds"]["messages"],
                    tgr["cd_x_channel_messages_in_y_seconds"]["within"],
                    commands.BucketType.channel,
                )

            if tgr["type"] == "cd_user_x_mentions_in_y_seconds":
                self.cd_user_x_mentions_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_user_x_mentions_in_y_seconds"]["mentions"],
                    tgr["cd_user_x_mentions_in_y_seconds"]["within"],
                    commands.BucketType.member,
                )
            if tgr["type"] == "cd_channel_x_mentions_in_y_seconds":
                self.cd_channel_x_mentions_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_channel_x_mentions_in_y_seconds"]["mentions"],
                    tgr["cd_channel_x_mentions_in_y_seconds"]["within"],
                    commands.BucketType.channel,
                )

            if tgr["type"] == "cd_x_user_attachments_in_y_seconds":
                self.cd_x_user_attachments_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_user_attachments_in_y_seconds"]["attachments"],
                    tgr["cd_x_user_attachments_in_y_seconds"]["within"],
                    commands.BucketType.member,
                )
            if tgr["type"] == "cd_x_channel_attachments_in_y_seconds":
                self.cd_x_channel_attachments_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_channel_attachments_in_y_seconds"]["attachments"],
                    tgr["cd_x_channel_attachments_in_y_seconds"]["within"],
                    commands.BucketType.channel,
                )

            if tgr["type"] == "cd_x_user_links_in_y_seconds":
                self.cd_x_user_links_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_user_links_in_y_seconds"]["links"],
                    tgr["cd_x_user_links_in_y_seconds"]["within"],
                    commands.BucketType.member,
                )
            if tgr["type"] == "cd_x_channel_links_in_y_seconds":
                self.cd_x_channel_links_in_y_seconds = commands.CooldownMapping.from_cooldown(
                    tgr["cd_x_channel_links_in_y_seconds"]["links"],
                    tgr["cd_x_channel_links_in_y_seconds"]["within"],
                    commands.BucketType.channel,
                )

    def x_user_messages_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_user_messages_in_y_seconds:
            bucket = self.cd_x_user_messages_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def x_channel_messages_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_channel_messages_in_y_seconds:
            bucket = self.cd_x_channel_messages_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def user_x_mentions_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_user_x_mentions_in_y_seconds and message.raw_mentions:
            bucket = self.cd_user_x_mentions_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def channel_x_mentions_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_channel_x_mentions_in_y_seconds and message.raw_mentions:
            bucket = self.cd_channel_x_mentions_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def x_user_attachments_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_user_attachments_in_y_seconds and message.attachments:
            bucket = self.cd_x_user_attachments_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def x_channel_attachments_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_channel_attachments_in_y_seconds and message.attachments:
            bucket = self.cd_x_channel_attachments_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def x_user_links_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_user_links_in_y_seconds and bool(LINKS_RE.search(message.content)):
            bucket = self.cd_x_user_links_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def x_channel_links_in_y_seconds(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False
        if self.cd_x_channel_links_in_y_seconds and bool(LINKS_RE.search(message.content)):
            bucket = self.cd_x_channel_links_in_y_seconds.get_bucket(message)
            return bool(bucket.update_rate_limit()) if bucket else False
        return False

    def all_caps(
        self, *, message: Message | None = None, threshold: float = float("inf"), percentage: float = 100, **kw
    ) -> bool:
        if not message:
            return False
        content = message.content

        count = sum(bool(ch.isupper()) for ch in content)
        if threshold and not percentage:
            return count >= threshold

        if percentage and not threshold:
            return count / len(content) >= percentage

        return False if count < threshold else count / len(content) >= percentage

    def message_mentions(self, *, message: Message | None = None, threshold: int = 0, **kw) -> bool:
        return len(message.raw_mentions) >= threshold if message else False

    def any_link(self, *, message: Message | None = None, **kw) -> bool:
        return bool(LINKS_RE.search(message.content)) if message else False

    def word_blacklist(self, *, message: Message | None, words: list[str] = None, **kw) -> bool:
        if words is None:
            words = []
        return any(word in message.content for word in words) if message else False

    def word_whitelist(self, *, message: Message | None = None, words: list[str] = None, **kw) -> bool:
        if words is None:
            words = []
        return all(word not in message.content for word in words) if message else False

    def server_invites(self, *, message: Message | None = None, **kw) -> bool:
        return bool(INVITE_RE.search(message.content)) if message else False

    def message_match_regex(self, *, message: Message | None = None, regex: str, **kw) -> bool:
        return bool(re.search(regex, message.content)) if message else False

    def message_not_match_regex(self, *, message: Message, regex: str, **kw) -> bool:
        return not bool(re.search(regex, message.content))

    def nickname_match_regex(self, *, member: Member, regex: str, **kw) -> bool:
        return bool(re.search(regex, member.display_name))

    def nickname_not_match_regex(self, *, member: Member, regex: str, **kw) -> bool:
        return not bool(re.search(regex, member.display_name))

    def nickname_word_blacklist(self, *, member: Member, words: list[str], **kw) -> bool:
        return any(word in member.display_name for word in words)

    def nickname_word_whitelist(self, *, member: Member, words: list[str], **kw) -> bool:
        return all(word not in member.display_name for word in words)

    def join_username_match_regex(self, *, member: Member, regex: str, **kw) -> bool:
        return bool(re.search(regex, member.display_name)) or bool(re.search(regex, member.name))

    def join_username_not_match_regex(self, *, member: Member, regex: str, **kw) -> bool:
        return not (bool(re.search(regex, member.display_name)) or bool(re.search(regex, member.name)))

    def join_username_word_blacklist(self, *, member: Member, words: list[str], **kw) -> bool:
        return any(word in member.display_name for word in words) or any(word in member.name for word in words)

    def join_username_word_whitelist(self, *, member: Member, words: list[str], **kw) -> bool:
        return all(word not in member.display_name for word in words) and all(word not in member.name for word in words)

    def join_username_invite(self, *, member: Member, **kw) -> bool:
        return bool(INVITE_RE.search(member.display_name)) or bool(INVITE_RE.search(member.name))

    def message_without_attachments(self, *, message: Message | None = None, **kw) -> bool:
        return not message.attachments if message else False

    def message_with_attachments(self, *, message: Message | None = None, **kw) -> bool:
        return bool(message.attachments) if message else False

    def message_with_more_than_x_characters(self, *, message: Message | None = None, characters: int, **kw) -> bool:
        return len(message.content) > characters if message else False

    def message_with_less_than_x_characters(self, *, message: Message | None = None, characters: int, **kw) -> bool:
        return len(message.content) < characters if message else False

    async def scam_links(self, *, message: Message | None = None, **kw) -> bool:
        if not message:
            return False

        cog: OnMsg = self.bot.OnMsg
        if not cog:
            return False
        has_scam_link = await cog._scam_detection(message, to_send=False)
        return bool(has_scam_link)
