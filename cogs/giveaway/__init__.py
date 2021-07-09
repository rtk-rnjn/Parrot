from discord.ext import commands
import discord, asyncio

from datetime import datetime, timedelta

from core import Cog, Parrot, Context
from utilities.checks import can_giveaway
from utilities.converters import convert_time

from cogs.giveaway import method as mt

from utilities import exceptions as ex


class Giveaway(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(embed_links=True,
                                  manage_messages=True,
                                  add_reactions=True)
    @commands.check_any(can_giveaway(),
                        commands.has_permissions(manage_guild=True))
    @commands.max_concurrency(1, commands.cooldowns.BucketType.guild)
    async def gcreate(self, ctx: Context):
        """
				To create a Giveaway in the server
				"""
        ques = [
            ('How long do you want the giveaway to last?', 1),
            ('In which channel do you want to host this giveaway?', 2),
            ('What is the prize for this giveaway?', 3),
            ('How many winners do you want me to pick?', 4),
            ('How many messages do users need to join the giveaway?', 5),
            ('Which role is required to participate in the giveaway?', 6),
            #	('Which server is required to participate in the giveaway?', 7)
        ]

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        for q, i in ques:
            embed = discord.Embed(title="Giveaway Create",
                                  description=f"{i}. {q}",
                                  timestamp=datetime.utcnow())
            embed.set_footer(text='Type `Cancel` to cancel')
            await ctx.send(embed=embed)
            try:
                msg = await self.bot.wait_for('message', timeout=60, check=check)
            except Exception:
                return await ctx.send(
                    f"{ctx.author.mention} you ran out time. Try again")
            
            if msg.content.lower() == 'cancel':
                raise ex.GiveawayError(f"{ctx.author.mention} canceling...")
            if i == 1:
                t = convert_time(msg.content)
            if i == 2:
                channel = await commands.TextChannelConverter().convert(
                    ctx, msg.content)
            if i == 3:
                prize = msg.clean_content
            if i == 4:
                try:
                    winner = int(msg.clean_content)
                except ValueError:
                    raise ex.GiveawayError(
                        'Invalid Winner Count. Make sure you use whole number, like 1, 10, 05'
                    )
            if i == 5:
                if msg.content.lower() != 'none':
                    try:
                        msg_count = int(msg.clean_content)
                    except ValueError:
                        raise ex.GiveawayError(
                            'Invalid Message Count. Make sure you use whole number, like 1, 10, 05'
                        )
                else:
                    msg_count = None
            if i == 6:
                if msg.content.lower() != 'none':
                    role = await commands.RoleConverter().convert(
                        ctx, msg.content)
                else:
                    role = None
        #	if i == 7:
        #		if msg.content.lower() != 'none':
        #			guild = await commands.GuildConverter().convert(ctx, msg.content)

        embed = discord.Embed(title=f'Giveaway :tada: | Prize: {prize}',
                              description=f"**React to :tada: to win.**",
                              timestamp=datetime.utcnow() +
                              timedelta(seconds=t))
        embed.set_footer(text=f"{ctx.guild.name} | Ends at")
        if role:
            embed.add_field(name="Required Role",
                            value=f"{role.mention}",
                            inline=False)
        if msg_count:
            embed.add_field(name="Required Message Count",
                            value=f"{msg_count}",
                            inline=False)
        perms = channel.permissions_for(ctx.me)
        if not all((perms.add_reactions, perms.manage_messages,
                    perms.send_messages, perms.embed_links)):
            raise commands.BotMissingPermissions([
                'add_reactions', 'manage_messages', 'send_messages',
                'embed_links'
            ])

        msg = await channel.send(embed=embed)
        await mt.create_giveaway(msg.id, channel.id, winner,
                                 role.id if role else None,
                                 msg_count if msg_count else None,
                                 datetime.utcnow() + timedelta(seconds=t))
        await msg.add_reaction(":tada:")


def setup(bot):
    bot.add_cog(Giveaway(bot))
