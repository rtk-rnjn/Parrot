from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["premium"]
collection_guild = db["premium_guild"]


async def premium_add_guild(guild_id: int):
    post = {
        "_id": guild_id,
    }

    collection_guild.insert_one(post)



async def premium_del_guild(guild_id: int):
    post = {
        "_id": guild_id,
    }

    collection_guild.delete_one(post)
     

collection_user = db["premium_user"]


async def premium_add_user(user_id: int):
    post = {
        "_id": user_id,
    }

    collection_user.insert_one(post)
    


async def premium_del_user(user_id: int):
    post = {
        "_id": user_id,
    }

    collection_user.delete_one(post)
    
