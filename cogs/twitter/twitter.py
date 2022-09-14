from __future__ import annotations

import os

import tweepy  # type: ignore

from core import Cog, Context, Parrot


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
            bearer_token=os.environ["BEARER"],
            consumer_key=os.environ["API_KEY"],
            consumer_secret=os.environ["API_KEY_SECRET"],
            access_token=os.environ["ACCESS_TOKEN"],
            access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
        )
        self.async_client = tweepy.asynchronous.AsyncClient(
            bearer_token=os.environ["BEARER"],
            consumer_key=os.environ["API_KEY"],
            consumer_secret=os.environ["API_KEY_SECRET"],
            access_token=os.environ["ACCESS_TOKEN"],
            access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
        )

    async def cog_check(self, ctx: Context):
        return ctx.author.id in ctx.bot.owner_ids

