from __future__ import annotations

import discord, typing, random

from datetime import datetime
from time import time

from utilities.database import tags, todo, parrot_db, msg_db, cluster
from utilities.buttons import Confirm, Prompt
from utilities.paginator import PaginationView, ParrotPaginator
from utilities.time import ShortTime

from discord.ext import commands

from core import Parrot, Context

giveaway = parrot_db['giveaway']
reacter = cluster['reacter']

async def _show_tag(bot: Parrot, ctx: Context, tag, msg_ref=None):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if not data['nsfw']:
            if msg_ref is not None:
                await msg_ref.reply(data["text"])
            else:
                await ctx.send(data["text"])
        else:
            if ctx.channel.nsfw:
                if msg_ref is not None:
                    await msg_ref.reply(data["text"])
                else:
                    await ctx.send(data["text"])
            else:
                await ctx.reply(f"{ctx.author.mention} this tag can only be called in NSFW marked channel")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")
    await collection.update_one({"id": tag}, {"$inc": {"count": 1}})


async def _create_tag(bot: Parrot, ctx: Context, tag, text):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        return await ctx.reply(f"{ctx.author.mention} the name `{tag}` already exists")
    else:
        view = Prompt(ctx.author.id)
        msg = await ctx.send(f"{ctx.author.mention} do you want to make the tag as NSFW marked channels", view=view)
        await view.wait()
        if view.value is None:
            await msg.reply(f"{ctx.author.mention} you did not responds on time. Considering as non NSFW")
            nsfw = False
        elif view.value:
            nsfw = True
        else:
            nsfw = False
        await collection.insert_one(
            {
                "id": tag,
                "text": text,
                "count": 0,
                "owner": ctx.author.id,
                "nsfw": nsfw,
                "created_at": int(time()),
            }
        )
        await ctx.reply(f"{ctx.author.mention} tag created successfully")


