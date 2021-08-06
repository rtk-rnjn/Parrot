from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["msg_db"]


async def increment(guild_id: int, user_id: int):
    collection = db[f'{guild_id}']
    data = collection.find_one({'_id': user_id})
    if not data: collection.insert_one({'_id': user_id, 'count': 1})
    pre_post = {'_id': user_id}
    collection.update_one(pre_post, {'$inc': {'count': 1}})
 

async def guild_remove(guild_id: int):
    
        collection = db[f'{guild_id}']
        collection.drop()
    
