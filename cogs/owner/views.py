from __future__ import annotations

import json

import discord
from core import Context, Parrot
from utilities.paginator import PaginationView


class NitroView(discord.ui.View):
    def __init__(self, ctx: Context) -> None:
        super().__init__(timeout=None)
        self.ctx: Context = ctx
        self.bot: Parrot = ctx.bot

    @discord.ui.button(
        custom_id="fun (nitro)",
        label="\N{BRAILLE PATTERN BLANK}" * 16 + "Claim" + "\N{BRAILLE PATTERN BLANK}" * 16,
        style=discord.ButtonStyle.green,
    )
    async def func(self, interaction: discord.Interaction, button: discord.ui.Button):
        i = discord.Embed()
        i.set_image(url="https://c.tenor.com/x8v1oNUOmg4AAAAd/rickroll-roll.gif")
        await interaction.response.send_message("https://imgur.com/NQinKJB", ephemeral=True)

        button.disabled = True
        button.style = discord.ButtonStyle.grey
        button.label = ("\N{BRAILLE PATTERN BLANK}" * 16 + "Claimed" + "\N{BRAILLE PATTERN BLANK}" * 16,)  # type: ignore

        ni: discord.Embed = discord.Embed(
            title="You received a gift, but...",
            description="The gift link has either expired or has been\nrevoked.",
        )
        ni.set_thumbnail(url="https://i.imgur.com/w9aiD6F.png")
        try:
            await interaction.message.edit(embed=ni, view=self)  # type: ignore
        except AttributeError:
            pass


class MongoCollectionView(discord.ui.View):
    message: discord.Message | None = None

    def __init__(self, *, timeout: float = 20, db: str, collection: str, ctx: Context) -> None:
        super().__init__(timeout=timeout)
        self.collection = collection
        self.db = db
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:
        return await self.ctx.bot.is_owner(interaction.user)

    @discord.ui.button(label="Paginate", style=discord.ButtonStyle.blurple, emoji="\N{BOOKS}")
    async def paginate(self, interaction: discord.Interaction, button: discord.ui.Button):
        assert self.message is not None
        await interaction.response.defer()

        collection = self.ctx.bot.mongo[self.db][self.collection]

        view = PaginationView([])
        view._str_prefix = "```json\n"
        view._str_suffix = "\n```"
        await view.start(self.ctx)

        index = 0
        async for data in collection.find():
            _id = data.pop("_id")
            data["_id"] = str(_id)

            data = json.dumps(data, indent=4).split("\n")
            new_data = []
            for ind, line in enumerate(data):
                if ind == 20:
                    break
                new_data.append(line)
            new_data.append("...")

            await view.add_item_to_embed_list("\n".join(new_data))

            if index == 100:
                break

            index += 1
        await view._update_message()

    async def disable_all(self):
        assert self.message is not None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                child.style = discord.ButtonStyle.grey
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.disable_all()


class MongoViewSelect(discord.ui.Select["MongoView"]):
    def __init__(self, ctx: Context, **kwargs) -> None:
        self.db_name = kwargs.pop("db_name", "")
        super().__init__(min_values=1, max_values=1, **kwargs)
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None and self.view.message is not None

        await interaction.response.defer()
        embed = await self.build_embed(self.ctx, self.db_name, self.values[0])

        view = MongoCollectionView(collection=self.values[0], ctx=self.ctx, db=self.db_name)
        view.message = await self.view.message.edit(
            embed=embed,
            view=view,
        )
        self.view.stop()

    @staticmethod
    async def build_embed(ctx: Context, db_name: str, collection_name: str) -> discord.Embed:
        db = ctx.bot.mongo[db_name][collection_name]
        document_count = await db.count_documents({})
        full_name = f"{db_name}.{collection_name}"
        return (
            discord.Embed(title="MongoDB - Collection - Lookup")
            .add_field(name="Total documents", value=document_count)
            .add_field(name="Full Name", value=full_name)
            .add_field(name="Database", value=db_name)
        )


class MongoView(discord.ui.View):
    def __init__(self, ctx: Context, *, timeout: float | None = 20, **kwargs) -> None:
        super().__init__(timeout=timeout, **kwargs)

        self.ctx = ctx

    async def init(self):
        names: list[str] = await self.ctx.bot.mongo.list_database_names()
        for name in ("admin", "local", "config"):
            try:
                names.remove(name)
            except ValueError:
                pass

        def to_emoji(c):
            return chr(127462 + c)

        embed = discord.Embed(
            title="MongoDB  - Database - Lookup",
        )

        for i, name in enumerate(names):
            embed.add_field(name=f"{to_emoji(i)} {name}", value="\u200b")
            collections = await self.ctx.bot.mongo[name].list_collection_names()
            if not collections:
                continue

            options = [
                discord.SelectOption(
                    label=collection,
                    value=collection,
                    emoji=chr(0x1F1E6 + j),
                )
                for j, collection in enumerate(collections)
            ]
            self.add_item(
                MongoViewSelect(
                    self.ctx,
                    options=options[:25],
                    placeholder=f"Database - {name}",
                    db_name=name,
                    row=i,
                ),
            )

        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:
        return await self.ctx.bot.is_owner(interaction.user)

    async def on_timeout(self) -> None:
        if hasattr(self, "message"):
            for child in self.children:
                if isinstance(child, discord.ui.Select | discord.ui.Button):
                    child.disabled = True
