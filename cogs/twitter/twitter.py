from __future__ import annotations

from core import Parrot, Cog, Context
from typing import Any, Optional, Union

import discord
from discord.ext import commands

import os
import tweepy
from utilities.converters import ToAsync


@ToAsync()
def func(obj: Any, *args: Any, **kwargs: Any) -> Any:
    return obj(*args, **kwargs)


class Twitter(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        
        self.auth = tweepy.OAuthHandler(
            os.environ['API_KEY'], os.environ['API_KEY_SECRET']
        )
        self.auth.set_access_token(
            os.environ['ACCESS_TOKEN'], os.environ['ACCESS_TOKEN_SECRET']
        )
        self.api = tweepy.API(self.auth)
        if not hasattr(bot, "twitter"):
            bot.twitter = self.api
