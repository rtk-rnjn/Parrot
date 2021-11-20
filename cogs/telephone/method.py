from __future__ import annotations

from utilities.database import parrot_db, telephone_update

collection = parrot_db['telephone']

import asyncio, discord, random, time
from discord.ext import commands

cd_mapping = commands.CooldownMapping.from_cooldown(
    5, 5, commands.BucketType.channel)


async def dial(bot, ctx, server, reverse=False):
    if server.id == ctx.guild.id:
        return await ctx.send(f"Can't make a self call")
    number = server.id
    channel = ctx.channel
    self_guild = await collection.find_one({'_id': ctx.guild.id})
    if not self_guild:
        return await ctx.send(
            f"{ctx.author.mention} no telephone line channel is set for this server, ask your Server Manager to fix this."
        )
    target_guild = await collection.find_one({'_id': number})
    if not target_guild:
        return await ctx.send(
            f"{ctx.author.mention} no telephone line channel is set for the **{number}** server, or the number you entered do not match with any other server!"
        )

    if target_guild['is_line_busy']:
        return await ctx.send(
            f"Can not make a connection to **{number} ({bot.get_guild(target_guild['_id']).name})**. Line busy!"
        )

    target_channel = bot.get_channel(target_guild['channel'])
    if not target_channel:
        return await ctx.send(
            "Calling failed! Possible reasons: `Channel deleted`, missing `View Channels` permission."
        )

    if (target_guild['_id']
            in self_guild['blocked']) or (self_guild['_id']
                                          in target_guild['blocked']):
        return await ctx.send(
            f'Calling failed! Possible reasons: They blocked You, You blocked Them.'
        )

    await ctx.send(
        f"Calling to **{number} ({bot.get_guild(target_guild['_id']).name})** ... Waiting for the response ..."
    )

    await target_channel.send(
        f"**Incoming call from {ctx.guild.id}. {ctx.guild.name} ...**\n`pickup` to pickup | `hangup` to reject"
    )
    try:
        temp_message = target_channel.send(
            f'{bot.get_guild(target_guild["_id"]).get_role(target_guild["pingrole"]).mention} {bot.get_user(target_guild["memberping"]).mention}'
        )
        await temp_message.delete()
    except Exception:
        pass

    def check(m):
        return (m.content.lower() in ("pickup", "hangup")) and (m.channel == channel or m.channel == target_channel) and (not m.author.bot)

    try:
        _talk = await bot.wait_for('message', check=check, timeout=60)
    except Exception:
        await asyncio.sleep(0.5)
        await target_channel.send(
            f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds"
        )
        await ctx.send(
            f"Line disconnected from **{number} ({bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds"
        )

        await telephone_update(ctx.guild.id, 'is_line_busy', False)
        await telephone_update(number, 'is_line_busy', False)
        return

    if _talk.content.lower() == 'hangup':
        await ctx.send(
            f'Disconnected. From **{_talk.author.guild.name} ({_talk.author.guild.id})**'
        )
        await target_channel.send(
            f'Disconnected. From **{_talk.author.guild.name} ({_talk.author.guild.id})**'
        )
        await telephone_update(ctx.guild.id, 'is_line_busy', False)
        await telephone_update(number, 'is_line_busy', False)
        return

    elif _talk.content.lower() == 'pickup':
        await ctx.send(
            f"**Connected. Say {random.choice(['hi', 'hello', 'heya'])}**")
        await target_channel.send(
            f"**Connected. Say {random.choice(['hi', 'hello', 'heya'])}**")

        await telephone_update(ctx.guild.id, 'is_line_busy', True)
        await telephone_update(number, 'is_line_busy', True)
        ini = time.time() + 120
        while True:

            def check(m):
                if m.author.bot:
                    return
                if (m.channel == target_channel) or (m.channel == channel):
                    return True

            try:
                talk_message = await bot.wait_for('message',
                                                  check=check,
                                                  timeout=60.0)
            except Exception:
                await asyncio.sleep(0.5)
                await target_channel.send(
                    f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds"
                )
                await ctx.send(
                    f"Line disconnected from **{number} ({bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds"
                )

                await telephone_update(ctx.guild.id, 'is_line_busy', False)
                await telephone_update(number, 'is_line_busy', False)
                return

            bucket = cd_mapping.get_bucket(talk_message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                await target_channel.send("Disconnect due to channel spam")
                await ctx.send("Disconnect due to channel spam")
                return

            if talk_message.content.lower() == 'hangup':
                await telephone_update(ctx.guild.id, 'is_line_busy', False)
                await telephone_update(number, 'is_line_busy', False)
                await ctx.send(f'Disconnected')
                await target_channel.send(f'Disconnected')
                return
            TALK = discord.utils.escape_mentions(talk_message.content[:1000:])
            if reverse:
                TALK = discord.utils.escape_mentions(
                    "".join(reversed(talk_message.content[:1000:]))
                )  # this is imp, cause people can bypass so i added discord.utils

            if talk_message.channel == target_channel:
                await channel.send(
                    f"**{talk_message.author.name}#{talk_message.author.discriminator}** {TALK}"
                )

            elif talk_message.channel == channel:
                await target_channel.send(
                    f"**{talk_message.author.name}#{talk_message.author.discriminator}** {TALK}"
                )
            if ini - time.time() <= 60:
                await channel.send(
                    f'Disconnected. Call duration reached its maximum limit')
                await target_channel.send(
                    f'Disconnected. Call duration reached its maximum limit')
                await telephone_update(ctx.guild.id, 'is_line_busy', False)
                await telephone_update(number, 'is_line_busy', False)
                return
