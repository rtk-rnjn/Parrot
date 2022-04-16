from __future__ import annotations

from core import Parrot, Context, Cog
import discord
from discord.ext import commands


class Actions(Cog):
    """Action commands like hug and kiss"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://api.waifu.pics/sfw"

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            name="Lights_Camera_Action__Emoticon__", id=892434144364220497
        )

    async def send_message(self, ctx: Context, *, url: str=None) -> None:
        response = await self.bot.http_session.get(url or f"{self.url}/{ctx.command.name}")
        if response.status != 200:
            return
        data = await response.json()
        embed = discord.Embed(
            title=f"{ctx.command.name.title()}", color=self.bot.color, timestamp=ctx.message.created_at,
        )
        embed.set_image(url=data["url"])
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def waifu(self, ctx: Context,):
        """Waifu pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def shinobu(self, ctx: Context,):
        """Shinobu pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def megumin(self, ctx: Context,):
        """Megumin pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bully(self, ctx: Context,):
        """Bully pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def cuddle(self, ctx: Context,):
        """Cuddle pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def weep(self, ctx: Context,):
        """Cry pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def hug(self, ctx: Context,):
        """Hug pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def awoo(self, ctx: Context,):
        """Awoo pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def kiss(self, ctx: Context,):
        """Kiss pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def lick(self, ctx: Context,):
        """Lick pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def pat(self, ctx: Context,):
        """Pat pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def smug(self, ctx: Context,):
        """Smug pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bonk(self, ctx: Context,):
        """Bonk pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def yeet(self, ctx: Context,):
        """Yeet pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def blush(
        self,
        ctx: Context,
    ):
        """Blush pics?"""
        await self.send_message(ctx)

    @commands.command(aliases=["grin"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def smile(
        self,
        ctx: Context,
    ):
        """Smile pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def wave(self, ctx: Context,):
        """Wave pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def highfive(self, ctx: Context,):
        """Highfive pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def handhold(self, ctx: Context,):
        """Handhold pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def nom(self, ctx: Context,):
        """Nom pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bite(self, ctx: Context,):
        """Bite pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def glomp(self, ctx: Context,):
        """Glomp pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def slap(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: commands.clean_content = None,
    ):
        """Slap pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def kill(self, ctx: Context,):
        """Kill pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def hit(self, ctx: Context,):
        """Kick pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def happy(self, ctx: Context,):
        """Happy pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def wink(self, ctx: Context,):
        """Wink pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def poke(self, ctx: Context,):
        """Poke pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def dance(self, ctx: Context):
        """Dance pics?"""
        await self.send_message(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def cringe(self, ctx: Context,):
        """Cringe pics?"""
        await self.send_message(ctx)
