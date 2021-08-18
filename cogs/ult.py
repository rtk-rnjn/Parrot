from typing import Optional
from discord.ext import commands
from time import time 
import discord
from datetime import datetime, timedelta 
from psutil import Process, virtual_memory
from discord import __version__ as discord_version
from platform import python_version

from core import Parrot, Context, Cog
from utilities.config import VERSION

class ult(Cog, name="utilities", description="Basic commands for the bots."):
  '''Basic commands for the bots.'''
  def __init__(self, bot: Parrot):
    self.bot = bot

  @commands.command(name="ping")
  @commands.cooldown(1, 5, commands.BucketType.member)
  async def ping(self, ctx: Context):
    '''
    Get the latency of bot.
    '''
    start = time()
    message = await ctx.reply(f"Pong! latency: {self.bot.latency*1000:,.0f} ms.")
    end = time()
    await message.edit(content=f"Pong! latency: {self.bot.latency*1000:,.0f} ms. Response time: {(end-start)*1000:,.0f} ms.")


  @commands.command(aliases=['av'])
  @commands.cooldown(1, 5, commands.BucketType.member)
  @commands.bot_has_permissions(embed_links=True)
  async def avatar(self, ctx: Context, *, member: discord.Member= None):
      '''
      Get the avatar of the user. Make sure you don't misuse.
      '''
      if member is None:
          member = ctx.author
      embed = discord.Embed(timestamp=datetime.utcnow())
      embed.add_field(name=member.name,value=f'[Download]({member.avatar.url})')
      embed.set_image(url=member.avatar.url)
      embed.set_footer(text=f'Requested by {ctx.author.name}', icon_url= ctx.author.avatar.url)
      await ctx.reply(embed=embed)


  @commands.command(name="owner")
  @commands.cooldown(1, 5, commands.BucketType.member)
  @commands.bot_has_permissions(embed_links=True)
  async def owner(self, ctx: Context):
    '''
    Get the freaking bot owner name.
    '''
    await ctx.reply(embed=discord.Embed(title="Owner Info", description='This bot is being hosted by !! Ritik Ranjan [\*.\*]#9230. He is actually a dumb bot developer. He do not know why he made this shit bot. But it\'s cool', timestamp=datetime.utcnow()))


  @commands.command(aliases=['guildavatar', 'serverlogo', 'servericon'])
  @commands.bot_has_permissions(embed_links=True)
  @commands.cooldown(1, 5, commands.BucketType.member)
  async def guildicon(self, ctx: Context, server:int=None):
      '''
      Get the freaking server icon
      '''
      guild = self.bot.get_guild(server) or ctx.guild
      embed = discord.Embed(timestamp=datetime.utcnow())
      embed.set_image(url = guild.icon.url)
      embed.set_footer(text=f"{ctx.author.name}")
      await ctx.reply(embed=embed)


  @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
  @commands.bot_has_permissions(embed_links=True)
  @commands.cooldown(1, 5, commands.BucketType.member)
  async def server_info(self, ctx: Context):
    '''
    Get the basic stats about the server
    '''
    embed = discord.Embed(title="Server information",
            colour=ctx.guild.owner.colour,
            timestamp=datetime.utcnow())

    embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text=f'ID: {ctx.guild.id}')
    statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
          len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
          len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
          len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

    fields = [("Owner", ctx.guild.owner, True),
          ("Region", str(ctx.guild.region).capitalize(), True),
          ("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
          ("Total Members", f'Members: {len(ctx.guild.members)}\nHumans: {len(list(filter(lambda m: not m.bot, ctx.guild.members)))}\nBots: {len(list(filter(lambda m: m.bot, ctx.guild.members)))} ', True),
          ("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
          ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
          ("Statuses", f":green_circle: {statuses[0]} :yellow_circle:  {statuses[1]} :red_circle: {statuses[2]} :black_circle: {statuses[3]}", True),
          ("Total channels", f'Categories:{len(ctx.guild.categories)}\nText: {len(ctx.guild.text_channels)}\nVoice:{len(ctx.guild.voice_channels)}', True),
          #("Banned members", len(await ctx.guild.bans()), True),
          ("Roles", len(ctx.guild.roles), True),
          #("Invites", len(await ctx.guild.invites()), True),
          ]

    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)
    try: embed.add_field(name="Banned Members", value=f"{len(await ctx.guild.bans())}", inline=True)
    except: pass
    await ctx.reply(embed=embed)


  @commands.command(name="stats")
  @commands.cooldown(1, 5, commands.BucketType.member)
  @commands.bot_has_permissions(embed_links=True)
  async def show_bot_stats(self, ctx: Context):
    '''
    Get the bot stats
    '''
    embed = discord.Embed(title="Bot stats",
            colour=ctx.author.colour,
            timestamp=datetime.utcnow())
    embed.set_thumbnail(url=f'{ctx.guild.me.avatar.url}')
    proc = Process()
    with proc.oneshot():
      uptime = timedelta(seconds=time()-proc.create_time())
      cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
      mem_total = virtual_memory().total / (1024**2)
      mem_of_total = proc.memory_percent()
      mem_usage = mem_total * (mem_of_total / 100)
    
    x = len(self.bot.users)
    y = len(self.bot.guilds)
    fields = [
        ("Bot version", f"`{VERSION}`", True),
        ("Python version", "`"+str(python_version())+"`", True),
        ("discord.py version", "`"+str(discord_version)+"`", True),
        ("Uptime", "`"+str(uptime)+"`", True),
        ("CPU time", "`"+str(cpu_time)+"`", True),
        ("Memory usage", f"`{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)`", True),
        ("Total users on count", "`"+str(x)+"`", True),
        ("Owner",'`!! Ritik Ranjan [*.*]#9230`', True),
        ("Total guild on count", "`"+str(y)+"`", True)]
    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)
    await ctx.reply(embed=embed)


  @commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
  @commands.bot_has_permissions(embed_links=True)
  @commands.cooldown(1, 5, commands.BucketType.member)
  async def user_info(self, ctx: Context, *, member:discord.Member=None):
    '''
    Get the basic stats about the user
    '''
    target = member or ctx.author
    roles = [role for role in target.roles]
    embed = discord.Embed(title="User information",
            colour=target.colour,
            timestamp=datetime.utcnow())

    embed.set_thumbnail(url=target.avatar.url)
    embed.set_footer(text=f"{target.id}")
    fields = [("Name", str(target), True),
          #("ID", target.id, True),
          ("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
          ("Status", str(target.status).title(), True),
          ("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
          ("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
          ("Boosted", bool(target.premium_since), True),
          ("Bot?", target.bot, True),
          (f"Roles ({len(roles)})", " ".join([role.mention for role in roles]), False)]
          
    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)

    await ctx.reply(embed=embed)


  @commands.command()
  @commands.cooldown(1, 5, commands.BucketType.member)
  @commands.bot_has_permissions(embed_links=True)
  async def invite(self, ctx: Context):
    """
    Get the invite of the bot! Thanks for seeing this command
    """
    em = discord.Embed(title="Click here to add", description="```ini\n[Default Prefix: `$` and `@Parrot#9209`]\n```", url="https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=8&redirect_uri=https%3A%2F%2Fdiscord.gg%2FNEyJxM7G7f&scope=bot%20applications.commands", timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}#{ctx.author.discriminator}")
    em.set_thumbnail(url=ctx.guild.me.avatar.url)
    await ctx.reply(embed=em)

def setup(bot):
  bot.add_cog(ult(bot))
