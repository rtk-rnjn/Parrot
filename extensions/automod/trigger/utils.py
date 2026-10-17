from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from enum import StrEnum
from urllib.parse import urlsplit

import discord

from core.constants import LINKS_RE

from .enum import TriggerType as T

TRAILING = ".,;:!?)]}'\"|*_~"

MARKUP = re.compile(r"```.*?```|`[^`\n]*`|<[^<>\s]*>", re.DOTALL)
USER_MENTION = re.compile(r"<@!?(\d+)>")
WORD = re.compile(r"[^\W_]+")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def words_of(text: str) -> list[str]:
    return WORD.findall(normalize(text))


def link_hosts(text: str) -> list[str]:
    hosts: list[str] = []
    for match in LINKS_RE.finditer(text):
        url = match.group().rstrip(TRAILING)
        if not url.lower().startswith("http"):
            url = "http://" + url
        try:
            host = urlsplit(url).hostname
        except ValueError:
            continue
        if host:
            hosts.append(host.rstrip(".").lower())
    return hosts


def covered(host: str, domains: Sequence[str]) -> bool:
    labels = host.split(".")
    return any(".".join(labels[index:]) in domains for index in range(len(labels) - 1))


def mentioned_ids(message: discord.Message) -> set[int]:
    return {int(found) for found in USER_MENTION.findall(message.content)} - {message.author.id}


def count_letters(text: str) -> tuple[int, int]:
    cleaned = LINKS_RE.sub(" ", MARKUP.sub(" ", text))
    upper = lower = 0
    for char in cleaned:
        if char.isupper():
            upper += 1
        elif char.islower():
            lower += 1
    return upper, upper + lower


class Scope(StrEnum):
    USER = "user"
    CHANNEL = "channel"


class Metric(StrEnum):
    MESSAGES = "messages"
    LINKS = "links"
    ATTACHMENTS = "attachments"
    MENTIONS = "mentions"


RATE_LIMITS: dict[T, tuple[Scope, Metric]] = {
    T.X_USER_MESSAGE_IN_Y_MINUTES: (Scope.USER, Metric.MESSAGES),
    T.X_USER_LINKS_IN_Y_MINUTES: (Scope.USER, Metric.LINKS),
    T.X_USER_ATTACHMENTS_IN_Y_MINUTES: (Scope.USER, Metric.ATTACHMENTS),
    T.X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES: (Scope.USER, Metric.MENTIONS),
    T.X_CHANNEL_MESSAGE_IN_Y_MINUTES: (Scope.CHANNEL, Metric.MESSAGES),
    T.X_CHANNEL_LINKS_IN_Y_MINUTES: (Scope.CHANNEL, Metric.LINKS),
    T.X_CHANNEL_ATTACHMENTS_IN_Y_MINUTES: (Scope.CHANNEL, Metric.ATTACHMENTS),
    T.X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES: (Scope.CHANNEL, Metric.MENTIONS),
}
