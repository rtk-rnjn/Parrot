from __future__ import annotations
from datetime import datetime
from typing import Collection, Optional

from core import Parrot, Cog, Context

from discord.ext import commands, tasks
import discord, asyncio

from utilities.database import parrot_db
from utilities import time
from utilities.paginator import PaginationView

from typing import Optional, Union
from datetime import datetime

class Timer(Cog):
    """For timers and reminders"""
    
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['timers']
        self.reminder_task.start()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{ALARM CLOCK}')
    
    async def create_timer(self, 
                           channel: Union[discord.TextChannel, discord.Thread], 
                           message: discord.Message, 
                           member: discord.Member, 
                           age: int, 
                           *, 
                           remark: str=None,
                           dm: bool=False
                        ):
        collection = self.collection
        post = {
            '_id': message.id,
            'channel': channel.id,
            'age': age,
            'author': member.id,
            'remark': remark,
            'dm': dm
        }
        await collection.insert_one(post)
    
    async def delete_timer(self, member: discord.Member, message_id: int):
        collection = self.reminder_db[f'{member.id}']
        await collection.delete_one({'_id': message_id})
    
    async def get_all_timers(self, member: discord.User) -> list[discord.Embed]:
        collection = self.collection
        records = []
        async for data in collection.find({'author': member.id}):
            embed = discord.Embed(
                title='Timers', 
                timestamp=datetime.utcnow(), 
                color=member.color
            ).set_footer(
                text=f'{member}'
            )
            embed.description = f"```\n{data['remark'] if data['remark'] else 'No description was given'}```\n\nMessage ID:` **{data['_id']}**\n`Channel ID:` **{data['channel']}**\n`Age:` {time.format_dt_with_int(data['age'])}"
            records.append(embed)
        return records
    
    @commands.command()
    async def remindme(self, ctx: Context, age: time.ShortTime, *, task: commands.clean_content):
        """To make reminders as to get your tasks done on time"""
        seconds = age.dt.timestamp()
        await ctx.reply(f"{ctx.author.mention} alright, you will be mentioned here within **{seconds}** or **{age}**. To delete your reminder consider typing ```\n{ctx.clean_prefix}delremind {ctx.message.id}```")
        if seconds < 60:
            await asyncio.sleep(seconds)
            await ctx.send(f"{ctx.author.mention} reminder for **{age}** is over. Remark: **{task}**")
        else:
            await self.create_timer(ctx.channel, ctx.message, ctx.author, seconds, remark=task, dm=False)
        
    @commands.command()
    async def reminders(self, ctx: Context):
        """To get all your reminders"""
        em_list = await self.get_all_timers(ctx.author)
        await PaginationView(em_list).start()
    
    @commands.command()
    async def delremind(self, ctx: Context, message: int):
        """To delete the reminder"""
        await self.delete_timer(ctx.author, message)
        await ctx.reply(f"{ctx.author.mention} deleted reminder of ID: **{message}**")
    
    @commands.command()
    async def remindmedm(self, ctx: Context, age: time.ShortTime, *, task: commands.clean_content):
        """Same as remindme, but you will be mentioned in DM. Make sure you have DM open for the bot"""
        seconds = age.dt.timestamp()
        await ctx.reply(f"{ctx.author.mention} alright, you will be mentioned in your DM (Make sure you have your DM open for this bot) within **{seconds}** or **{age}**. To delete your reminder consider typing ```\n{ctx.clean_prefix}delremind {ctx.message.id}```")
        if seconds < 60:
            await asyncio.sleep(seconds)
            await ctx.author.send(f"{ctx.author.mention} reminder for **{age}** is over. Remark: **{task}**")
        else:
            await self.create_timer(ctx.channel, ctx.message, ctx.author, seconds, remark=task, dm=True)
    
    @tasks.loop(seconds=1.0)
    async def reminder_task(self):
        async for data in self.collection.find({'age': {'$lte': datetime.utcnow().timestamp()}}):
            channel = self.bot.get_channel(data['channel'])
            if not channel:
                await self.collection.delete_one({'_id': data['id']})
            else:
                if not data['dm']:
                    await channel.send(f"<@{data['author']}> reminder for: {data['remark']}")
                else:
                    member = channel.guild.get_member(data['author'])
                    if not member:
                        await self.collection.delete_one({'_id': data['id']})
                    else:
                        await member.send(f"<@{data['author']}> reminder for: {data['remark']}")
            await self.collection.delete_one({'_id': data['id']})