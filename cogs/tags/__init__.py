from __future__ import annotations

import cogs.tags.method as mt
import discord
from core import Cog, Context, Parrot
from discord.ext import commands


class Tags(Cog):
    """For making the tags. Tags are like the snippets. You can create tags and use them later."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{TICKET}")

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def tag(self, ctx: Context, *, tag: str = None):
        """Tag management, or to show the tag.

        **Examples:**
        - `[p]tag [tag_name]`
        """
        if not ctx.invoked_subcommand and tag is not None:
            await mt._show_tag(
                self.bot,
                ctx,
                tag,
                ctx.message.reference.resolved if ctx.message.reference else None,  # type: ignore
            )
        else:
            await self.bot.invoke_help_command(ctx)

    @tag.command(name="create", aliases=["add", "new", "make", "mk"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_create(self, ctx: Context, tag: str, *, text: str):
        """To create tag. All tag have unique name.

        **Examples:**
        - `[p]tag create tag_name tag_text`

        **Note:**
        - If name has whitespace, then you must use double quotes around the name.
            - `[p]tag create "tag name" tag_text with more characters`
        """
        await mt._create_tag(self.bot, ctx, tag, text)

    @tag.command(name="delete", aliases=["del", "rm"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_delete(self, ctx: Context, *, tag: str):
        """To delete tag. You must own the tag to delete.

        **Examples:**
        - `[p]tag delete tag_name`

        ~~**Note:**~~
        ~~- If name has whitespace, then you must use double quotes around the name.~~
            ~~- `[p]tag delete "tag name"`~~
        """
        await mt._delete_tag(self.bot, ctx, tag)

    @tag.command(name="editname", aliases=["rename", "edit-name", "edit_name"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_name(self, ctx: Context, tag: str, *, name: str):
        """To edit the tag name. You must own the tag to edit.

        **Examples:**
        - `[p]tag editname tag_name new_tag_name`

        **Note:**
        - If name has whitespace, then you must use double quotes around the name.
            - `[p]tag editname "tag name" "new tag name"`
        """
        await mt._name_edit(self.bot, ctx, tag, name)

    @tag.command(name="edittext", aliases=["edit-text", "edit_text"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_edit_text(self, ctx: Context, tag: str, *, text: str):
        """To edit the tag text. You must own the tag to edit.

        **Examples:**
        - `[p]tag edittext tag_name new_tag_text`

        **Note:**
        - If name has whitespace, then you must use double quotes around the name.
            - `[p]tag edittext "tag name" "new tag text"`
        """
        await mt._text_edit(self.bot, ctx, tag, text)

    @tag.command(name="owner", aliases=["info", "details", "whois", "detail"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_owner(self, ctx: Context, *, tag: str):
        """To check the tag details.

        **Examples:**
        - `[p]tag owner tag_name`
        """
        await mt._view_tag(self.bot, ctx, tag)

    @tag.command(name="snipe", aliases=["steal", "claim", "take"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_claim(self, ctx: Context, *, tag: str):
        """To claim the ownership of the tag, if the owner of the tag left the server.

        **Examples:**
        - `[p]tag snipe tag_name`
        """
        await mt._claim_owner(self.bot, ctx, tag)

    @tag.command(name="togglensfw", aliases=["nsfw", "tnsfw"])
    @commands.bot_has_permissions(embed_links=True)
    async def toggle_nsfw(self, ctx: Context, *, tag: str):
        """To enable/disable the NSFW of a Tag.

        **Examples:**
        - `[p]tag togglensfw tag_name`
        """
        await mt._toggle_nsfw(self.bot, ctx, tag)

    @tag.command(name="give", aliases=["transfer", "share"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_tranfer(self, ctx: Context, tag: str, *, member: discord.Member):
        """To transfer the ownership of tag you own to other member.

        **Examples:**
        - `[p]tag give tag_name @member`
        - `[p]tag give tag_name member_id`

        **Note:**
        - If name has whitespace, then you must use double quotes around the name.
            - `[p]tag give "tag name" @member`
            - `[p]tag give "tag name" member_id`
        """
        await mt._transfer_owner(self.bot, ctx, tag, member)

    @tag.command(name="all", aliases=["list", "show", "ls"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_all(self, ctx: Context):
        """To show all tags.

        **Examples:**
        - `[p]tag all`
        """
        await mt._show_all_tags(self.bot, ctx)

    @tag.command(name="mine", aliases=["my", "owned", "own"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_mine(self, ctx: Context):
        """To show those tag which you own.

        **Examples:**
        - `[p]tag mine`
        """
        await mt._show_tag_mine(self.bot, ctx)

    @tag.command(name="raw", aliases=["source", "code"])
    @commands.bot_has_permissions(embed_links=True)
    async def tag_raw(self, ctx: Context, *, tag: str):
        """To show the tag in raw format.

        **Examples:**
        - `[p]tag raw tag_name`
        """
        await mt._show_raw_tag(self.bot, ctx, tag)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Tags(bot))
