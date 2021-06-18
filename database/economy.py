import os
import pymongo

from pymongo import MongoClient

my_secret = os.environ['pass']

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["economy"]
collection = db["global_economy"]


async def ge_update(user_id: int, start_bank: int, start_wallet: int, items):
    pre_post = {"_id": user_id}
    post = {'bank': start_bank, 'wallet': start_wallet, "items": items}

    try:
        collection.update_one(pre_post, {"$set": post})
        return "OK"
    except Exception as e:
        return str(e)


async def ge_on_join(user_id: int):
    post = {'_id': user_id, 'bank': 0, 'wallet': 400, "items": []}

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)

