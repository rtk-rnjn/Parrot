from __future__ import annotations

from core import Parrot, Cog, Context
from discord.ext import commands
import discord, typing
import datetime

from utilities.converters import reason_convert
from utilities.database import guild_update

from cogs.utils import method as mt


class Utils(Cog):
    """Tag System for your server"""
    def __init__(self, bot: Parrot):
        self.bot = bot
    
    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='sparkles_', id=892435276264259665)

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def tag(self, ctx: Context, *, tag: str=None):
        """Tag management, or to show the tag"""
        if not ctx.invoked_subcommand:
            await mt._show_tag(self.bot, ctx, tag, ctx.message.reference.resolved if ctx.message.reference else None)
    
    @tag.command(name='create', aliases=['add'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_create(self, ctx: Context, tag: commands.clean_content, *, text: commands.clean_content):
        """To create tag. All tag have unique name"""
        await mt._create_tag(self.bot, ctx, tag, text)

    @tag.command(name='delete', aliases=['del'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_delete(self, ctx: Context, tag: commands.clean_content):
        """To delete tag. You must own the tag to delete"""
        await mt._delete_tag(self.bot, ctx, tag)

    @tag.command(name='editname')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_name(self, ctx: Context, tag: commands.clean_content, *, name: commands.clean_content):
        """To edit the tag name. You must own the tag to edit"""
        await mt._name_edit(self.bot, ctx, tag, name)

    @tag.command(name='edittext')
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_text(self, ctx: Context, tag: commands.clean_content, *, text: commands.clean_content):
        """To edit the tag text. You must own the tag to edit"""
        await mt._text_edit(self.bot, ctx, tag, text)

    @tag.command(name='owner', alises=['info'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_owner(self, ctx: Context, *, tag: commands.clean_content):
        """To check the tag details."""
        await mt._view_tag(self.bot, ctx, tag)
    
    @tag.command(name='snipe', aliases=['steal', 'claim'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_claim(self, ctx: Context, *, tag: commands.clean_content):
        """To claim the ownership of the tag, if the owner of the tag left the server"""
        await mt._claim_owner(self.bot, ctx, tag)
    
    @tag.command(name='togglensfw', aliases=['nsfw', 'tnsfw'])
    @commands.bot_has_permissions(embed_links=True)
    async def toggle_nsfw(self, ctx: Context, *, tag: commands.clean_content):
        """To enable/disable the NSFW of a Tag."""
        await mt._toggle_nsfw(self.bot, ctx, tag)

    @tag.command(name='give', aliases=['transfer'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_tranfer(self, ctx: Context, tag: commands.clean_content, *, member: discord.Member):
        """To transfer the ownership of tag you own to other member"""
        await mt._transfer_owner(self.bot, ctx, tag, member)
    
    @commands.group(name='starboard', invoke_without_command=True)
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True) # manage_permissions=True
    async def starboard(self, ctx: Context, *, message: int):
        """Starboard Management system"""
        if not ctx.invoked_subcommand:
            db = await self.bot.db('parrot_db')
            collection = db['server_config']
            if data := collection.find_one({'_id': ctx.guild.id, 'starboard': {}}):
                try:
                    channel = ctx.guild.get_channel(data['starboard']['channel'])
                except KeyError:
                    return await ctx.reply(f"{ctx.author.mention} starboard channel is either deleted or bot can not see that channel")
                finally:
                    if msg := await channel.fetch_message(message.id):
                        pass # TODO: to show the info regarding the star message
                    else:
                        return await ctx.reply(f"{ctx.author.mention} Something not right. Message either deleted or the ID is invalid")
            else:
                return await ctx.reply(f"{ctx.author.mention} Starboard channel not found!")
                    
    @starboard.command(name='lock')
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True)
    async def star_lock(self, ctx: Context):
        """To lock the starboard channel"""
        db = await self.bot.db('parrot_db')
        collection = parrot_db['server_config']
        await collection.update_one({'_id': ctx.guild.id}, {'$set': {'star_lock': True}})
        await ctx.reply(
            f"{ctx.author.mention} starboard channel is locked!"
        )

    @starboard.command(name='unlock')
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True)
    async def star_unlock(self, ctx: Context):
        """To lock the starboard channel"""
        db = await self.bot.db('parrot_db')
        collection = parrot_db['server_config']
        await collection.update_one({'_id': ctx.guild.id}, {'$set': {'star_lock': False}})
        await ctx.reply(
            f"{ctx.author.mention} starboard channel is unlocked!"
        )
    
    @starboard.command(aliases=['starc'])
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True)
    @Context.with_type
    async def starchannel(self, ctx: Context, *, channel: discord.TextChannel=None):
        """To set the starboard channel in your server"""
        if not channel:
            post = {'starboard': {'channel': None}}
            await guild_update(ctx.guild.id, post)
            return await ctx.reply(
                f"{ctx.author.mention} starboard channel removed"
            )
        post = {'starboard': {'channel': channel.id}}
        await guild_update(ctx.guild.id, post)
        await ctx.reply(
          f"{ctx.author.mention} starboard channel for the server is being set to {channel.mention}"
        )

    @starboard.command(aliases=['stare'])
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True)
    @Context.with_type
    async def staremoji(self, ctx: Context, *, emoji: typing.Union[discord.Emoji, discord.PartialEmoji, str]):
        """To set the starboard channel in your server"""
        channel = channel or ctx.channel
        post = {'starboard': {'emoji': str(emoji)}}
        await guild_update(ctx.guild.id, post)
        await ctx.reply(
          f"{ctx.author.mention} starboard emoji for the server is being set to {emoji}"
        )
    
    @starboard.command(aliases=['starc'])
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True)
    @Context.with_type
    async def starcount(self, ctx: Context, *, number: int):
        """To set the starboard channel in your server"""
        channel = channel or ctx.channel
        post = {'starboard': {'count': number}}
        await guild_update(ctx.guild.id, post)
        await ctx.reply(
          f"{ctx.author.mention} starboard emoji count for the server is being set to {number}"
        )
    
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