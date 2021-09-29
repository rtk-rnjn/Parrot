from __future__ import annotations

from core import Parrot, Cog, Context
from discord.ext import commands
import discord

from utilities.converters import reason_convert

from cogs.utils import method as mt


class utils(Cog):
    """Tag System for your server"""
    def __init__(self, bot: Parrot):
        self.bot = bot
    
    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def tag(self, ctx: Context, *, tag: str=None):
        """Tag management, or to show the tag"""
        if not ctx.invoked_subcommand:
            await mt._show_tag(self.bot, ctx, tag, ctx.message.reference.resolved)
    
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
        """To claim the ownership of the tag, if the owner of the tag left the server"""
        await mt._toggle_nsfw(self.bot, ctx, tag)

    @tag.command(name='give', aliases=['transfer'])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_tranfer(self, ctx: Context, tag: commands.clean_content, *, member: discord.Member):
        """To transfer the ownership of tag you own to other member"""
        await mt._transfer_owner(self.bot, ctx, tag, member)
    
    @commands.group(name='starboard', invoke_without_command=True)
    @commands.has_permissions(manage_messages=True, add_reactions=True, manage_channels=True) # manage_permissions=True
    async def starboard(self, ctx: Context, *, message: discord.Message=None):
        """Starboard Management system"""
        if not ctx.invoked_subcommand:
            pass

    @starboard.command(name='lock')
    async def star_lock(self, ctx: Context, *, reason: reason_convert=None):
        """To lock the starboard channel"""
        pass
    
    # @starboard.command(name='emoji')
    # async def star_emoji(self, ctx: Context):
    #     """Displays the starboard emoji"""
    #     pass
    
    # @starboard.command(name='channel')
    # async def star_view(self, ctx: Context):
    #     """Displays the starboard channel"""
    #     pass