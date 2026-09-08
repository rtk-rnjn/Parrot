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

        tags = await self.bot.database.get_all_tags(guild_id=ctx.guild.id)
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

        content = await self.bot.database.get_tag_content(guild_id=ctx.guild.id, name_or_alias=name)
        if content is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return
        channel_is_nsfw = getattr(ctx.channel, "is_nsfw", lambda: False)()
        if await self.bot.database.is_tag_nsfw(guild_id=ctx.guild.id, name_or_alias=name) and not channel_is_nsfw:
            raise commands.NSFWChannelRequired(ctx.channel)  # type: ignore[arg-type]

        await self.bot.database.increment_tag_used_count(
            guild_id=ctx.guild.id,
            name_or_alias=name,
            author_id=ctx.author.id,
        )
        await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())

    @tag.command(name="all", aliases=["list", "ls"])
    async def list_tags(self, ctx: commands.Context[Parrot]) -> None:
        """List all tags in the server."""
        await ctx.invoke(self.tags)

    @tag.command(name="create", aliases=["add", "new"])
    async def create_tag(self, ctx: commands.Context[Parrot], name: str, *, content: Annotated[str, commands.clean_content]) -> None:
        """Create a new tag."""
        assert ctx.guild is not None

        exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=name)
        if exists:
            await ctx.reply(f"Tag `{name}` already exists.")
            return

        channel_is_nsfw = getattr(ctx.channel, "is_nsfw", lambda: False)()
        await self.bot.database.create_tag(
            guild_id=ctx.guild.id,
            name=name,
            content=content,
            creator_id=ctx.author.id,
            nsfw=channel_is_nsfw,
        )
        await ctx.reply(f"Tag `{name}` created successfully.")

    @tag.command(name="delete", aliases=["remove", "rm", "del"])
    async def delete_tag(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """Delete a tag."""
        assert ctx.guild is not None

        tag_name = await self.bot.database.get_tag_name(guild_id=ctx.guild.id, name_or_alias=name)
        if tag_name is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        is_admin = isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator
        owner_id = await self.bot.database.get_tag_owner_id(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not is_admin and owner_id != ctx.author.id:
            await ctx.reply("Only the tag owner or a server administrator can delete this tag.")
            return
        if not await self.bot.confirm(ctx, f"Are you sure you want to delete tag `{tag_name}`?"):
            return

        deleted = await self.bot.database.delete_tag(
            guild_id=ctx.guild.id,
            name=tag_name,
            creator_id=ctx.author.id,
            is_admin=is_admin,
        )
        if deleted:
            await ctx.reply(f"Tag `{tag_name}` deleted successfully.")
        else:
            await ctx.reply(f"No tag found with the name: `{name}`")

    @tag.command(name="raw")
    async def raw_tag(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """View a tag with mentions escaped."""
        assert ctx.guild is not None

        content = await self.bot.database.get_tag_content(guild_id=ctx.guild.id, name_or_alias=name)
        if content is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return
        if await self.bot.database.is_tag_nsfw(guild_id=ctx.guild.id, name_or_alias=name) and not getattr(ctx.channel, "is_nsfw", lambda: False)():
            raise commands.NSFWChannelRequired(ctx.channel)  # type: ignore[arg-type]

        await self.bot.database.increment_tag_used_count(
            guild_id=ctx.guild.id,
            name_or_alias=name,
            author_id=ctx.author.id,
        )
        await ctx.reply(discord.utils.escape_mentions(content), allowed_mentions=discord.AllowedMentions.none())

    @tag.command(name="transfer")
    async def transfer_tag(self, ctx: commands.Context[Parrot], name: str, member: discord.Member) -> None:
        """Transfer a tag to another server member."""
        assert ctx.guild is not None

        tag_name = await self.bot.database.get_tag_name(guild_id=ctx.guild.id, name_or_alias=name)
        if tag_name is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        is_admin = isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator
        owner_id = await self.bot.database.get_tag_owner_id(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not is_admin and owner_id != ctx.author.id:
            await ctx.reply("Only the tag owner or a server administrator can transfer this tag.")
            return
        if not await self.bot.confirm(ctx, f"Transfer `{tag_name}` to {member.mention}?"):
            return

        transferred = await self.bot.database.transfer_tag_ownership(
            guild_id=ctx.guild.id,
            name=tag_name,
            new_creator_id=member.id,
        )
        await ctx.reply(f"Tag `{tag_name}` transferred to {member.mention}." if transferred else f"No tag found with the name: `{name}`")

    @tag.command(name="search")
    async def search_tags(self, ctx: commands.Context[Parrot], *, query: str) -> None:
        """Search tag names and aliases."""
        assert ctx.guild is not None

        matches = await self.bot.database.search_tags(guild_id=ctx.guild.id, query=query)
        if not matches:
            await ctx.reply(f"No tags found matching `{query}`.")
            return
        await self.bot.paginate(ctx, embed=discord.Embed(title=f"Tags matching {query}"), pages=[f"`{name}`" for name in matches])

    @tag.command(name="count", aliases=["usage", "stats"])
    async def tag_usage(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """Show usage counts for a tag."""
        assert ctx.guild is not None

        usage = await self.bot.database.get_tag_usage(guild_id=ctx.guild.id, name_or_alias=name)
        if usage is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return
        total = sum(usage.values())
        await ctx.reply(f"Tag `{name}` has been used **{total}** times by **{len(usage)}** users.")

    @tag.group(name="top", invoke_without_command=True)
    async def top_tags(self, ctx: commands.Context[Parrot]) -> None:
        """Show top tag usage reports."""
        await ctx.send_help(ctx.command)

    @top_tags.command(name="users")
    async def top_tag_users(self, ctx: commands.Context[Parrot]) -> None:
        """Show users with the most tag uses."""
        assert ctx.guild is not None

        rows = await self.bot.database.get_top_tag_users(guild_id=ctx.guild.id)
        pages = []
        for index, row in enumerate(rows, start=1):
            user = await self.bot.get_or_fetch_user(row["user_id"])
            name = user.mention if user is not None else f"User {row['user_id']}"
            pages.append(f"{index}. {name}: **{row['count']}** uses")
        await ctx.reply("No tag usage recorded yet." if not pages else "\n".join(pages))

    @top_tags.command(name="used", aliases=["tags"])
    async def top_used_tags(self, ctx: commands.Context[Parrot]) -> None:
        """Show the most-used tags."""
        assert ctx.guild is not None

        rows = await self.bot.database.get_top_used_tags(guild_id=ctx.guild.id)
        if not rows:
            await ctx.reply("No tag usage recorded yet.")
            return
        await ctx.reply("\n".join(f"{index}. `{row['name']}`: **{row['count']}** uses" for index, row in enumerate(rows, start=1)))

    @tag.command(name="nsfw", aliases=["mark-nsfw"])
    async def mark_tag_nsfw(self, ctx: commands.Context[Parrot], *, name: str) -> None:
        """Mark a tag as NSFW."""
        assert ctx.guild is not None

        tag_name = await self.bot.database.get_tag_name(guild_id=ctx.guild.id, name_or_alias=name)
        if tag_name is None:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        marked = await self.bot.database.mark_tag_nsfw(
            guild_id=ctx.guild.id,
            name=tag_name,
            creator_id=ctx.author.id,
            is_admin=isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator,
        )
        if marked:
            await ctx.reply(f"Tag `{tag_name}` marked as NSFW.")
        else:
            await ctx.reply("Only the tag owner or a server administrator can mark this tag as NSFW.")

    @tag.command(name="edit", aliases=["update"])
    async def edit_tag(self, ctx: commands.Context[Parrot], name: str, *, new_content: Annotated[str, commands.clean_content]) -> None:
        """Edit a tag's content."""
        assert ctx.guild is not None

        exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{name}`")
            return

        await self.bot.database.edit_tag_content(guild_id=ctx.guild.id, creator_id=ctx.author.id, name=name, content=new_content)
        await ctx.reply(f"Tag `{name}` updated successfully.")

    @tag.group(name="alias", invoke_without_command=True)
    async def tag_alias(self, ctx: commands.Context[Parrot]) -> None:
        """Manage tag aliases."""
        await ctx.send_help(ctx.command)

    @tag_alias.command(name="add", aliases=["create", "new"])
    async def add_tag_alias(self, ctx: commands.Context[Parrot], tag_name: str, alias: str) -> None:
        """Add an alias to a tag."""
        assert ctx.guild is not None

        exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{tag_name}`")
            return

        alias_exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=alias)
        if alias_exists:
            await ctx.reply(f"Alias `{alias}` already exists as a tag or alias.")
            return

        await self.bot.database.add_tag_alias(guild_id=ctx.guild.id, name=tag_name, alias=alias)
        await ctx.reply(f"Alias `{alias}` added to tag `{tag_name}` successfully.")

    @tag_alias.command(name="remove", aliases=["delete", "rm", "del"])
    async def remove_tag_alias(self, ctx: commands.Context[Parrot], tag_name: str, alias: str) -> None:
        """Remove an alias from a tag."""
        assert ctx.guild is not None

        exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=tag_name)
        if not exists:
            await ctx.reply(f"No tag found with the name: `{tag_name}`")
            return

        alias_exists = await self.bot.database.is_tag_present(guild_id=ctx.guild.id, name_or_alias=alias)
        if not alias_exists:
            await ctx.reply(f"No alias found with the name: `{alias}`")
            return

        await self.bot.database.remove_tag_alias(
            guild_id=ctx.guild.id,
            creator_id=ctx.author.id,
            name=tag_name,
            alias=alias,
            is_admin=isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator,
        )
        await ctx.reply(f"Alias `{alias}` removed from tag `{tag_name}` successfully.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Tags(bot))
