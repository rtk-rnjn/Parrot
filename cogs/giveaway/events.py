from core import Parrot, Cog
from cogs.giveaway.method import collection, add_user, can_win_giveaway, remove_user


class ReactionGiveaway(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.emoji.name == ':tada:': return
        message_id = payload.message_id
        channel_id = payload.channel_id
        data = collection.find_one({'_id': message_id})
        member = payload.member
        if not data: return
        will_win = await can_win_giveaway(message_id, channel_id, member.id,
                                          member.guild, member)
        if will_win:
            await add_user(message_id, member.id)
            try:
                channel = self.bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                await message.remove_reaction(":tada:", member)
            except Exception:
                pass

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.emoji.name == ':tada:': return
        message_id = payload.message_id
        data = collection.find_one({'_id': message_id})
        member = payload.member
        if not data: return
        await remove_user(message_id, member.id)


def setup(bot):
    bot.add_cog(ReactionGiveaway(bot))
