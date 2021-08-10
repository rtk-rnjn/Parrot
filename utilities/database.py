from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

parrot_db = cluster['parrot_db']
economy_db = cluster['economy']
msg_db = cluster['msg_db']
tags = cluster['tags']


async def cmd_increment(cmd: str):
    collection = parrot_db['cmd_count']
    data = collection.find_one({'_id': cmd})
    if not data:
        return collection.insert_one({'_id': cmd, 'count': 1})
    collection.update_one({'_id': cmd}, {'$inc': {'count': 1}})


async def ge_update(user_id: int, bank: int, wallet: int):
    collection = economy_db['global_economy']
    if not collection.find_one({'_id': user_id}):
        collection.insert_one({'_id': user_id, 'bank': 0, 'wallet': 400})

    collection.update_one({"_id": user_id},
                          {"$set": {
                              'bank': bank,
                              'wallet': wallet
                          }})


async def gchat_update(guild_id: int, post: dict):
    collection = parrot_db['global_chat']
    if not collection.find_one({'_id': guild_id}):
        collection.insert_one({'_id': guild_id})

    collection.update_one({'_id': guild_id}, {'$set': post})


async def msg_increment(guild_id: int, user_id: int):
    collection = parrot_db[f'{guild_id}']
    data = collection.find_one({'_id': user_id})
    if not data: collection.insert_one({'_id': user_id, 'count': 1})
    pre_post = {'_id': user_id}
    collection.update_one(pre_post, {'$inc': {'count': 1}})


async def telephone_update(guild_id: int, event: str, value):
    collection = parrot_db["telephone"]
    if not collection.find_one({'_id': guild_id}):
        collection.insert_one({'_id': guild_id})

    collection.update_one({'_id': guild_id}, {"$set": {event: value}})


async def ticket_update(guild_id: int, post):
    collection = parrot_db["ticket"]
    if not collection.find_one({'_id': guild_id}):
        collection.insert_one({
            '_id': guild_id,
            "ticket-counter": 0,
            "valid-roles": [],
            "pinged-roles": [],
            "ticket-channel-ids": [],
            "verified-roles": [],
            "message_id": None,
            "log": None,
            "category": None,
            "channel_id": None
        })

    collection.update_one({'_id': guild_id}, {"$set": post})


async def guild_update(guild_id: int, post: dict):
    collection = parrot_db['server_config']
    if not collection.find_one({'_id': guild_id}):
        collection.insert_one({
            '_id': guild_id,
            'prefix': '$',
            'mod_role': None,
            'action_log': None,
            'mute_role': None,
        })

    collection.update_one({'_id': guild_id}, {"$set": post})


async def guild_join(guild_id: int):
    collection = parrot_db['server_config']
    post = {
        '_id': guild_id,
        'prefix': '$',
        'mod_role': None,
        'action_log': None,
        'mute_role': None,
    }
    collection.insert_one(post)
    collection = parrot_db['global_chat']
    post = {
        '_id': guild_id,
        'channel_id': None,
        'webhook': None,
        'ignore-role': None,
    }
    collection.insert_one(post)
    collection = parrot_db["telephone"]

    post = {
        "_id": guild_id,
        "channel": None,
        "pingrole": None,
        "is_line_busy": False,
        "memberping": None,
        "blocked": []
    }

    collection.insert_one(post)
    collection = parrot_db["ticket"]
    post = {
        "_id": guild_id,
        "ticket-counter": 0,
        "valid-roles": [],
        "pinged-roles": [],
        "ticket-channel-ids": [],
        "verified-roles": [],
        "message_id": None,
        "log": None,
        "category": None,
        "channel_id": None
    }

    collection.insert_one(post)


async def guild_remove(guild_id: int):
    collection = parrot_db['server_config']
    collection.delete_one({'_id': guild_id})
    collection = parrot_db[f'{guild_id}']
    collection.drop()
    collection = parrot_db['global_chat']
    collection.delete_one({'_id': guild_id})
    collection = parrot_db["telephone"]
    collection.delete_one({'_id': guild_id})
    collection = parrot_db["ticket"]
    collection.delete_one({'_id': guild_id})
