from __future__ import annotations

from core import Parrot, Cog, Context
from discord.ext import commands, tasks
import discord, typing
import datetime

from utilities.converters import reason_convert
from utilities.database import guild_update

from cogs.utils import method as mt
from cogs.utils.method import giveaway


class Utils(Cog):
    """Tag System for your server"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.gw_tasks.start()
    
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
    
    @giveaway.command()
    async def reroll(self, ctx: Context, message: int):
        """To reroll the giveaway winners"""
        await mt.end_giveaway(self.bot, message, ctx=ctx, auto=False)
    
    @tasks.loop(seconds=1)
    async def gw_tasks(self):
        async for data in giveaway.find({'endtime': {'$lte': datetime.utcnow().timestamp()}}):
            guild = self.bot.get_guild(data['guild'])
            if not guild:
                return await giveaway.delete_one({'_id': data['_id']})
            try:
                await mt.end_giveaway(self.bot, data['_id'], ctx=None, auto=False)
            except Exception:
                pass
            await giveaway.delete_one({'_id': data['_id']})
