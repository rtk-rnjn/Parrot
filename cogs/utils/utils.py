from __future__ import annotations

from core import Parrot, Cog, Context
from discord.ext import commands, tasks
import discord

import typing, datetime, random

from utilities.converters import reason_convert
from utilities.database import parrot_db, msg_db
from utilities.time import ShortTime
from utilities.paginator import PaginationView

from cogs.utils import method as mt
from cogs.utils.method import giveaway


class Utils(Cog):
    """Utilities for server, UwU"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.gw_tasks.start()
        self.react_collection = parrot_db['reactions']
        self.reminder_task.start()
        self.collection = parrot_db['timers']
    
    async def create_timer(self, 
                           channel: typing.Union[discord.TextChannel, discord.Thread], 
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
            await ctx.reply(f"{ctx.author.mention} check you DM")
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
            await ctx.reply(f"{ctx.author.mention} check you DM")
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
    
    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='sparkles_', id=892435276264259665)

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def tag(self, ctx: Context, *, tag: str=None):
        """Tag management, or to show the tag"""
        if not ctx.invoked_subcommand and tag is not None:
            await mt._show_tag(self.bot, ctx, tag, ctx.message.reference.resolved if ctx.message.reference else None)
    
    @tag.command(name='create', aliases=['add'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_create(self, ctx: Context, tag: str, *, text: str):
        """To create tag. All tag have unique name"""
        await mt._create_tag(self.bot, ctx, tag, text)

    @tag.command(name='delete', aliases=['del'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_delete(self, ctx: Context, *, tag: str):
        """To delete tag. You must own the tag to delete"""
        await mt._delete_tag(self.bot, ctx, tag)

    @tag.command(name='editname')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_name(self, ctx: Context, tag: str, *, name: str):
        """To edit the tag name. You must own the tag to edit"""
        await mt._name_edit(self.bot, ctx, tag, name)

    @tag.command(name='edittext')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_text(self, ctx: Context, tag: str, *, text: str):
        """To edit the tag text. You must own the tag to edit"""
        await mt._text_edit(self.bot, ctx, tag, text)

    @tag.command(name='owner', alises=['info'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_owner(self, ctx: Context, *, tag: str):
        """To check the tag details."""
        await mt._view_tag(self.bot, ctx, tag)
    
    @tag.command(name='snipe', aliases=['steal', 'claim'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_claim(self, ctx: Context, *, tag: str):
        """To claim the ownership of the tag, if the owner of the tag left the server"""
        await mt._claim_owner(self.bot, ctx, tag)
    
    @tag.command(name='togglensfw', aliases=['nsfw', 'tnsfw'])
    @commands.bot_has_permissions(embed_links=True)
    async def toggle_nsfw(self, ctx: Context, *, tag: str):
        """To enable/disable the NSFW of a Tag."""
        await mt._toggle_nsfw(self.bot, ctx, tag)

    @tag.command(name='give', aliases=['transfer'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_tranfer(self, ctx: Context, tag: str, *, member: discord.Member):
        """To transfer the ownership of tag you own to other member"""
        await mt._transfer_owner(self.bot, ctx, tag, member)
    
    @tag.command(name='all')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_all(self, ctx: Context):
        """To show all tags"""
        await mt._show_all_tags(self.bot, ctx)
    
    @tag.command(name='mine')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_mine(self, ctx: Context):
        """To show those tag which you own"""
        await mt._show_tag_mine(self.bot, ctx)

    @commands.command()
    @commands.has_permissions(manage_messages=True, add_reactions=True)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True, read_message_history=True)
    @Context.with_type
    async def quickpoll(self, ctx: Context, *questions_and_choices: str):
        """
        To make a quick poll for making quick decision. 'Question must be in quotes' and Options, must, be, seperated, by, commans.
        Not more than 10 options. :)
        """
        def to_emoji(c):
            base = 0x1f1e6
            return chr(base + c)

        if len(questions_and_choices) < 3:
            return await ctx.send('Need at least 1 question with 2 choices.')
        elif len(questions_and_choices) > 21:
            return await ctx.send('You can only have up to 20 choices.')

        question = questions_and_choices[0]
        choices = [(to_emoji(e), v) for e, v in enumerate(questions_and_choices[1:])]

        try:
            await ctx.message.delete()
        except:
            pass

        body = "\n".join(f"{key}: {c}" for key, c in choices)
        poll = await ctx.send(f'**Poll: {question}**\n\n{body}')
        for emoji, _ in choices:
            await poll.add_reaction(emoji)
    
    @commands.group(name='todo', invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def todo(self, ctx: Context):
        """For making the TODO list"""
        if not ctx.invoked_subcommand:
            await mt._list_todo(self.bot, ctx)
    
    @todo.command(name='show')
    @commands.bot_has_permissions(embed_links=True)
    async def todu_show(self, ctx: Context, *, name: str):
        """To show the TODO task you created"""
        await mt._show_todo(self.bot, ctx, name)
    
    @todo.command(name='create')
    @commands.bot_has_permissions(embed_links=True)
    async def todo_create(self, ctx: Context, name: str, *, text: str):
        """To create a new TODO"""
        await mt._create_todo(self.bot, ctx, name, text)
    
    @todo.command(name='editname')
    @commands.bot_has_permissions(embed_links=True)
    async def todo_editname(self, ctx: Context, name: str, *, new_name: str):
        """To edit the TODO name"""
        await mt._update_todo_name(self.bot, ctx, name, new_name)
    
    @todo.command(name='edittext')
    @commands.bot_has_permissions(embed_links=True)
    async def todo_edittext(self, ctx: Context, name: str, *, text: str):
        """To edit the TODO text"""
        await mt._update_todo_text(self.bot, ctx, name, text)
    
    @todo.command(name='delete')
    @commands.bot_has_permissions(embed_links=True)
    async def delete_todo(self, ctx: Context, *, name: str):
        """To delete the TODO task"""
        await mt._delete_todo(self.bot, ctx, name)

    @todo.command(name='settime', aliases=['set-time'])
    @commands.bot_has_permissions(embed_links=True)
    async def settime_todo(self, ctx: Context, name: str, *, deadline: ShortTime):
        """To set timer for your Timer"""
        await mt._set_timer_todo(self.bot, ctx, name, deadline.dt.timestamp())

    @commands.group(name='giveaway')
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.has_permissions(manage_guild=True, add_reactions=True)
    async def giveaway(self, ctx: Context):
        """To host small giveaways in the server. Do not use this as dedicated server giveaway"""
        pass
    
    @giveaway.command()
    async def create(self, ctx: Context):
        """To create a giveaway in the server"""
        await mt.create_gw(self.bot, ctx)
    
    @giveaway.command()
    async def end(self, ctx: Context, message: int):
        """To end the giveaway"""
        await mt.end_giveaway(self.bot, message, ctx=ctx, auto=False)
        await giveaway.delete_one({'_id': message})
    
    # @giveaway.command()
    # async def reroll(self, ctx: Context, message: int):
    #     """To reroll the giveaway winners"""
    #     await mt.end_giveaway(self.bot, message, ctx=ctx, auto=False)
    

    @tasks.loop(seconds=1)
    async def gw_tasks(self):
        await self.bot.wait_until_ready()
        async for data in giveaway.find({'endtime': {'$lte': datetime.datetime.utcnow().timestamp()}}):
            channel = self.bot.get_channel(data['channel'])
            if not channel:
                return await giveaway.delete_one({'_id': data['_id']})
            msg = await self.bot.fetch_message_by_channel(channel, data['_id'])
            if not msg:
                return await giveaway.delete_one({'_id': data['_id']})
            for reaction in msg.reactions:
                if str(reaction) == "\N{PARTY POPPER}":
                    if reaction.count < (data['winners'] - 1):
                        print('reaction count', reaction.count)
                        return await channel.send(
                            f"Winners of giveaway at **{msg.jump_url}** can not be decided due to insufficient reaction count."
                        )
                    users = await reaction.users().flatten()
                    await self.write_db(users, data['_id'])
                    w = await self.get_winners(data['winners'], data['_id'])
                    winners = await self.check_gw_requirements(
                        w, data['_id'], data['link'], data['guild']
                    )
                    if winners:
                        await channel.send(f"Contrats **{', '.join(['<@'+str(w)+'>' for w in winners])}**. You won {data['prize']}")
                    else:
                        await channel.send(f"Well. No one winner can not be determined")
                    print(winners)
            await giveaway.delete_one({'_id': data['_id']})
            await self.react_collection.delete_one({'_id': data['_id']})

    async def write_db(self, users: list[typing.Union[discord.Users, discord.Members, int]], messageID: int):
        post = {
            '_id': messageID,
            'ids': [user.id if type(user) is not int else user for user in users]
        }
        try:
            await self.react_collection.insert_one(post)
        except Exception:
            pass
    
    async def get_winners(self, winners: int, messageID: int) -> typing.Optional[list[int]]:
        if data := await self.react_collection.find_one({'_id': messageID}):
            winners = random.sample(data['ids'], winners)
            li2 = data['ids']
            li1 = winners
            ids = [i for i in li1 + li2 if i not in li1 or i not in li2]
            await self.react_collection.update_one({'_id': data['_id']}, {'$set': {'ids': ids}})    
            return winners if winners else None
    
    async def check_gw_requirements(
                self, 
                winners: list[
                        typing.Union[
                            discord.Users, 
                            discord.Members,
                            int
                        ]
                    ], 
                message: typing.Optional[int],
                link: typing.Optional[str],
                guild_: int
            ) -> typing.Optional[list[int]]:
        guild = await self.bot.fetch_invite(link) if link else None
        if not isinstance(guild, discord.Guild):
            print(1)
            return None # bot isnt in the guild...
            
        g = self.bot.get_guild(guild_)
        if not g:
            return None # bot is kicked or banned...
        new_winners = []
        collection = msg_db[f"{g.id}"]
        for winner in winners:
            print(2)
            msg_req = await collection.find_one({'_id': winner.id if type(winner) is not int else winner})
            print(3)
            if ((msg_req['count'] >= message)) or (message is None):
                print(4)
                if not guild:
                    new_winners.append(winner)
                    print(5)
                else:
                    print(6)
                    m = guild.get_member(winner)
                    if m:
                        new_winners.append(m.id)
                    else:
                        pass
        
        return new_winners if new_winners else None