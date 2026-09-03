from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.tags")


class Tags(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="tags")
    async def tags(self, ctx: commands.Context[Parrot]) -> None:
        """List all tags in the server."""
        assert ctx.guild is not None

        tags = await self.bot.database_manager.get_all_tags(guild_id=ctx.guild.id)
        if not tags:
            await ctx.reply("No tags found in this server.")
            return

        pages = []
        for index, tag in enumerate(tags, start=1):
            page = f"{index}. `{tag['name']}`"
            pages.append(page)

        await self.bot.paginate(ctx, embed=discord.Embed(), pages=pages)

    @commands.group(name="tag")
    async def tag(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """View a specific tag."""
        assert ctx.guild is not None

        content = await self.bot.database_manager.get_tag_content(guild_id=ctx.guild.id, name_or_alias=name)
        if content is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())

    @tag.command(name="all", aliases=["list", "ls"])
    async def list_tags(self, ctx: commands.Context[Parrot]) -> None:
        """List all tags in the server."""
        await ctx.invoke(self.tags)

    @tag.command(name="create", aliases=["add", "new"])
    async def create_tag(self, ctx: commands.Context[Parrot], name: str, *, content: Annotated[str, commands.clean_content]) -> None:
        """Create a new tag."""
        assert ctx.guild is not None

        exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=name)
        if exists:
            await ctx.reply(f"Tag `{name}` already exists.")
            return

        await self.bot.database_manager.create_tag(guild_id=ctx.guild.id, name=name, content=content, creator_id=ctx.author.id)
        await ctx.reply(f"Tag `{name}` created successfully.")

    @tag.command(name="delete", aliases=["remove", "rm", "del"])
    async def delete_tag(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """Delete a tag."""
        assert ctx.guild is not None

        deleted = await self.bot.database_manager.delete_tag(guild_id=ctx.guild.id, name=name, creator_id=ctx.author.id)
        if deleted:
            await ctx.reply(f"Tag `{name}` deleted successfully.")
        else:
            await ctx.reply(f"No tag found with the name: `{name}`")

    @tag.command(name="edit", aliases=["update"])
    async def edit_tag(self, ctx: commands.Context[Parrot], name: str, *, new_content: Annotated[str, commands.clean_content]) -> None:
        """Edit a tag's content."""
        assert ctx.guild is not None

        exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        await self.bot.database_manager.edit_tag_content(guild_id=ctx.guild.id, creator_id=ctx.author.id, name=name, content=new_content)
        await ctx.reply(f"Tag `{name}` updated successfully.")

    @tag.group(name="alias", invoke_without_command=True)
    async def tag_alias(self, ctx: commands.Context[Parrot]) -> None:
        """Manage tag aliases."""
        await ctx.send_help(ctx.command)

    @tag_alias.command(name="add", aliases=["create", "new"])
    async def add_tag_alias(self, ctx: commands.Context[Parrot], tag_name: str, alias: str) -> None:
        """Add an alias to a tag."""
        assert ctx.guild is not None

        exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{tag_name}`")
            return

        alias_exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=alias)
        if alias_exists:
            await ctx.reply(f"Alias `{alias}` already exists as a tag or alias.")
            return

        await self.bot.database_manager.add_tag_alias(guild_id=ctx.guild.id, name=tag_name, alias=alias)
        await ctx.reply(f"Alias `{alias}` added to tag `{tag_name}` successfully.")

    @tag_alias.command(name="remove", aliases=["delete", "rm", "del"])
    async def remove_tag_alias(self, ctx: commands.Context[Parrot], tag_name: str, alias: str) -> None:
        """Remove an alias from a tag."""
        assert ctx.guild is not None

        exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{tag_name}`")
            return

        alias_exists = await self.bot.database_manager.is_tag_present(guild_id=ctx.guild.id, name_or_alias=alias)
        if not alias_exists:
            await ctx.reply(f"No alias found with the name: `{alias}`")
            return

        await self.bot.database_manager.remove_tag_alias(guild_id=ctx.guild.id, creator_id=ctx.author.id, name=tag_name, alias=alias)
        await ctx.reply(f"Alias `{alias}` removed from tag `{tag_name}` successfully.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Tags(bot))
