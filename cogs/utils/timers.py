from __future__ import annotations
from datetime import datetime
from typing import Collection, Optional

from core import Parrot, Cog, Context

from discord.ext import commands, tasks
import discord, asyncio

from utilities.database import parrot_db
from utilities.time import ShortTime
from utilities.paginator import PaginationView

from typing import Optional, Union
from datetime import datetime
from time import time

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
        collection = self.collection
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
            embed.description = f"```\nTASK: {data['remark'] if data['remark'] else 'No description was given'}```\n`Message ID :` **{data['_id']}**\n`Channel ID :` **<#{data['channel']}>**\n`Reminder at:` <t:{int(data['age'])}>"
            records.append(embed)
        return records
    
    @commands.command()
    @Context.with_type
    async def remindme(self, ctx: Context, age: ShortTime, *, task: commands.clean_content):
        """To make reminders as to get your tasks done on time"""
        seconds = age.dt.timestamp()
        text = f"{ctx.author.mention} alright, you will be mentioned in {ctx.channel.mention} at **<t:{int(seconds)}>**. To delete your reminder consider typing ```\n{ctx.clean_prefix}delremind {ctx.message.id}```"
        try:
            await ctx.author.send(text)
        except Exception:
            await ctx.reply(text)
        await self.create_timer(ctx.channel, ctx.message, ctx.author, seconds, remark=task, dm=False)
        
    @commands.command()
    @Context.with_type
    async def reminders(self, ctx: Context):
        """To get all your reminders"""
        em_list = await self.get_all_timers(ctx.author)
        if not em_list:
            return await ctx.reply(f"{ctx.author.mention} you don't have any reminders")
        await PaginationView(em_list).start(ctx)
        
    @commands.command()
    @Context.with_type
    async def delremind(self, ctx: Context, message: int):
        """To delete the reminder"""
        await self.delete_timer(ctx.author, message)
        await ctx.reply(f"{ctx.author.mention} deleted reminder of ID: **{message}**")
    
    @commands.command()
    @Context.with_type
    async def remindmedm(self, ctx: Context, age: ShortTime, *, task: commands.clean_content):
        """Same as remindme, but you will be mentioned in DM. Make sure you have DM open for the bot"""
        seconds = age.dt.timestamp()
        text = f"{ctx.author.mention} alright, you will be mentioned in your DM (Make sure you have your DM open for this bot) within **<t:{int(seconds)}>**. To delete your reminder consider typing ```\n{ctx.clean_prefix}delremind {ctx.message.id}```"
        try:
            await ctx.author.send(text)
        except Exception:
            await ctx.reply(text)
        await self.create_timer(ctx.channel, ctx.message, ctx.author, seconds, remark=task, dm=True)
    
    @tasks.loop(seconds=1.0)
    async def reminder_task(self):
        async for data in self.collection.find({'age': {'$lte': datetime.utcnow().timestamp()}}):
            channel = self.bot.get_channel(data['channel'])
            if not channel:
                await self.collection.delete_one({'_id': data['_id']})
            else:
                if not data['dm']:
                    try:
                        await channel.send(f"<@{data['author']}> reminder for: {data['remark']}")
                    except Exception:
                        pass # this is done as bot may have being denied to send message
                    await self.collection.delete_one({'_id': data['_id']})
                else:
                    member = channel.guild.get_member(data['author'])
                    if not member:
                        await self.collection.delete_one({'_id': data['_id']})
                    else:
                        try:
                            await member.send(f"<@{data['author']}> reminder for: {data['remark']}")
                        except Exception:
                            pass # what if member DM are blocked?
                        await self.collection.delete_one({'_id': data['_id']})