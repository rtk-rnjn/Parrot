from __future__ import annotations

from core import Parrot, Cog

import discord
from discord.ext import commands

import os
import tweepy


class Twitter(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self.auth = tweepy.OAuthHandler(
            os.environ["API_KEY"], os.environ["API_KEY_SECRET"]
        )
        self.auth.set_access_token(
            os.environ["ACCESS_TOKEN"], os.environ["ACCESS_TOKEN_SECRET"]
        )
        self.api = tweepy.API(self.auth)
        if not hasattr(bot, "twitter"):
            bot.twitter = self.api
        self.client = tweepy.Client(
            os.environ["BEARER"]
        )
        self.async_client = tweepy.asynchronous.AsyncClient(
            os.environ["BEARER"]
        )