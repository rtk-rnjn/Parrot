from __future__ import annotations

from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.features.baseclass import Feature

from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot, Context
    from pymongo.collection import Collection as PyMongoCollection
    from pymongo.results import DeleteResult

try:
    import orjson as json
except ImportError:
    import json

class MongoFeature(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """
    Feature that adds a mongo command to jishaku
    """

    @Feature.Command(parent="jsk", name="mongofind", aliases=["mf", "mongof"])
    async def jsk_mongo(self, ctx: Context[Parrot], db: str, collection: str, *, filter: str):
        """
        Runs a mongo command. Syntax: `jsk mongofind <db> <collection> <query>`
        """
    
        col: PyMongoCollection = ctx.bot.mongo[db][collection]
        result = await col.find_one(json.loads(filter))
        if result is None:
            await ctx.send("No results found.")
        else:
            await ctx.send(f"```json\n{json.dumps(result, option=json.OPT_INDENT_2)}```")

    @Feature.Command(parent="jsk", name="mongodelete", aliases=["md", "mongod"])
    async def jsk_mongo_delete(self, ctx: Context[Parrot], db: str, collection: str, *, filter: str):
        """
        Runs a mongo command. Syntax: `jsk mongofind <db> <collection> <query>`
        """

        col: PyMongoCollection = ctx.bot.mongo[db][collection]
        result: DeleteResult = await col.delete_one(json.loads(filter))
        if result.deleted_count == 0:
            await ctx.send("No results found.")
        else:
            await ctx.send(f"Deleted {result.deleted_count} documents.")