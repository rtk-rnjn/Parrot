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

class utilities(Cog):
    """Basic commands for the bots."""
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.command(name="ping")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def ping(self, ctx: Context):
        """
        Get the latency of bot.
        """
        start = time()
        message = await ctx.reply(f"Pinging...")
        db = await self.bot.db_latency
        end = time()
        await message.edit(content=f"Pong! latency: {self.bot.latency*1000:,.0f} ms. Response time: {(end-start)*1000:,.0f} ms. Database: {db*1000:,.0f} ms.")

    @commands.command(aliases=['av'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def avatar(self, ctx: Context, *, member: discord.Member= None):
        """
        Get the avatar of the user. Make sure you don't misuse.
        """
        member = member or ctx.author
        embed = discord.Embed(timestamp=datetime.utcnow())
        embed.add_field(name=member.name,value=f'[Download]({member.display_avatar.url})')
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f'Requested by {ctx.author.name}', icon_url= ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)


    @commands.command(name="owner")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def owner(self, ctx: Context):
        """
        Get the freaking bot owner name.
        """
        await ctx.reply(
            embed=discord.Embed(
                title="Owner Info", 
                description='This bot is being hosted by !! Ritik Ranjan [\*.\*]#9230. He is actually a dumb bot developer. He do not know why he made this shit bot. But it\'s cool', 
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
                url="https://discord.com/users/741614468546560092")
            )


    @commands.command(aliases=['guildavatar', 'serverlogo', 'servericon'])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def guildicon(self, ctx: Context, *, server: discord.Guild=None):
        """
        Get the freaking server icon
        """
        guild = server or ctx.guild
        embed = discord.Embed(timestamp=datetime.utcnow())
        embed.set_image(url = guild.icon.url)
        embed.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=embed)


    @commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def server_info(self, ctx: Context):
        """
        Get the basic stats about the server
        """
        embed = discord.Embed(title=f"Server Info: {ctx.guild.name}",
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
              ("Created at", f"<t:{int(ctx.guild.created_at.timestamp())}>", True),
              ("Total Members", f'Members: {len(ctx.guild.members)}\nHumans: {len(list(filter(lambda m: not m.bot, ctx.guild.members)))}\nBots: {len(list(filter(lambda m: m.bot, ctx.guild.members)))} ', True),
              ("Total channels", f'Categories: {len(ctx.guild.categories)}\nText: {len(ctx.guild.text_channels)}\nVoice:{len(ctx.guild.voice_channels)}', True),
              ("General", f"Roles: {len(ctx.guild.roles)}\n Emojis: {len(ctx.guild.emojis)}\n Boost Level: {ctx.guild.premium_tier}", True),
              ("Statuses", f":green_circle: {statuses[0]} :yellow_circle:  {statuses[1]} :red_circle: {statuses[2]} :black_circle: {statuses[3]}", True),
              ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        if ctx.guild.me.guild_permissions.ban_members:
            embed.add_field(name="Banned Members", value=f"{len(await ctx.guild.bans())}", inline=True)
        if ctx.guild.me.guild_permissions.manage_guild:
            embed.add_field(name="Invites", value=f"{len(await ctx.guild.invites())}", inline=True)
        await ctx.reply(embed=embed)


    @commands.command(name="stats")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def show_bot_stats(self, ctx: Context):
        """
        Get the bot stats
        """
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
        
        fields = [
            ("Bot version", f"`{VERSION}`", True),
            ("Python version", "`"+str(python_version())+"`", True),
            ("discord.py version", "`"+str(discord_version)+"`", True),
            ("Uptime", "`"+str(uptime)+"`", True),
            ("CPU time", "`"+str(cpu_time)+"`", True),
            ("Memory usage", f"`{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)`", True),
            ("Total users on count", f"`{len(self.bot.users)}`", True),
            ("Owner",'`!! Ritik Ranjan [*.*]#9230`', True),
            ("Total guild on count", f"`{len(self.bot.guilds)}`", True)]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        await ctx.reply(embed=embed)


    @commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def user_info(self, ctx: Context, *, member:discord.Member=None):
        """
        Get the basic stats about the user
        """
        target = member or ctx.author
        roles = [role for role in target.roles]
        embed = discord.Embed(title="User information",
                colour=target.colour,
                timestamp=datetime.utcnow())

        embed.set_thumbnail(url=target.avatar.url)
        embed.set_footer(text=f"ID: {target.id}")
        fields = [("Name", str(target), True),
              ("Created at", f"<t:{int(target.created_at.timestamp())}>", True),
              ("Status", str(target.status).title(), True),
              ("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
              ("Joined at", f"<t:{int(target.joined_at.timestamp())}>", True),
              ("Boosted", bool(target.premium_since), True),
              ("Bot?", target.bot, True),
              ("Nickname", target.display_name, True),
              (f"Top Role [{len(roles)}]", target.top_role.mention, True)]
        perms = []  
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        if target.guild_permissions.administrator:
            perms.append("Administrator")
        if target.guild_permissions.kick_members and target.guild_permissions.ban_members and target.guild_permissions.manage_messages:
            perms.append("Server Moderator")
        if target.guild_permissions.manage_guild:
            perms.append("Server Manager")
        if target.guild_permissions.manage_roles:
            perms.append("Role Manager")
        embed.description = f"Key perms: {', '.join(perms if perms else ['NA'])}"
        await ctx.reply(embed=embed)


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def invite(self, ctx: Context):
        """
        Get the invite of the bot! Thanks for seeing this command
        """
        em = discord.Embed(title="Click here to add", 
                           description="```ini\n[Default Prefix: `$` and `@Parrot#9209`]\n```\n**Bot Owned and created by `!! Ritik Ranjan [*.*]#9230`**", 
                           url=f"https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=8&redirect_uri=https%3A%2F%2Fdiscord.gg%2FNEyJxM7G7f&scope=bot%20applications.commands", 
                           timestamp=datetime.utcnow())
        em.set_footer(text=f"{ctx.author}")
        em.set_thumbnail(url=ctx.guild.me.avatar.url)
        await ctx.reply(embed=em)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def roleinfo(self, ctx: Context, *, role: discord.Role):
        """To get the info regarding the server role"""
        embed = discord.Embed(title=f"Role Information: {role.name}", description=f"ID: `{role.id}`", color=role.color, timestamp=datetime.utcnow())
        data = [("Created At", f"<t:{int(role.created_at.timestamp())}>", True),
                ("Is Hoisted?", role.hoist, True),
                ("Position", role.position, True),
                ("Managed", role.managed, True),
                ("Mentionalble?", role.mentionable, True),
                ("Members", len(role.members), True),
                ("Mention", role.mention, True),
                ("Is Boost role?", role.is_premium_subscriber(), True),
                ("Is Bot role?", role.is_bot_managed(), True)
               ]
        for name, value, inline in data:
            embed.add_field(name=name, value=value, inline=inline)
        perms=[]
        if role.permissions.administrator:
            perms.append("Administrator")
        if role.permissions.kick_members and role.permissions.ban_members and role.permissions.manage_messages:
            perms.append("Server Moderator")
        if role.permissions.manage_guild:
            perms.append("Server Manager")
        if role.permissions.manage_roles:
            perms.append("Role Manager")
        embed.description = f"Key perms: {', '.join(perms if perms else ['NA'])}"
        embed.set_footer(text=f"ID: {role.id}")
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def emojiinfo(self, ctx: Context, *, emoji: discord.Emoji):
        """To get the info regarding the server emoji"""
        em = discord.Embed(title="Emoji Info", description=f"• [Download the emoji]({emoji.url})\n• Emoji ID: `{emoji.id}`" ,timestamp=datetime.utcnow(), color=ctx.author.color)
        data = [("Name", emoji.name, True),
                ("Is Animated?", emoji.animated, True),
                ("Created At", f"<t:{int(emoji.created_at.timestamp())}>", True),
                ("Server Owned", emoji.guild.name, True),
                ("Server ID", emoji.guild_id, True),
                ("Created By", emoji.user if emoji.user else 'User Not Found', True),
                ("Available?", emoji.available, True),
                ("Managed by Twitch?", emoji.managed, True),
                ("Require Colons?", emoji.require_colons, True)
                ]
        em.set_footer(text=f"{ctx.author}")
        em.set_thumbnail(url=emoji.url)
        for name, value, inline in data:
            em.add_field(name=name, value=f"{value}", inline=inline)
        await ctx.reply(embed=em)

    @commands.command(aliases=['suggest'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def request(self, ctx: Context, *, text: str):
        """To request directly from the owner"""
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        await ctx.reply(f"{ctx.author.mention} are you sure want to request for the same. Abuse of this feature may result in mute. Type `YES` to continue (case insensitive)")
        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)
        except Exception:
            return
        if msg.content == "YES":
            await self.bot.get_user(741614468546560092).send(f"`{ctx.author}` {text[:190:]}")