async def _delete_tag(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"id": tag})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot: Parrot, ctx: Context, tag, name):
    collection = tags[f"{ctx.guild.id}"]
    if exists := await collection.find_one({"id": name}):
        await ctx.reply(
            f"{ctx.author.mention} that name already exists in the database"
        )
    elif data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"id": name}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _text_edit(bot: Parrot, ctx: Context, tag, text):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"text": text}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        member = ctx.guild.get_member(data["owner"])
        if member:
            return await ctx.reply(
                f"{ctx.author.mention} you can not claim the tag ownership as the member is still in the server"
            )
        await collection.update_one({"id": tag}, {"$set": {"owner": ctx.author.id}})
        await ctx.reply(f"{ctx.author.mention} ownership of tag `{tag}` claimed!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _transfer_owner(bot: Parrot, ctx: Context, tag, member):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        view = Confirm(ctx.author.id)
        msg = await ctx.reply(
            f"{ctx.author.mention} are you sure to transfer the tag ownership to **{member}**? This process is irreversible!",
            view=view,
        )
        await view.wait()
        if view.value is None:
            await msg.reply(f"{ctx.author.mention} you did not responds on time")
        elif view.value:
            await collection.update_one({"id": tag}, {"$set": {"owner": member.id}})
            await msg.reply(
                f"{ctx.author.mention} tag ownership successfully transfered to **{member}**"
            )
        else:
            await msg.reply(f"{ctx.author.mention} ok! reverting the process!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _toggle_nsfw(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({'id': tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        nsfw = not data['nsfw']
        await collection.update_one({'id': tag}, {'$set': {'nsfw': nsfw}})
        await ctx.reply(
            f"{ctx.author.mention} NSFW status of tag named `{tag}` is set to **{nsfw}**"
          )
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")

async def _show_tag_mine(bot: Parrot, ctx: Context):
    collection = tags[f'{ctx.guild.id}']
    i = 1
    paginator = ParrotPaginator(ctx, title="Tags")
    async for data in collection.find({'owner': ctx.author.id}):
        paginator.add_line(f"`{i}` {data['_id']}")
        i += 1
    try:
        await paginator.start()
    except Exception:
        await ctx.reply(f"{ctx.author.mention} you don't have any tags registered with your name")

async def _show_all_tags(bot: Parrot, ctx: Context):
    collection = tags[f"{ctx.guild.id}"]
    i = 1
    paginator = ParrotPaginator(ctx, title=f"Tags", per_page=12)
    async for data in collection.find({}):
        paginator.add_line(f"`{i}` {data['id']}")
        i += 1
    try:
        await paginator.start()
    except Exception:
        await ctx.reply(f"{ctx.author.mention} this server don't have any tags")

async def _view_tag(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        em = discord.Embed(
            title=f"Tag: {tag}", timestamp=datetime.utcnow(), color=ctx.author.color
        )
        text_len = len(data["text"])
        owner = ctx.guild.get_member(data["owner"])
        nsfw = data["nsfw"]
        count = data["count"]
        created_at = f"<t:{data['created_at']}>"
        claimable = True if owner is None else False
        em.add_field(name="Owner", value=f"**{owner.mention if owner else None}** ")
        em.add_field(name="Created At?", value=created_at)
        em.add_field(name="Text Length", value=str(text_len))
        em.add_field(name="Is NSFW?", value=nsfw)
        em.add_field(name="Tag Used", value=count)
        em.add_field(name="Can Claim?", value=claimable)
        em.set_footer(text=f"{ctx.author}")
        await ctx.reply(embed=em)


async def _create_todo(bot: Parrot, ctx: Context, name, text):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        await ctx.reply(f"{ctx.author.mention} `{name}` already exists as your TODO list")
    else:
        await collection.insert_one(
          {
            'id': name, 
            'text': text, 
            'time': int(time()),
            'deadline': None,
            'msglink': ctx.message.jump_url
          }
        )
        await ctx.reply(f"{ctx.author.mention} created as your TODO list")

async def _set_timer_todo(bot: Parrot, ctx: Context, name: str, timestamp: float):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({'id': name}):
        post = {'deadline': timestamp}
        try:
            await ctx.author.send(f"{ctx.author.mention} check your DM")
        except Exception:
            return await ctx.reply(f"{ctx.author.mention} can not complete the action as your DM(s) are locked for the bot")
        await collection.update_one({'_id': name}, {'$set': post})
        await bot.get_cog('Utils').create_timer(ctx.channel, ctx.message, ctx.author, timestamp, reamark=f'{ctx.author.mention} you had set TODO reminder for your task named **{name}**', dm=True)
        await ctx.author.send(f"You will be reminded for your task named **{name}** here at <t:{int(timestamp)}>. To delete your reminder consider typing.\n```\n$delremind {ctx.message.id}```")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")

async def _update_todo_name(bot: Parrot, ctx: Context, name, new_name):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        if new_data := await collection.find_one({"id": new_name}):
            await ctx.reply(f"{ctx.author.mention} `{new_name}` already exists as your TODO list")
        else:
            await collection.update_one({'id': name}, {'$set': {'id': new_name}})
            await ctx.reply(f"{ctx.author.mention} name changed from `{name}` to `{new_name}`")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")

async def _update_todo_text(bot: Parrot, ctx: Context, name, text):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        await collection.update_one({'id': name}, {'$set': {'text': text}})
        await ctx.reply(f"{ctx.author.mention} TODO list of name `{name}` has been updated")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")

async def _list_todo(bot: Parrot, ctx: Context):
    collection = todo[f"{ctx.author.id}"]
    i = 1
    paginator = ParrotPaginator(ctx, title=f"Your Pending Tasks", per_page=12)
    async for data in collection.find({}):
        paginator.add_line(f"[`{i}`]({data['msglink']}) {data['id']}")
        i += 1
    try:
        await paginator.start()
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you do not have task to do")

async def _show_todo(bot: Parrot, ctx: Context, name):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({'id': name}):
        await ctx.reply(f"> **{data['id']}**\n\nDescription: {data['text']}\n\nCreated At: <t:{data['time']}>")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")

async def _delete_todo(bot: Parrot, ctx: Context, name):
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({'id': name}):
        await collection.delete_one({'id': name})
        await ctx.reply(f"{ctx.author.mention} delete `{name}` task")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")

    
async def create_gw(bot: Parrot, ctx: Context):
    questions = [
        (1, "Enter the prize of Giveaway"),
        (2, "Enter the channel in which the giveaway will be hosted"),
        (3, "Enter amount of winners"),
        (4, "Enter duration of giveaway"),
        (5, "Enter Message requirements (if any)"),
        (6, "Enter the server link incase requirement (if any)")
    ]
    def check(m):
        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
    
    answers = {}
    channel = None
    
    for i, q in questions:
        await ctx.send(f"{ctx.author.mention} **{q}**")
        msg = await bot.wait_for('message', check=check, timeout=30)
        
        if msg.content.lower() in ('end', 'cancel'):
            return await ctx.send(f"{ctx.author.mention} alright, reverting all process")
        if i == 1:
            answers['prize'] = msg.content
        if i == 2:
            channel = await commands.TextChannelConverter().convert(ctx, msg.content)
            if not channel:
                return await ctx.send(f"{ctx.author.mention} Invalid Channel")
            if not (channel.permissions_for(ctx.guild.me).add_reactions and channel.permissions_for(ctx.guild.me).embed_links):
                return await ctx.send(f"{ctx.author.mention} bot don't have Add Reaction and Embed Links permission in {channel.mention}")  
            answers['channel'] = channel.id
            
        if i == 3:
            try:
                winner = int(msg.content)
            except Exception:
                return await ctx.send(f"{ctx.author.mention} Invalid Winner count")
            answers['winners'] = winner
        if i == 4:
            seconds = ShortTime(f'{msg.content}').dt.timestamp()
            answers['endtime'] = seconds
        if i == 5:
            if msg.content.lower() in ('none', 'no', 'na'):
                answers['message'] = None
            else:
                try:
                    message_requirement = int(msg.content)
                    answers['message'] = message_requirement
                except Exception:
                    return await ctx.send(f"{ctx.author.mention} Invalid Message Requirement count")
        if i == 6:
            answers['link'] = None if msg.content.lower() in ('none', 'no', 'na') else msg.content
        
    _id = await channel.send(
            embed=discord.Embed(
                description=f"**Prize:** {answers['prize']}\n**Ends In:** <t:{int(answers['endtime'])}>\n**Winner:** {answers['winners']}\n**Hosted By:** {ctx.author.mention}",
                timestamp=datetime.utcnow(),
                color=ctx.guild.owner.color
            ).set_author(
                name=f"GIVEAWAY!"
            ).set_footer(
                text=f"ID: {ctx.message.id}"
            )
        )
    answers['_id'] = _id.id
    answers['guild'] = ctx.guild.id
    await giveaway.insert_one(answers)
    # {
    #     '_id': int,
    #     'link': str,
    #     'guild': int,
    #     'endtime': float,
    #     'winners': int,
    #     'message': int,
    #     'prize': str,
    #     'channel': int
    # }
    await _id.add_reaction("\N{PARTY POPPER}")
    
    await ctx.send(f"{ctx.author.mention} success. Giveaway created in {channel.mention}. Giveaway URL: **<{_id.jump_url}>**")

async def end_giveaway(bot: Parrot, _id: int, *, ctx: Context=None, auto: bool=False):
    if data := await giveaway.find_one({'_id': _id}):
        if not auto:
            if not (data['guild'] == ctx.guild.id):
                return await ctx.send(f"{ctx.author.mention} invalid message ID") if ctx else None
            
            channel = ctx.guild.get_channel(data['channel'])
        else:
            channel = bot.get_guild(data['guild']).get_channel(data['channel'])

        if not channel:
            await giveaway.delete_one({'_id': _id})
            if not auto:
                return await ctx.send(
                    f"{ctx.author.mention} the channel in which the giveaway with id **{_id}** was hosted is either deleted or bot do not have permission to see that channel"
                ) if ctx else None
            
        async for msg in channel.history(limit=1, before=discord.Object(_id+1), after=discord.Object(_id-1)): # this is good. UwU
            if msg is None:
                if not auto:
                    return await ctx.send(f"{ctx.author.mention} no message found! Proably deleted") if ctx else None
            await msg.remove_reaction("\N{PARTY POPPER}", channel.guild.me)

        for reaction in msg.reactions:
            if str(reaction) == "\N{PARTY POPPER}":
                if reaction.count < (data['winners'] - 1):
                    if not auto:
                        return await ctx.send(
                            f"{ctx.author.mention} winner can not be decided due to insufficient reaction count."
                        ) if ctx else None
                users = await reaction.users().flatten()
                ls = await get_winners(
                    bot, 
                    ctx=ctx, 
                    msg=msg,
                    guild=data['guild'],
                    channel=channel, 
                    users=users, 
                    winners=data['winners'], 
                    msg_required=data['message'], 
                    server_link=data['link']
                )
                if ls[0] == 0:
                    return await ctx.send(
                        f"{ctx.author.mention} can not determine the winner, bot isn't in the server as it is the requiremnt"
                    ) if ctx and (not auto) else None
                
                return await channel.send(f"**Congrats {', '.join(member.mention for member in ls)}. You won {data['prize']}.**")
        else:
            if not auto:
                return await ctx.send(f"{ctx.author.mention} winner can not be decided as reactions on the messages had being cleared.") if ctx else None
    else:
        if not auto:
            await ctx.send(f"{ctx.author.mention} invalid message ID") if ctx else None

async def get_winners(
                bot: Parrot, 
                *,
                msg: discord.Message, 
                guild: int, 
                ctx: Context=None, 
                channel: discord.TextChannel, 
                users: list, 
                winners: int,
                msg_required: int=None, 
                server_link: str=None
            ) -> list:
    collection = msg_db[f"{guild}"]
    wins = random.sample(users, winners)
    req_reroll = True
    while req_reroll:
        if msg_required:
            for m in wins:
                if data := await collection.find_one({'_id': m.id}):
                    if data['count'] < msg_required:
                        winners.remove(m)
                        req_reroll = True
                else:
                    winners.remove(m)
                    req_reroll = True
            else:
                req_reroll = False

        elif server_link:
            invite = bot.fetch_invite(server_link)
            ignore_obj = (discord.PartialInviteGuild, discord.PartialInviteChannel) # bot isnt in guild
            if isinstance(invite, ignore_obj):
                return [0]
            guild = invite.guild
            for m in wins:
                m_obj = guild.get_member(m.id) # to check whether member is in required guild
                if not m_obj:
                    winners.remove(m)
                    req_reroll = True
            else:
                req_reroll = False

        else:
            req_reroll = False
    for m in wins:
        await msg.remove_reaction("\N{PARTY POPPER}", m)
    return wins

