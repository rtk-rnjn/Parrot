from pymongo import MongoClient
from utilities.config import my_secret
import random


cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

db = cluster['parrot_db']
collection = db['giveaway']


async def create_giveaway(message_id, channel_id, winner, required_role,
                          required_msg, ends_at, active):
    post = {
        '_id': message_id,
        'channel_id': channel_id,
        'winner': winner,
        'required_role': required_role,
        'required_msg': required_msg,
        'ends_at': ends_at,
        'user': [],
        'active': active
    }
    collection.insert_one(post)


async def end_giveaway(bot, message_id, winner):
    data = collection.find_one({'_id': message_id})
    if not data: return
    channel = bot.get_channel(data['channel_id'])
    msg = await channel.fetch_message(message_id)
    if not msg: return
    winner = winner or data['winner']
    for reaction in msg.reactions:
        if reaction.emoji == "🎉":
            #index = list(msg.reactions).index(reaction)
            break
    users = list(
        set((await reaction.users().flatten()) +
            [channel.guild.get_member(user) for user in data['user']]))
    from_users = []
    for user in users:
        will = await can_win_giveaway(message_id, channel.id, user.id,
                                      channel.guild, user)
        if will: from_users.apend(user)
        collection.update_one(
            {'_id': message_id},
            {"$set": {
                'user': [user.id for user in from_users]
            }})
        collection.update_one({'_id': message_id}, {'$set': {'active': False}})

    users.remove(bot.user)
    winners = random.sample(from_users, winner)

    await msg.reply(f"{', '.join(winners.mention)} you won {data['prize']}")
    for winner in winners:
        await remove_user(message_id, winner.id)


async def drop_giveaway(message_id):
    post = {'_id': message_id}
    collection.delete_one(post)


async def can_win_giveaway(message_id, channel_id, user_id, guild, member):
    data = collection.find_one({'_id': message_id})
    col = db[f'{guild.id}']
    msg_user = col.find_one({'_id': member.id})
    if not data: return
    if (guild.get_role(data['required_role']) in member.roles
            and data['required_msg'] >= msg_user['count']):
        return True
    else:
        return False


async def add_user(message_id, user_id):
    post = {'_id': message_id}
    collection.update_one(post, {'$push': {'user': user_id}})


async def remove_user(message_id, user_id):
    post = {'_id': message_id}
    collection.update_one(post, {"$pull": {'user': user_id}})
