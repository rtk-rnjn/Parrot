from discord.ext import commands
from pymongo import MongoClient
from os import environ

my_secret = environ['pass']

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

db = cluster["premium"]

collection_pr_user = db["premium_user"]
collection_pre_guild = db["premium_guild"]


def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)


def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 741614468546560092  # !! Ritik Ranjan [*.*]#9230

    return commands.check(predicate)


def is_user_premium():
    def predicate(ctx):
        data = list(
            collection_pr_user.find({
                "_id": ctx.guild.id
            }).distinct('_id'))
        if ctx.guild.id in data:
            return commands.cooldown(0, 0, commands.BucketType.member)
        else:
            return commands.cooldown(1, 2, commands.BucketType.member)

    return commands.check(predicate)


def mod_premium():
    def predicate(ctx):
        data = list(
            collection_pre_guild.find({
                "_id": ctx.guild.id
            }).distinct('_id'))
        if ctx.guild.id in data:
            return commands.cooldown(0, 0, commands.BucketType.guild)
        else:
            return commands.cooldown(3, 30, commands.BucketType.guild)

    return commands.check(predicate)
