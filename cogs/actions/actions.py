from __future__ import annotations

from core import Parrot, Context, Cog
import discord
from discord.ext import commands
from ._actions import ENDPOINTS


class Actions(Cog):
    """Action commands like hug and kiss"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://api.waifu.pics/sfw"
        self.command_loader()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            name="Lights_Camera_Action__Emoticon__", id=892434144364220497
        )

    async def send_message(self, ctx: Context, *, url: str = None) -> None:
        response = await self.bot.http_session.get(
            url or f"{self.url}/{ctx.command.name}"
        )
        if response.status != 200:
            return
        data = await response.json()
        embed = discord.Embed(
            title=f"{ctx.command.name.title()}",
            color=self.bot.color,
            timestamp=ctx.message.created_at,
        )
        embed.set_image(url=data["url"])
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

        await ctx.reply(embed=embed)

    async def command_loader(self):
        method = self.send_message
        for end_point in ENDPOINTS:

            @commands.command(name=end_point)
            @commands.bot_has_permissions(embed_links=True)
            @commands.cooldown(1, 5, commands.BucketType.member)
            @commands.max_concurrency(1, per=commands.BucketType.user)
            @Context.with_type
            async def callback(
                ctx: Context,
            ):
                await method(ctx)

            self.bot.add_command(callback)
