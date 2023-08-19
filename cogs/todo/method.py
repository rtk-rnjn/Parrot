import discord
from core import Context, Parrot


async def _create_todo(bot: Parrot, ctx: Context, name: str, text: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        await ctx.reply(f"{ctx.author.mention} `{name}` already exists as your TODO list")
    else:
        await collection.insert_one(
            {
                "id": name,
                "text": text,
                "time": int(discord.utils.utcnow().timestamp()),
                "deadline": None,
                "msglink": ctx.message.jump_url,
            },
        )
        await ctx.reply(f"{ctx.author.mention} created as your TODO list")


async def _set_timer_todo(bot: Parrot, ctx: Context, name: str, timestamp: float):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        post = {"deadline": timestamp}
        try:
            await ctx.author.send(
                f"You will be reminded for your task named **{name}** here at <t:{int(timestamp)}>. "
                f"To delete your reminder consider typing.\n```\n{ctx.clean_prefix}remind delete {ctx.message.id}```",
                view=ctx.send_view(),
            )
        except Exception as e:
            return await ctx.error(f"{ctx.author.mention} seems that your DM are blocked for the bot. Error: {e}")
        finally:
            await collection.update_one({"_id": name}, {"$set": post})
            await bot.create_timer(
                _event_name="todo",
                expires_at=timestamp,
                created_at=ctx.message.created_at.timestamp(),
                message=ctx.message,
                content=f"you had set TODO reminder for your task named `{name}`",
                dm_notify=True,
                is_todo=True,
            )
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _update_todo_name(bot: Parrot, ctx: Context, name: str, new_name: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        if _ := await collection.find_one({"id": new_name}):
            await ctx.reply(f"{ctx.author.mention} `{new_name}` already exists as your TODO list")
        else:
            await collection.update_one({"id": name}, {"$set": {"id": new_name}})
            await ctx.reply(f"{ctx.author.mention} name changed from `{name}` to `{new_name}`")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _update_todo_text(bot: Parrot, ctx: Context, name: str, text: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        await collection.update_one({"id": name}, {"$set": {"text": text}})
        await ctx.reply(f"{ctx.author.mention} TODO list of name `{name}` has been updated")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _list_todo(bot: Parrot, ctx: Context) -> None:
    collection = ctx.user_collection
    entries: list[str] = []
    async for data in collection.find({}):
        entries.append(f"({data['msglink']}) {data['id']}")
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you do not have task to do")


async def _show_todo(bot: Parrot, ctx: Context, name: str):
    collection = ctx.user_collection
    if data := await collection.find_one({"id": name}):
        await ctx.reply(f"> **{data['id']}**\n\nDescription: {data['text']}\n\nCreated At: <t:{data['time']}>")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _delete_todo(bot: Parrot, ctx: Context, name: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        await collection.delete_one({"id": name})
        await ctx.reply(f"{ctx.author.mention} delete `{name}` task")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")
