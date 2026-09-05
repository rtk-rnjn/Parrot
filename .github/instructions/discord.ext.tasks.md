### Execute logic during task cancellation

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Checks if a task is being cancelled using is_being_cancelled to perform final cleanup or data flushing.

```python
from discord.ext import tasks, commands
import asyncio


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._batch = []
        self.lock = asyncio.Lock()
        self.bulker.start()

    async def cog_unload(self):
        self.bulker.cancel()

    async def do_bulk(self):
        # bulk insert data here
        ...

    @tasks.loop(seconds=10.0)
    async def bulker(self):
        async with self.lock:
            await self.do_bulk()

    @bulker.after_loop
    async def on_bulker_cancel(self):
        if self.bulker.is_being_cancelled() and len(self._batch) != 0:
            # if we're cancelled and we have some data left...
            # let's insert it to our database
            await self.do_bulk()
```

--------------------------------

### Setup for multiple daily task times

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Initializes the imports and timezone configuration required for scheduling tasks at multiple times per day.

```python
import datetime
from discord.ext import commands, tasks

utc = datetime.timezone.utc
```

--------------------------------

### Run a task at a specific time daily

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Schedules a task to run at a specific time of day using the time parameter with datetime.time.

```python
import datetime
from discord.ext import commands, tasks

utc = datetime.timezone.utc

# If no tzinfo is given then UTC is assumed.
time = datetime.time(hour=8, minute=30, tzinfo=utc)


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.my_task.start()

    def cog_unload(self):
        self.my_task.cancel()

    @tasks.loop(time=time)
    async def my_task(self):
        print("My task is running!")
```

--------------------------------

### Create a simple background task in a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Demonstrates a basic loop running every 5 seconds within a Cog, including start and cancellation logic.

```python
from discord.ext import tasks, commands


class MyCog(commands.Cog):
    def __init__(self):
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=5.0)
    async def printer(self):
        print(self.index)
        self.index += 1
```

--------------------------------

### Loop a specific number of times

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Configures a task to run a fixed number of times using the count parameter and executes cleanup code after completion.

```python
from discord.ext import tasks
import discord


@tasks.loop(seconds=5.0, count=5)
async def slow_count():
    print(slow_count.current_loop)


@slow_count.after_loop
async def after_slow_count():
    print("done!")


class MyClient(discord.Client):
    async def setup_hook(self):
        slow_count.start()
```

--------------------------------

### Send Typing Indicator

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates how to use the typing context manager to indicate activity during long-running tasks.

```python
async with channel.typing():
    # simulate something heavy
    await asyncio.sleep(20)

await channel.send("Done!")
```

```python
await channel.typing()
# Do some computational magic for about 10 seconds
await channel.send("Done!")
```

--------------------------------

### AudioSource.cleanup()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Performs necessary clean-up tasks, such as clearing buffer data or processes after audio playback is finished.

```APIDOC
## cleanup()

### Description
Called when clean-up is needed to be done. Useful for clearing buffer data or processes after it is done playing audio.
```

--------------------------------

### Client.setup_hook

Source: https://discordpy.readthedocs.io/en/latest/api.html

An asynchronous hook for performing setup tasks after login but before connecting to the websocket.

```APIDOC
## setup_hook()

### Description
A coroutine to be called to setup the bot. Overwrite this coroutine to perform asynchronous setup after the bot is logged in but before it has connected to the Websocket.
```

--------------------------------

### Handle exceptions during reconnects

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Uses add_exception_type to specify which exceptions should be ignored or handled during task execution.

```python
import asyncpg
from discord.ext import tasks, commands


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = []
        self.batch_update.add_exception_type(asyncpg.PostgresConnectionError)
        self.batch_update.start()

    def cog_unload(self):
        self.batch_update.cancel()

    @tasks.loop(minutes=5.0)
    async def batch_update(self):
        async with self.bot.pool.acquire() as con:
            # batch update here...
            pass
```

--------------------------------

### Wait for bot readiness before starting a loop

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Uses the before_loop decorator to ensure the bot is fully connected before the task begins execution.

```python
from discord.ext import tasks, commands


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.index = 0
        self.bot = bot
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=5.0)
    async def printer(self):
        print(self.index)
        self.index += 1

    @printer.before_loop
    async def before_printer(self):
        print("waiting...")
        await self.bot.wait_until_ready()
```

--------------------------------

### Implement setup and teardown

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

Define setup and teardown coroutines to handle initialization and cleanup logic when an extension is loaded or unloaded.

```python
async def setup(bot):
    print("I am being loaded!")


async def teardown(bot):
    print("I am being unloaded!")
```

--------------------------------

### await edit(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the scheduled event. This is a coroutine.

```APIDOC
## await edit(**kwargs)

### Description
Edits the scheduled event. You must have manage_events permission to do this.

### Parameters
- **name** (str) - Optional - The name of the scheduled event.
- **description** (str) - Optional - The description of the scheduled event.
- **channel** (Optional[Snowflake]) - Optional - The channel to put the scheduled event in.
- **start_time** (datetime.datetime) - Optional - The time that the scheduled event will start.
- **end_time** (Optional[datetime.datetime]) - Optional - The time that the scheduled event will end.
- **privacy_level** (PrivacyLevel) - Optional - The privacy level of the scheduled event.
- **entity_type** (EntityType) - Optional - The new entity type.
- **status** (EventStatus) - Optional - The new status of the scheduled event.
- **image** (Optional[bytes]) - Optional - The new image of the scheduled event.
- **location** (str) - Optional - The new location of the scheduled event.
- **reason** (Optional[str]) - Optional - The reason for editing the scheduled event.
```

--------------------------------

### Iterate over Entitlements

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates how to asynchronously iterate over application entitlements using the entitlements method.

```python
async for entitlement in client.entitlements(limit=100):
    print(entitlement.user_id, entitlement.ends_at)
```

```python
entitlements = [entitlement async for entitlement in client.entitlements(limit=100)]
# entitlements is now a list of Entitlement...
```

--------------------------------

### await add_tags(*tags, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds the given forum tags to a thread.

```APIDOC
## await add_tags(*tags, reason=None)

### Description
Adds the given forum tags to a thread. The parent channel must be a ForumChannel.

### Parameters
- **tags** (abc.Snowflake) - Required - An argument list of abc.Snowflake representing a ForumTag to add.
- **reason** (Optional[str]) - Optional - The reason for adding these tags.
```

--------------------------------

### Integration.sync

Source: https://discordpy.readthedocs.io/en/latest/api.html

Syncs the integration. Requires manage_guild permission.

```APIDOC
## await sync()

### Description
Syncs the integration. You must have `manage_guild` to do this.

### Raises
- **Forbidden** - You do not have permission to sync the integration.
- **HTTPException** - Syncing the integration failed.
```

--------------------------------

### Update Intents Iteration Logic

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Adjust iteration over Intents to account for the renaming of emojis to emojis_and_stickers.

```python
# before
friendly_names = {
    ...,
    'emojis': 'Emojis Intent',
    ...,
}
for name, value in discord.Intents.all():
    print(f'{friendly_names[name]}: {value}')

# after
friendly_names = {
    ...,
    'emojis_and_stickers': 'Emojis Intent',
    ...,
}
for name, value in discord.Intents.all():
    print(f'{friendly_names[name]}: {value}')
```

--------------------------------

### entitlements()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of the application's entitlements.

```APIDOC
## entitlements()

### Description
Retrieves an asynchronous iterator of the `Entitlement` that the application has.

### Parameters
- **limit** (int) - Optional - Number of entitlements to retrieve. Defaults to 100.
- **before** (Snowflake/datetime) - Optional - Retrieve entitlements before this date or entitlement.
- **after** (Snowflake/datetime) - Optional - Retrieve entitlements after this date or entitlement.
- **skus** (Sequence[Snowflake]) - Optional - List of SKUs to filter by.
- **user** (Snowflake) - Optional - User to filter by.
- **guild** (Snowflake) - Optional - Guild to filter by.
- **exclude_ended** (bool) - Optional - Whether to exclude ended entitlements. Defaults to False.
- **exclude_deleted** (bool) - Optional - Whether to exclude deleted entitlements. Defaults to True.
```

--------------------------------

### await create_forum(name, *, topic=..., position=..., category=None, slowmode_delay=..., nsfw=..., media=..., overwrites=..., reason=None, default_auto_archive_duration=..., default_thread_slowmode_delay=..., default_sort_order=..., default_reaction_emoji=..., default_layout=..., available_tags=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new ForumChannel within the guild. This is a coroutine.

```APIDOC
## await create_forum(...)

### Description
Creates a new ForumChannel in the guild. The overwrites parameter can be used to create a 'secret' channel upon creation.

### Parameters
- **name** (str) - Required - The channel's name.
- **topic** (str) - Optional - The forum topic.
- **position** (int) - Optional - The position in the channel list.
- **category** (CategoryChannel) - Optional - The category to place the channel under.
- **slowmode_delay** (int) - Optional - The slowmode delay.
- **nsfw** (bool) - Optional - Whether the channel is NSFW.
- **overwrites** (Dict) - Optional - Permission overwrites for the channel.
- **reason** (str) - Optional - Reason for creation in audit log.
```

--------------------------------

### await chunk(cache)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Requests all members that belong to this guild. Requires Intents.members to be enabled.

```APIDOC
## await chunk(cache)

### Description
Requests all members that belong to this guild. This is a websocket operation and can be slow.

### Parameters
- **cache** (bool) - Whether to cache the members as well.

### Returns
- **List[Member]** - The list of members in the guild.

### Raises
- **ClientException** - The members intent is not enabled.
```

--------------------------------

### Handle Optional Attachments with Greedy

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates basic optional attachment handling and the use of Greedy to consume multiple attachments.

```python
@bot.command()
async def upload(ctx, attachment: typing.Optional[discord.Attachment]):
    if attachment is None:
        await ctx.send("You did not upload anything!")
    else:
        await ctx.send(f"You have uploaded <{attachment.url}>")
```

```python
import typing
import discord


@bot.command()
async def upload_many(
    ctx,
    first: discord.Attachment,
    second: typing.Optional[discord.Attachment],
):
    if second is None:
        files = [first.url]
    else:
        files = [first.url, second.url]

    await ctx.send(f"You uploaded: {' '.join(files)}")
```

```python
import discord
from discord.ext import commands


@bot.command()
async def upload_many(
    ctx,
    first: discord.Attachment,
    remaining: commands.Greedy[discord.Attachment],
):
    files = [first.url]
    files.extend(a.url for a in remaining)
    await ctx.send(f"You uploaded: {' '.join(files)}")
```

--------------------------------

### Flatten pinned messages into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to collect pinned messages into a list using an asynchronous list comprehension.

```python
messages = [message async for message in channel.pins(limit=50)]
# messages is now a list of Message...
```

--------------------------------

### await send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination. This is a coroutine that supports text content, embeds, files, stickers, and UI views.

```APIDOC
## await send(...)

### Description
Sends a message to the destination. If content is None, an embed must be provided.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message.
- **tts** (bool) - Optional - Whether to use text-to-speech.
- **embed** (Embed) - Optional - A single rich embed.
- **embeds** (List[Embed]) - Optional - A list of up to 10 embeds.
- **file** (File) - Optional - A single file to upload.
- **files** (List[File]) - Optional - A list of up to 10 files.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of up to 3 stickers.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **nonce** (int) - Optional - The nonce for the message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls mention processing.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A message to reference/reply to.
- **mention_author** (Optional[bool]) - Optional - Overrides mention behavior for replies.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A UI view to attach.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds.
- **silent** (bool) - Optional - Whether to suppress notifications.
- **poll** (Poll) - Optional - A poll to send.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### Registering Client Events via Subclassing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to handle events by subclassing discord.Client and defining coroutines for specific events.

```python
import discord


class MyClient(discord.Client):
    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith("$hello"):
            await message.channel.send("Hello World!")
```

--------------------------------

### End a Scheduled Event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends a scheduled event by updating its status to completed.

```python
await event.edit(status=EventStatus.completed)
```

--------------------------------

### Registering Command Checks

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates various ways to restrict command execution using predicates and decorators.

```python
async def is_owner(ctx):
    return ctx.author.id == 316026178463072268


@bot.command(name="eval")
@commands.check(is_owner)
async def _eval(ctx, *, code):
    """A bad example of an eval command"""
    await ctx.send(eval(code))
```

```python
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == 316026178463072268

    return commands.check(predicate)


@bot.command(name="eval")
@is_owner()
async def _eval(ctx, *, code):
    """A bad example of an eval command"""
    await ctx.send(eval(code))
```

```python
@bot.command(name="eval")
@commands.is_owner()
async def _eval(ctx, *, code):
    """A bad example of an eval command"""
    await ctx.send(eval(code))
```

```python
def is_in_guild(guild_id):
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == guild_id

    return commands.check(predicate)


@bot.command()
@commands.is_owner()
@is_in_guild(41771983423143937)
async def secretguilddata(ctx):
    """super secret stuff"""
    await ctx.send("secret stuff")
```

--------------------------------

### LayoutView.interaction_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Coroutine called to verify if the view should process item callbacks.

```APIDOC
## LayoutView.interaction_check(interaction)

### Description
A callback that checks whether the view should process item callbacks for the interaction. Defaults to returning True.

### Parameters
- **interaction** (Interaction) - Required - The interaction that occurred.

### Returns
- **bool** - Whether the view children's callbacks should be called.
```

--------------------------------

### discord.on_guild_stickers_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild updates its stickers. Requires Intents.emojis_and_stickers.

```APIDOC
## discord.on_guild_stickers_update(guild, before, after)

### Description
Called when a Guild updates its stickers. This requires Intents.emojis_and_stickers to be enabled.

### Parameters
- **guild** (Guild) - The guild who got their stickers updated.
- **before** (Sequence[GuildSticker]) - A list of stickers before the update.
- **after** (Sequence[GuildSticker]) - A list of stickers after the update.
```

--------------------------------

### Calling Coroutines with await or yield from

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates the transition from direct function calls to asynchronous execution using yield from or await.

```python
client.send_message(message.channel, "Hello")
```

```python
yield from client.send_message(message.channel, "Hello")

# or in python 3.5+
await client.send_message(message.channel, "Hello")
```

--------------------------------

### await create_category(name, *, overwrites=..., reason=None, position=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new CategoryChannel within the guild. This is a coroutine.

```APIDOC
## await create_category(name, *, overwrites=..., reason=None, position=...)

### Description
Creates a new CategoryChannel in the guild. Note that the category parameter is not supported as categories cannot have parent categories.

### Parameters
- **name** (str) - Required - The channel's name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply.
- **reason** (str) - Optional - The reason for creating this channel, shown in the audit log.
- **position** (int) - Optional - The position in the channel list.

### Returns
- **CategoryChannel** - The channel that was just created.

### Raises
- **Forbidden** - Insufficient permissions.
- **HTTPException** - Creation failed.
- **TypeError** - Permission overwrite information is not in proper form.
```

--------------------------------

### fetch_scheduled_events

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all scheduled events for the guild.

```APIDOC
## await fetch_scheduled_events(with_counts)

### Description
Retrieves a list of all scheduled events for the guild.

### Parameters
- **with_counts** (bool) - Optional - Whether to include the number of users that are subscribed to the event.
```

--------------------------------

### join

Source: https://discordpy.readthedocs.io/en/latest/api.html

Joins the current thread.

```APIDOC
## join()

### Description
Joins this thread. Requires send_messages_in_threads permission; private threads require manage_threads.

### Raises
- **Forbidden** - You do not have permissions to join the thread.
- **HTTPException** - Joining the thread failed.
```

--------------------------------

### await edit(name=..., archived=..., locked=..., invitable=..., pinned=..., slowmode_delay=..., auto_archive_duration=..., applied_tags=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the thread properties. Requires manage_threads permission.

```APIDOC
## await edit(name=..., archived=..., locked=..., invitable=..., pinned=..., slowmode_delay=..., auto_archive_duration=..., applied_tags=..., reason=None)

### Description
Edits the thread. Editing the thread requires Permissions.manage_threads.

### Parameters
- **name** (str) - Optional - The new name of the thread.
- **archived** (bool) - Optional - Whether to archive the thread or not.
- **locked** (bool) - Optional - Whether to lock the thread or not.
- **pinned** (bool) - Optional - Whether to pin the thread or not.
- **invitable** (bool) - Optional - Whether non-moderators can add other non-moderators to this thread.
- **auto_archive_duration** (int) - Optional - The new duration in minutes before a thread is automatically hidden.
- **slowmode_delay** (int) - Optional - Specifies the slowmode rate limit for user in this thread, in seconds.
- **applied_tags** (Sequence[ForumTag]) - Optional - The new tags to apply to the thread.
- **reason** (Optional[str]) - Optional - The reason for editing this thread.

### Returns
- **Thread** - The newly edited thread.
```

--------------------------------

### Iterate Guild Audit Logs

Source: https://discordpy.readthedocs.io/en/latest/api.html

Examples for retrieving and processing guild audit log entries using an asynchronous iterator.

```python
async for entry in guild.audit_logs(limit=100):
    print(f"{entry.user} did {entry.action} to {entry.target}")
```

```python
async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
    print(f"{entry.user} banned {entry.target}")
```

```python
entries = [entry async for entry in guild.audit_logs(limit=None, user=guild.me)]
await channel.send(f"I made {len(entries)} moderation actions.")
```

--------------------------------

### Waiting for messages in v1.0

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates the legacy approach for waiting for messages prior to the v1.0 generalization.

```python
# before
msg = await client.wait_for_message(author=message.author, channel=message.channel)
```

--------------------------------

### leave

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the current thread.

```APIDOC
## leave()

### Description
Leaves this thread.

### Raises
- **HTTPException** - Leaving the thread failed.
```

--------------------------------

### Update Extension Setup Function

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Convert synchronous setup functions to asynchronous coroutines to support the new loading mechanism.

```python
# before
def setup(bot):
    bot.add_cog(MyCog(bot))


# after
async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

--------------------------------

### Configure Basic Intents

Source: https://discordpy.readthedocs.io/en/latest/intents.html

Example of initializing a bot with specific intents for messages and guild information.

```python
import discord

intents = discord.Intents(messages=True, guilds=True)
# If you also want reaction events enable the following:
# intents.reactions = True

# Somewhere else:
# client = discord.Client(intents=intents)
# or
# from discord.ext import commands
# bot = commands.Bot(command_prefix='!', intents=intents)
```

--------------------------------

### Translator.unload()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

An asynchronous teardown function for cleaning up the translation system.

```APIDOC
## await Translator.unload()

### Description
An asynchronous teardown function for unloading the translation system. The default implementation does nothing.

### Method
Coroutine

### Usage
This is invoked when `CommandTree.set_translator()` is called if a tree already has a translator or when `discord.Client.close()` is called.
```

--------------------------------

### Perform web requests

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the aiohttp library for non-blocking HTTP requests within an async context.

```python
async with aiohttp.ClientSession() as session:
    async with session.get("http://aws.random.cat/meow") as r:
        if r.status == 200:
            js = await r.json()
```

--------------------------------

### fetch_stickers

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all stickers for the guild.

```APIDOC
## await fetch_stickers()

### Description
Retrieves a list of all `Sticker`s for the guild.
```

--------------------------------

### Fetch Guild Members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Iterate over guild members using an asynchronous loop. Requires the members intent to be enabled.

```python
async for member in guild.fetch_members(limit=150):
    print(member.name)
```

--------------------------------

### Create a basic command check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Shows how to define a simple predicate function and apply it to a command using the @commands.check decorator.

```python
def check_if_it_is_me(ctx):
    return ctx.message.author.id == 85309593344815104


@bot.command()
@commands.check(check_if_it_is_me)
async def only_for_me(ctx):
    await ctx.send("I know you!")
```

--------------------------------

### Wait for a message event

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use a predicate function to filter messages when waiting for a specific event.

```python
def pred(m):
    return m.author == message.author and m.channel == message.channel


msg = await client.wait_for("message", check=pred)
```

--------------------------------

### Iterate over SKU subscriptions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use an asynchronous loop to process subscriptions for a specific SKU.

```python
async for subscription in sku.subscriptions(limit=100, user=user):
    print(subscription.user_id, subscription.current_period_end)
```

--------------------------------

### Iterate all channels

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates the underlying logic for retrieving all accessible guild channels.

```python
for guild in client.guilds:
    for channel in guild.channels:
        yield channel
```

--------------------------------

### await end(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends the scheduled event. This is a coroutine.

```APIDOC
## await end(reason=None)

### Description
Ends the scheduled event. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for ending the scheduled event.

### Returns
- **ScheduledEvent** - The scheduled event that was ended.

### Raises
- **ValueError** - The scheduled event is not active or has already ended.
- **Forbidden** - You do not have the proper permissions to end the scheduled event.
- **HTTPException** - The scheduled event could not be ended.
```

--------------------------------

### Iterate all members

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates the underlying logic for retrieving all visible members across all guilds.

```python
for guild in client.guilds:
    for member in guild.members:
        yield member
```

--------------------------------

### fetch_automod_rules()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches all automod rules from the guild. Requires Permissions.manage_guild.

```APIDOC
## fetch_automod_rules()

### Description
Fetches all automod rules from the guild. Requires `Permissions.manage_guild`.

### Returns
- **List[AutoModRule]** - The automod rules that were fetched.
```

--------------------------------

### Set client activity

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Configure the bot's activity status upon initialization.

```python
activity = discord.Activity(name="my activity", type=discord.ActivityType.watching)
client = discord.Client(activity=activity)
```

--------------------------------

### Perform asynchronous HTTP requests

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use aiohttp instead of the requests library to avoid blocking the event loop during HTTP calls.

```python
# bad
r = requests.get("http://aws.random.cat/meow")
if r.status_code == 200:
    js = r.json()
    await channel.send(js["file"])

# good
async with aiohttp.ClientSession() as session:
    async with session.get("http://aws.random.cat/meow") as r:
        if r.status == 200:
            js = await r.json()
            await channel.send(js["file"])
```

--------------------------------

### Perform HTTP requests with ClientSession

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use aiohttp.ClientSession for managing HTTP requests instead of deprecated helper functions.

```python
async with aiohttp.ClientSession() as sess:
    async with sess.get('url') as resp:
        # work with resp
```

--------------------------------

### Iterate over pinned messages

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to asynchronously iterate through pinned messages in a channel using a limit.

```python
counter = 0
async for message in channel.pins(limit=250):
    counter += 1
```

--------------------------------

### await pin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Pins the message. Requires 'pin_messages' permission in non-private channels.

```APIDOC
## await pin(reason=None)

### Description
Pins the message. Requires 'pin_messages' permission in non-private channels.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message. Shows up on the audit log.
```

--------------------------------

### Send Typing Indicator in Channels

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to use the typing indicator as an asynchronous context manager or as a standalone awaitable call.

```python
async with channel.typing():
    # simulate something heavy
    await asyncio.sleep(20)

await channel.send("Done!")
```

```python
await channel.typing()
```

--------------------------------

### Guild.leave()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the guild. This is a coroutine.

```APIDOC
## await Guild.leave()

### Description
Leaves the guild.

### Raises
- **HTTPException** - Leaving the guild failed.
```

--------------------------------

### await translate(string, *, locale=..., data=...)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Translates a string using the set Translator.

```APIDOC
## await translate(string, *, locale=..., data=...)

### Description
Translates a string using the set Translator.

### Parameters
- **string** (Union[str, locale_str]) - Required - The string to translate.
- **locale** (Locale) - Optional - The locale to use.
- **data** (Any) - Optional - Extraneous data being translated.
```

--------------------------------

### Flatten SKU subscriptions into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Collect all subscriptions for an SKU into a standard Python list using an asynchronous comprehension.

```python
subscriptions = [subscription async for subscription in sku.subscriptions(limit=100, user=user)]
# subscriptions is now a list of Subscription...
```

--------------------------------

### fetch_members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all members in the thread.

```APIDOC
## fetch_members()

### Description
Retrieves all ThreadMember objects in this thread. Requires Intents.members.

### Returns
- **List[ThreadMember]** - All thread members in the thread.

### Raises
- **HTTPException** - Retrieving the members failed.
```

--------------------------------

### discord.on_guild_emojis_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild adds or removes Emoji. Requires Intents.emojis_and_stickers.

```APIDOC
## discord.on_guild_emojis_update(guild, before, after)

### Description
Called when a Guild adds or removes Emoji. This requires Intents.emojis_and_stickers to be enabled.

### Parameters
- **guild** (Guild) - The guild who got their emojis updated.
- **before** (Sequence[Emoji]) - A list of emojis before the update.
- **after** (Sequence[Emoji]) - A list of emojis after the update.
```

--------------------------------

### Chaining AsyncIterator operations

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Filter and map messages within an AsyncIterator chain.

```python
async for m_id in channel.history().filter(lambda m: m.author == client.user).map(lambda m: m.id):
    print(m_id)
```

--------------------------------

### Sync Guild-Specific Command Tree

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Synchronize the command tree for a specific guild after registering guild-restricted commands.

```python
await tree.sync(guild=discord.Object(123456789012345678))
```

--------------------------------

### await cancel(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Cancels the scheduled event. This is a coroutine.

```APIDOC
## await cancel(reason=None)

### Description
Cancels the scheduled event. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for cancelling the scheduled event.

### Returns
- **ScheduledEvent** - The scheduled event that was cancelled.

### Raises
- **ValueError** - The scheduled event is already running.
- **Forbidden** - You do not have the proper permissions to cancel the scheduled event.
- **HTTPException** - The scheduled event could not be cancelled.
```

--------------------------------

### Initialize Client with Intents

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Required update for all Client subclasses to explicitly define intents.

```python
# before
client = discord.Client()

# after
intents = discord.Intents.default()
client = discord.Client(intents=intents)
```

--------------------------------

### discord.on_app_command_completion(interaction, command)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event triggered when an app command or context menu has successfully completed.

```APIDOC
## discord.on_app_command_completion(interaction, command)

### Description
Called when an `app_commands.Command` or `app_commands.ContextMenu` has successfully completed without error.

### Parameters
- **interaction** (Interaction) - Required - The interaction of the command.
- **command** (Union[app_commands.Command, app_commands.ContextMenu]) - Required - The command that completed successfully.
```

--------------------------------

### fetch()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches the partial message to a full Message object.

```APIDOC
## fetch()

### Description
Fetches the partial message to a full Message.

### Returns
- **Message** - The full message.
```

--------------------------------

### Start a Scheduled Event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Starts a scheduled event by updating its status to active.

```python
await event.edit(status=EventStatus.active)
```

--------------------------------

### Updating on_guild_emojis_update signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now includes the Guild object as the first argument.

```python
async def on_guild_emojis_update(before, after)
```

```python
async def on_guild_emojis_update(guild, before, after)
```

--------------------------------

### fetch_scheduled_event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific scheduled event from the guild.

```APIDOC
## await fetch_scheduled_event(scheduled_event_id, with_counts)

### Description
Retrieves a scheduled event from the guild.

### Parameters
- **scheduled_event_id** (int) - Required - The scheduled event ID.
- **with_counts** (bool) - Optional - Whether to include the number of users that are subscribed to the event.
```

--------------------------------

### Handle Command Errors with Local Error Handlers

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates catching a CheckFailure exception within a command-specific error handler.

```python
@bot.command()
@commands.is_owner()
@is_in_guild(41771983423143937)
async def secretguilddata(ctx):
    """super secret stuff"""
    await ctx.send("secret stuff")


@secretguilddata.error
async def secretguilddata_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("nothing to see here comrade.")
```

--------------------------------

### Migrate Naive Datetime to UTC-Aware

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Update datetime calculations to use UTC-aware objects to avoid local time ambiguity.

```python
# before
week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
if member.created_at > week_ago:
    print(f"Member account {member} was created less than a week ago!")

# after
# The new helper function can be used here:
week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
# ...or the equivalent result can be achieved with datetime.datetime.now():
week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
if member.created_at > week_ago:
    print(f"Member account {member} was created less than a week ago!")
```

--------------------------------

### fetch_roles()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all roles associated with the guild.

```APIDOC
## await fetch_roles()

### Description
Retrieves all `Role` that the guild has.

### Returns
- **List[Role]** - All roles in the guild.

### Raises
- **HTTPException** - Retrieving the roles failed.
```

--------------------------------

### Thread.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a typing indicator to the thread.

```APIDOC
## Thread.typing

### Description
Returns an asynchronous context manager that sends a typing indicator to the thread. It can be used as a context manager for an indefinite period or awaited for 10 seconds.

### Example Usage
```python
async with thread.typing():
    await asyncio.sleep(20)

await thread.send('Done!')
```
```

--------------------------------

### await query_members(query, limit, user_ids, presences, cache)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Request members of this guild whose username or nickname starts with the given query.

```APIDOC
## await query_members(query, limit, user_ids, presences, cache)

### Description
Request members of this guild whose username or nickname starts with the given query. This is a websocket operation.

### Parameters
- **query** (Optional[str]) - The string that the username or nickname should start with.
- **limit** (int) - The maximum number of members to send back (5-100).
- **presences** (bool) - Whether to request for presences to be provided.
- **cache** (bool) - Whether to cache the members internally.
- **user_ids** (Optional[List[int]]) - List of user IDs to search for.

### Returns
- **List[Member]** - The list of members that have matched the query.

### Raises
- **asyncio.TimeoutError** - The query timed out.
- **ValueError** - Invalid parameters were passed.
- **ClientException** - The presences intent is not enabled.
```

--------------------------------

### await start(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Starts the scheduled event. This is a coroutine.

```APIDOC
## await start(reason=None)

### Description
Starts the scheduled event. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for starting the scheduled event.

### Returns
- **ScheduledEvent** - The scheduled event that was started.

### Raises
- **ValueError** - The scheduled event has already started or has ended.
- **Forbidden** - You do not have the proper permissions to start the scheduled event.
- **HTTPException** - The scheduled event could not be started.
```

--------------------------------

### fetch_thread()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves the public thread attached to this message via an API call.

```APIDOC
## fetch_thread()

### Description
Retrieves the public thread attached to this message.

### Returns
- **Thread** - The public thread attached to this message.
```

--------------------------------

### create_sticker

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a sticker for the guild. Requires manage_emojis_and_stickers permission.

```APIDOC
## await create_sticker(name, description, emoji, file, reason)

### Description
Creates a `Sticker` for the guild. You must have `manage_emojis_and_stickers` to do this.

### Parameters
- **name** (str) - Required - The sticker name.
- **description** (str) - Optional - The sticker’s description.
- **emoji** (str) - Required - The emoji tag associated with the sticker.
- **file** (File) - Required - The file of the sticker to upload.
- **reason** (str) - Optional - The reason for creating this sticker.
```

--------------------------------

### CommandTree.sync

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Syncs the application commands to Discord, including translation processing. This must be called for commands to appear in the Discord UI.

```APIDOC
## await CommandTree.sync(guild=None)

### Description
Syncs the application commands to Discord. This also runs the translator to get the translated strings necessary for feeding back into Discord. This must be called for the application commands to show up.

### Parameters
#### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to sync the commands to. If None then it syncs all global commands instead.

### Returns
- **List[AppCommand]** - The application’s commands that got synced.

### Raises
- **HTTPException** - Syncing the commands failed.
- **CommandSyncFailure** - Syncing the commands failed due to a user related error.
- **Forbidden** - The client does not have the applications.commands scope in the guild.
- **MissingApplicationID** - The client does not have an application ID.
- **TranslationError** - An error occurred while translating the commands.
```

--------------------------------

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves permissions for a given Member or Role within the context of the thread, inheriting from the parent channel.

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for the Member or Role. Since threads do not have their own permissions, they mostly inherit them from the parent channel with some implicit permissions changed.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for. If it’s a role then member overwrites are not computed.

### Returns
- **Permissions** - The resolved permissions for the member or role.

### Raises
- **ClientException** - The parent channel was not cached and returned None.
```

--------------------------------

### AppCommandThread.fetch()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches the partial channel to a full Thread object. This is a coroutine.

```APIDOC
## await fetch()

### Description
Fetches the partial channel to a full Thread object.

### Raises
- **NotFound** - The thread was not found.
- **Forbidden** - You do not have the permissions required to get a thread.
- **HTTPException** - Retrieving the thread failed.

### Returns
- **Thread** - The full thread object.
```

--------------------------------

### Manage Event Loop Manually

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates how to gain control over the event loop by manually logging in and connecting instead of using the blocking run method.

```python
import discord
import asyncio

client = discord.Client()


@asyncio.coroutine
def main_task():
    yield from client.login("token")
    yield from client.connect()


loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main_task())
except:
    loop.run_until_complete(client.logout())
finally:
    loop.close()
```

--------------------------------

### await unpin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unpins the message. Requires 'pin_messages' permission in non-private channels.

```APIDOC
## await unpin(reason=None)

### Description
Unpins the message. Requires 'pin_messages' permission in non-private channels.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for unpinning the message. Shows up on the audit log.
```

--------------------------------

### @discord.ext.commands.max_concurrency(number, per=BucketType.default, *, wait=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator that adds a maximum concurrency limit to a Command or its subclasses.

```APIDOC
## @discord.ext.commands.max_concurrency(number, per=BucketType.default, *, wait=False)

### Description
A decorator that adds a maximum concurrency to a `Command` or its subclasses. This enables you to only allow a certain number of command invocations at the same time.

### Parameters
- **number** (int) - Required - The maximum number of invocations of this command that can be running at the same time.
- **per** (BucketType) - Optional - The bucket that this concurrency is based on.
- **wait** (bool) - Optional - Whether the command should wait for the queue to be over.
```

--------------------------------

### Create a text channel in a guild

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates creating a standard text channel using the create_text_channel coroutine.

```python
channel = await guild.create_text_channel("cool-channel")
```

--------------------------------

### Use listeners for message events

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use @bot.listen to handle events without needing to manually process commands.

```python
@bot.listen('on_message')
async def whatever_you_want_to_call_it(message):
    # do stuff here
    # do not process commands here
```

--------------------------------

### await fetch_automod_rule(automod_rule_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches an active automod rule from the guild.

```APIDOC
## await fetch_automod_rule(automod_rule_id)

### Description
Fetches an active automod rule from the guild. Requires Permissions.manage_guild.

### Parameters
- **automod_rule_id** (int) - The ID of the automod rule to fetch.

### Returns
- **AutoModRule** - The automod rule that was fetched.

### Raises
- **Forbidden** - You do not have permission to view the automod rule.
- **NotFound** - The automod rule does not exist within this guild.
```

--------------------------------

### on_submit(interaction)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine called when the modal is submitted.

```APIDOC
## await on_submit(interaction)

### Parameters
- **interaction** (Interaction) - Required - The interaction that submitted this modal.
```

--------------------------------

### @discord.ext.commands.before_invoke(coro)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a coroutine as a pre-invoke hook for commands.

```APIDOC
## @discord.ext.commands.before_invoke(coro)

### Description
A decorator that registers a coroutine as a pre-invoke hook. This allows you to refer to one before invoke hook for several commands that do not have to be within the same cog.

### Parameters
- **coro** (Callable) - Required - The coroutine to execute before the command.
```

--------------------------------

### @discord.ext.commands.after_invoke(coro)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a coroutine as a post-invoke hook for commands.

```APIDOC
## @discord.ext.commands.after_invoke(coro)

### Description
A decorator that registers a coroutine as a post-invoke hook. This allows you to refer to one after invoke hook for several commands that do not have to be within the same cog.

### Parameters
- **coro** (Callable) - Required - The coroutine to execute after the command.
```

--------------------------------

### Set bot activity status

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Pass an Activity object to the Client constructor to set a static playing status.

```python
client = discord.Client(activity=discord.Game(name="my game"))
```

--------------------------------

### Extend a command check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates how to wrap an existing check to add custom logic, such as allowing the guild owner to bypass specific permissions.

```python
def owner_or_permissions(**perms):
    original = commands.has_permissions(**perms).predicate

    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.guild.owner_id == ctx.author.id or await original(ctx)

    return commands.check(extended_check)
```

--------------------------------

### Restrict command by role

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Requires the user to possess at least one of the specified roles or role IDs.

```python
@bot.command()
@commands.has_any_role("Library Devs", "Moderators", 492212595072434186)
async def cool(ctx):
    await ctx.send("You are cool indeed")
```

--------------------------------

### fetch_skus

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the bot’s available SKUs.

```APIDOC
## fetch_skus()

### Description
Retrieves the bot’s available SKUs.

### Returns
- **List[SKU]** - The bot’s available SKUs.
```

--------------------------------

### await fetch_widget()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the widget of the guild. The guild must have the widget enabled.

```APIDOC
## await fetch_widget()

### Description
Retrieves the widget of the guild. Note that the guild must have the widget enabled to get this information.

### Returns
- **Widget** - The guild's widget.

### Raises
- **Forbidden** - The widget for this guild is disabled.
- **HTTPException** - Retrieving the widget failed.
```

--------------------------------

### wait_for(event, *, check=None, timeout=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Waits for a WebSocket event to be dispatched. This is a coroutine that returns the first event that meets the requirements.

```APIDOC
## wait_for(event, *, check=None, timeout=None)

### Description
Waits for a WebSocket event to be dispatched. This function returns the first event that meets the requirements.

### Parameters
- **event** (str) - Required - The event name, without the 'on_' prefix.
- **check** (Optional[Callable[..., bool]]) - Optional - A predicate to check what to wait for.
- **timeout** (Optional[float]) - Optional - The number of seconds to wait before timing out.

### Returns
- **Any** - Returns no arguments, a single argument, or a tuple of multiple arguments that mirrors the parameters passed in the event reference.
```

--------------------------------

### audit_logs(*, limit=100, before=..., after=..., oldest_first=..., user=..., action=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator that enables receiving the guild’s audit logs.

```APIDOC
## audit_logs(*, limit=100, before=..., after=..., oldest_first=..., user=..., action=...)

### Description
Returns an asynchronous iterator that enables receiving the guild’s audit logs. You must have view_audit_log to do this.

### Parameters
- **limit** (int) - Optional - The number of entries to retrieve.
- **before** (abc.Snowflake) - Optional - Retrieve entries before this entry.
- **after** (abc.Snowflake) - Optional - Retrieve entries after this entry.
- **oldest_first** (bool) - Optional - Whether to return entries in oldest first order.
- **user** (abc.Snowflake) - Optional - Filter by a specific user.
- **action** (AuditLogAction) - Optional - Filter by a specific action.
```

--------------------------------

### await edit_widget(enabled, channel, reason)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the widget of the guild. Requires manage_guild permission.

```APIDOC
## await edit_widget(enabled, channel, reason)

### Description
Edits the widget of the guild. You must have manage_guild permission to perform this action.

### Parameters
- **enabled** (bool) - Whether to enable the widget for the guild.
- **channel** (Optional[Snowflake]) - The new widget channel. None removes the widget channel.
- **reason** (Optional[str]) - The reason for editing this widget, which shows up on the audit log.

### Raises
- **Forbidden** - You do not have permission to edit the widget.
- **HTTPException** - Editing the widget failed.
```

--------------------------------

### Define a command with a Timestamp parameter

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the Timestamp annotation to automatically convert Discord timestamp inputs into datetime objects.

```python
@app_commands.command()
async def datetime(interaction: discord.Interaction, value: app_commands.Timestamp):
    await interaction.response.send_message(value.isoformat())
```

--------------------------------

### Send a typing indicator with async context manager

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use the async context manager to show a typing indicator for the duration of a block of code.

```python
async with channel.typing():
    # simulate something heavy
    await asyncio.sleep(20)

await channel.send("Done!")
```

--------------------------------

### @discord.app_commands.checks.has_permissions(**perms)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member has all of the specified permissions.

```APIDOC
## @discord.app_commands.checks.has_permissions(**perms)

### Description
A check that verifies if the member has all of the permissions necessary, based on `discord.Interaction.permissions`. Raises `MissingPermissions` on failure.

### Parameters
- **perms** (bool) - Required - Keyword arguments denoting the permissions to check for.
```

--------------------------------

### discord.ext.commands.on_command_completion

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

An event called when a command has successfully completed its invocation.

```APIDOC
## discord.ext.commands.on_command_completion(ctx)

### Description
An event that is called when a command has completed its invocation. This event is called only if the command succeeded.

### Parameters
- **ctx** (Context) - The invocation context.
```

--------------------------------

### Define an extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

Create a Python file with a setup coroutine to register commands with the bot.

```python
from discord.ext import commands


@commands.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.display_name}.")


async def setup(bot):
    bot.add_command(hello)
```

--------------------------------

### await send(content=..., username=..., avatar_url=..., tts=False, ephemeral=False, file=..., files=..., embed=..., embeds=..., allowed_mentions=..., view=..., thread=..., thread_name=..., wait=False, suppress_embeds=False, silent=False, applied_tags=..., poll=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message using the webhook.

```APIDOC
## await send(...)

### Description
Sends a message using the webhook. The content must be a type that can convert to a string through str(content).
```

--------------------------------

### await _onboarding()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the onboarding configuration for the guild. This is a coroutine.

```APIDOC
## await _onboarding()

### Description
Fetches the onboarding configuration for this guild.

### Returns
- **Onboarding** - The onboarding configuration that was fetched.
```

--------------------------------

### Set channel permissions with keyword arguments

Source: https://discordpy.readthedocs.io/en/latest/api.html

Configures channel-specific permissions for a member or role using keyword arguments for individual permission attributes.

```python
await message.channel.set_permissions(message.author, read_messages=True, send_messages=False)
```

--------------------------------

### Update command extension events

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Compares the old and new signatures for command-related events.

```python
# Before
on_command(command, ctx)
on_command_completion(command, ctx)
on_command_error(error, ctx)

# After
on_command(ctx)
on_command_completion(ctx)
on_command_error(ctx, error)
```

--------------------------------

### move(beginning=..., end=..., above=..., below=..., offset=0, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves a role relative to other roles in the guild.

```APIDOC
## move(beginning, end, above, below, offset, reason)

### Description
A coroutine to move a role relative to other roles. Requires manage_roles permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning of the list.
- **end** (bool) - Optional - Move to the end of the list.
- **above** (Role) - Optional - Move above this role.
- **below** (Role) - Optional - Move below this role.
- **offset** (int) - Optional - Number of roles to offset the move.
- **reason** (Optional[str]) - Optional - Reason for the audit log.

### Returns
- **List[Role]** - A list of all roles in the guild.
```

--------------------------------

### interaction_check(interaction)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine that checks whether the callback should be processed.

```APIDOC
## await interaction_check(interaction)

### Description
A callback that is called when an interaction happens within this item that checks whether the callback should be processed. Useful for permission checks.

### Parameters
- **interaction** (Interaction) - Required - The interaction that occurred.

### Returns
- **bool** - Whether the callback should be called.
```

--------------------------------

### Bulk Edit Role Positions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the positions of multiple roles in a guild using a dictionary mapping roles to their new integer positions.

```python
positions = {
    bots_role: 1,  # penultimate role
    tester_role: 2,
    admin_role: 6,
}

await guild.edit_role_positions(positions=positions)
```

--------------------------------

### Registering Events with asyncio

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates the transition from standard event registration to coroutine-based registration using @asyncio.coroutine or async def.

```python
@client.event
def on_message(message):
    pass
```

```python
@client.event
@asyncio.coroutine
def on_message(message):
    pass
```

```python
@client.event
async def on_message(message):
    pass
```

--------------------------------

### Member.typing()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination. It can be used as an async context manager for an indefinite period or awaited to send a typing indicator for 10 seconds.

```APIDOC
## async with channel.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is called using `await`.

### Usage
```python
async with channel.typing():
    # simulate something heavy
    await asyncio.sleep(20)

await channel.send('Done!')

# Or
await channel.typing()
# Do some computational magic for about 10 seconds
await channel.send('Done!')
```
```

--------------------------------

### Attaching a Channel Select Menu to a LayoutView

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates using the select decorator with ChannelSelect to filter for text channels and respond with the selected channel's mention.

```python
class MyView(discord.ui.LayoutView):
    action_row = discord.ui.ActionRow()

    @action_row.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f'You selected {select.values[0].mention}')
```

--------------------------------

### discord.opus.is_loaded()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the opus library has been successfully loaded.

```APIDOC
## discord.opus.is_loaded()

### Description
Checks if the opus library is successfully loaded either via `ctypes.util.find_library()` or `load_opus()`.

### Returns
- **bool** - Indicates if the opus library has been loaded.
```

--------------------------------

### fetch_members(limit=1000, after=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator for the guild's members.

```APIDOC
## async for ... in fetch_members(limit=1000, after=...)

### Description
Retrieves an asynchronous iterator that enables receiving the guild’s members. Requires `Intents.members` to be enabled.

### Parameters
- **limit** (Optional[int]) - Optional - The number of members to retrieve. Defaults to 1000.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve members after this date or object.

### Yields
- **Member** - The member with the member data parsed.
```

--------------------------------

### typing()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination.

```APIDOC
## typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is called using await.
```

--------------------------------

### discord.on_entitlement_create(entitlement)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a user subscribes to a SKU.

```APIDOC
## discord.on_entitlement_create(entitlement)

### Description
Called when a user subscribes to a SKU.

### Parameters
- **entitlement** (Entitlement) - Required - The entitlement that was created.
```

--------------------------------

### Set Channel Permissions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Examples for configuring channel-specific permission overwrites for members or roles.

```python
await message.channel.set_permissions(message.author, read_messages=True, send_messages=False)
```

```python
await channel.set_permissions(member, overwrite=None)
```

```python
overwrite = discord.PermissionOverwrite()
overwrite.send_messages = False
overwrite.read_messages = True
await channel.set_permissions(member, overwrite=overwrite)
```

--------------------------------

### Restrict command by channel permissions

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Requires the user to have specific channel-level permissions to execute the command.

```python
@bot.command()
@commands.has_permissions(manage_messages=True)
async def test(ctx):
    await ctx.send("You can manage messages.")
```

--------------------------------

### Update Client Execution Pattern

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Shows the transition from separate login and run calls to a single blocking run call with credentials.

```python
client.login("token")
client.run()
```

```python
client.run("token")
```

--------------------------------

### await fetch_guild(guild_id, *, with_counts=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a Guild object from an ID.

```APIDOC
## await fetch_guild(guild_id, *, with_counts=True)

### Description
Retrieves a Guild from an ID.

### Parameters
- **guild_id** (int) - Required - The guild's ID to fetch from.
- **with_counts** (bool) - Optional - Whether to include count information. Defaults to True.

### Raises
- **NotFound** - The guild doesn't exist or you got no access to it.
- **HTTPException** - Getting the guild failed.
```

--------------------------------

### Consume remaining arguments in commands

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the * syntax in command signatures to capture all remaining input as a single argument.

```python
@bot.command()
async def echo(ctx, message: str):
    await ctx.send(message)
```

```python
@bot.command()
async def echo(ctx, *, message: str):
    await ctx.send(message)
```

--------------------------------

### ForumChannel.permissions_for

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves the permissions for a given member or role in the forum channel.

```APIDOC
## ForumChannel.permissions_for(obj)

### Description
Handles permission resolution for a Member or Role, taking into account guild owner status, roles, channel overrides, member overrides, implicit permissions, member timeouts, and user-installed apps.

### Parameters
- **obj** (Union[Member, Role]) - Required - The member or role to resolve permissions for.
```

--------------------------------

### leave()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the group. If you are the only one in the group, this deletes it as well.

```APIDOC
## await leave()

### Description
Leave the group. If you are the only one in the group, this deletes it as well.

### Raises
- **HTTPException** - Leaving the group failed.
```

--------------------------------

### Run the bot script

Source: https://discordpy.readthedocs.io/en/latest/quickstart.html

Commands to execute the bot script on different operating systems.

```bash
$ py -3 example_bot.py
```

```bash
$ python3 example_bot.py
```

--------------------------------

### Send a typing indicator for 10 seconds

Source: https://discordpy.readthedocs.io/en/latest/api.html

Await the typing method to display a typing indicator for a fixed 10-second duration.

```python
await channel.typing()
# Do some computational magic for about 10 seconds
await channel.send("Done!")
```

--------------------------------

### Cancel a Scheduled Event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Cancels a scheduled event by updating its status to cancelled.

```python
await event.edit(status=EventStatus.cancelled)
```

--------------------------------

### await _edit_onboarding(*, prompts=..., default_channels=..., enabled=..., mode=..., reason=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the onboarding configuration for the guild. Requires Permissions.manage_guild and Permissions.manage_roles.

```APIDOC
## await _edit_onboarding(*, prompts=..., default_channels=..., enabled=..., mode=..., reason=...)

### Description
Edits the onboarding configuration for this guild.

### Parameters
- **prompts** (List[OnboardingPrompt]) - Optional - The prompts that will be shown to new members.
- **default_channels** (List[abc.Snowflake]) - Optional - The channels that will be used as the default channels for new members.
- **enabled** (bool) - Optional - Whether the onboarding configuration is enabled.
- **mode** (OnboardingMode) - Optional - The mode that will be used for the onboarding configuration.
- **reason** (str) - Optional - The reason for editing the onboarding configuration.

### Raises
- **Forbidden** - You do not have permissions to edit the onboarding configuration.
- **HTTPException** - Editing the onboarding configuration failed.

### Returns
- **Onboarding** - The new onboarding configuration.
```

--------------------------------

### by_category()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns every CategoryChannel and their associated channels, sorted in the official Discord UI order.

```APIDOC
## by_category()

### Description
Returns every `CategoryChannel` and their associated channels. These channels and categories are sorted in the official Discord UI order. If the channels do not have a category, then the first element of the tuple is `None`.

### Returns
- **List[Tuple[Optional[CategoryChannel], List[abc.GuildChannel]]]** - The categories and their associated channels.
```

--------------------------------

### @discord.app_commands.checks.has_any_role(*items)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member invoking the command has at least one of the specified roles.

```APIDOC
## @discord.app_commands.checks.has_any_role(*items)

### Description
A check that verifies if the member invoking the command has any of the roles specified. Raises `MissingAnyRole` or `NoPrivateMessage` on failure.

### Parameters
- **items** (List[Union[str, int]]) - Required - An argument list of names or IDs to check.
```

--------------------------------

### create_thread

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new thread within the text channel.

```APIDOC
## create_thread(name, message=None, auto_archive_duration=None, type=None, reason=None, invitable=True, slowmode_delay=None)

### Description
Creates a new thread in the text channel. Returns the created Thread object.

### Parameters
- **name** (str) - Required - The name of the thread.
- **message** (Optional[abc.Snowflake]) - Optional - The message to create the thread with.
- **auto_archive_duration** (int) - Optional - Duration in minutes before the thread is archived (60, 1440, 4320, or 10080).
- **type** (Optional[ChannelType]) - Optional - The type of thread to create.
- **reason** (str) - Optional - The reason for creating the thread for audit logs.
- **invitable** (bool) - Optional - Whether non-moderators can add users to the thread.
- **slowmode_delay** (Optional[int]) - Optional - Slowmode rate limit in seconds.

### Returns
- **Thread** - The created thread object.
```

--------------------------------

### Create a basic application command check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Defines a predicate function to validate the command invoker and applies it using the @app_commands.check decorator.

```python
def check_if_it_is_me(interaction: discord.Interaction) -> bool:
    return interaction.user.id == 85309593344815104


@tree.command()
@app_commands.check(check_if_it_is_me)
async def only_for_me(interaction: discord.Interaction):
    await interaction.response.send_message("I know you!", ephemeral=True)
```

--------------------------------

### fetch_guilds

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves an asynchronous iterator that enables receiving your guilds.

```APIDOC
## fetch_guilds(limit=200, before=None, after=None, with_counts=True)

### Description
Retrieves an asynchronous iterator that enables receiving your guilds. Note that this is an API call.

### Parameters
- **limit** (Optional[int]) - Optional - The number of guilds to retrieve. Defaults to 200.
- **before** (Union[abc.Snowflake, datetime.datetime]) - Optional - Retrieves guilds before this date or object.
- **after** (Union[abc.Snowflake, datetime.datetime]) - Optional - Retrieves guilds after this date or object.
- **with_counts** (bool) - Optional - Whether to include count information in the guilds. Defaults to True.

### Returns
- **Guild** - The guild with the guild data parsed.
```

--------------------------------

### CategoryChannel.permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves the permissions for a specific member or role within the category channel.

```APIDOC
## permissions_for(obj)

### Description
Resolves the permissions for a member or role in the channel. If a role is provided, member overwrites are not computed.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for.

### Returns
- **Permissions** - The resolved permissions for the member or role.
```

--------------------------------

### discord.utils.sleep_until

Source: https://discordpy.readthedocs.io/en/latest/api.html

Coroutine to sleep until a specified datetime.

```APIDOC
## discord.utils.sleep_until(when, result=None)

### Description
This function is a coroutine. Sleep until a specified time. If the time supplied is in the past this function will yield instantly.

### Parameters
- **when** (datetime.datetime) - Required - The timestamp in which to sleep until.
- **result** (Any) - Optional - If provided is returned to the caller when the coroutine completes.
```

--------------------------------

### Find an element in a sequence using discord.utils.find

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the first element in an iterable that satisfies the provided predicate function.

```python
member = discord.utils.find(lambda m: m.name == "Mighty", channel.guild.members)
```

--------------------------------

### await reply(content=None, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shortcut method to abc.Messageable.send() to reply to the Message.

```APIDOC
## await reply(content=None, **kwargs)

### Description
A shortcut method to abc.Messageable.send() to reply to the Message.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### pins()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the pinned messages for the channel.

```APIDOC
## pins(limit=50, before=None, oldest_first=False)

### Description
Retrieves the pinned messages in the channel.

### Parameters
- **limit** (Optional[int]) - Optional - The number of pinned messages to retrieve. Defaults to 50.
- **before** (Optional[Union[datetime.datetime, abc.Snowflake]]) - Optional - Retrieve pinned messages before this time or snowflake.
- **oldest_first** (bool) - Optional - If set to True, return messages in oldest pin to newest pin order. Defaults to False.

### Yields
- **Message** - The pinned message with Message.pinned_at set.

### Raises
- **Forbidden** - You do not have the permission to retrieve pinned messages.
- **HTTPException** - Retrieving the pinned messages failed.
```

--------------------------------

### discord.ui.View

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI view that must be inherited to create a UI within Discord.

```APIDOC
## class discord.ui.View(timeout=180.0)

### Description
Represents a UI view. This object must be inherited to create a UI within Discord.

### Parameters
- **timeout** (Optional[float]) - Optional - Timeout in seconds from last interaction with the UI before no longer accepting input. If None then there is no timeout.
```

--------------------------------

### fetch_commands(guild=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches all current application commands, either globally or for a specific guild.

```APIDOC
## fetch_commands(guild=None)

### Description
Fetches the application's current commands. If no guild is passed, global commands are fetched; otherwise, the guild's commands are fetched.

### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to fetch the commands from.

### Returns
- **List[AppCommand]** - A list of the application's commands.

### Raises
- **HTTPException** - Fetching the commands failed.
- **MissingApplicationID** - The application ID could not be found.
```

--------------------------------

### send(content=..., username=..., avatar_url=..., tts=False, file=..., files=..., embed=..., embeds=..., allowed_mentions=..., thread=..., thread_name=..., wait=False, suppress_embeds=False, silent=False, applied_tags=..., poll=..., view=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message using the webhook.

```APIDOC
## send(content=..., username=..., avatar_url=..., tts=False, file=..., files=..., embed=..., embeds=..., allowed_mentions=..., thread=..., thread_name=..., wait=False, suppress_embeds=False, silent=False, applied_tags=..., poll=..., view=...)

### Description
Sends a message using the webhook. The content must be a type that can convert to a string through str(content).
```

--------------------------------

### Create a minimal Discord bot

Source: https://discordpy.readthedocs.io/en/latest/quickstart.html

Initializes a client with message content intents and defines event handlers for ready and message events.

```python
# This example requires the 'message_content' intent.

import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")


client.run("your token here")
```

--------------------------------

### fetch_emojis()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all custom emojis from the guild.

```APIDOC
## await fetch_emojis()

### Description
Retrieves all custom `Emoji`s from the guild.

### Returns
- **List[Emoji]** - The retrieved emojis.

### Raises
- **HTTPException** - An error occurred fetching the emojis.
```

--------------------------------

### process_commands(message)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Processes commands registered to the bot. This is typically called within the on_message event.

```APIDOC
## process_commands(message)

### Description
Processes the commands that have been registered to the bot and other groups. This is a coroutine that should be invoked if you override the on_message event.

### Parameters
- **message** (discord.Message) - Required - The message to process commands for.
```

--------------------------------

### prune_members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Prunes the guild from its inactive members based on the number of days of inactivity and specific roles.

```APIDOC
## await prune_members(*, days, compute_prune_count=True, roles=..., reason=None)

### Description
Prunes the guild from its inactive members. Inactive members are those who have not logged on in the specified number of days and have no roles.

### Parameters
- **days** (int) - Required - The number of days before counting as inactive.
- **reason** (Optional[str]) - Optional - The reason for doing this action, which shows up on the audit log.
- **compute_prune_count** (bool) - Optional - Whether to compute the prune count. Defaults to True.
- **roles** (List[abc.Snowflake]) - Optional - A list of roles to include in the pruning process.

### Returns
- **int** - The number of members pruned. Returns None if compute_prune_count is False.
```

--------------------------------

### Register a global check with @bot.check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a check that runs before any command checks for every command in the bot.

```python
@bot.check
def check_commands(ctx):
    return ctx.command.qualified_name in allowed_commands
```

--------------------------------

### Iterate Guild Bans

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieve a paginated iterator of banned users. Requires the ban_members permission.

```python
async for entry in guild.bans(limit=150):
    print(entry.user, entry.reason)
```

```python
bans = [entry async for entry in guild.bans(limit=2000)]
```

--------------------------------

### purge(limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine that purges a list of messages that meet the criteria given by the predicate check.

```APIDOC
## purge(limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

### Description
Purges a list of messages that meet the criteria given by the predicate check. If a check is not provided, all messages are deleted. Requires manage_messages and read_message_history permissions.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to search through.
- **check** (Callable[[Message], bool]) - Optional - The function used to check if a message should be deleted.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this time or snowflake.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this time or snowflake.
- **around** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this time or snowflake.
- **oldest_first** (Optional[bool]) - Optional - Order of messages.
- **bulk** (bool) - Optional - If True, use bulk delete. Defaults to True.
- **reason** (Optional[str]) - Optional - The reason for purging the messages for the audit log.

### Returns
- **List[Message]** - The list of messages that were deleted.

### Raises
- **Forbidden** - You do not have proper permissions to do the actions required.
- **HTTPException** - Purging the messages failed.
```

--------------------------------

### await publish()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Publishes this message to the channel’s followers. Must be in a news channel.

```APIDOC
## await publish()

### Description
Publishes this message to the channel’s followers. The message must have been sent in a news channel. Requires 'send_messages' permission, or 'manage_messages' if the message is not your own.
```

--------------------------------

### @discord.ext.commands.guild_only()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A check that indicates the command must only be used in a guild context.

```APIDOC
## @discord.ext.commands.guild_only()

### Description
A `check()` that indicates this command must only be used in a guild context only. Basically, no private messages are allowed when using the command.
```

--------------------------------

### await edit(reason=None, name=..., avatar=..., channel=None, prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the webhook's properties.

```APIDOC
## await edit(reason=None, name=..., avatar=..., channel=None, prefer_auth=True)

### Description
Edits this Webhook.

### Parameters
- **name** (str) - Optional - The webhook’s new default name.
- **avatar** (bytes) - Optional - A bytes-like object representing the webhook’s new default avatar.
- **channel** (abc.Snowflake) - Optional - The webhook’s new channel. This requires an authenticated webhook.
- **reason** (str) - Optional - The reason for editing this webhook. Shows up on the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### SyncWebhook.fetch

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the current webhook details from Discord.

```APIDOC
## SyncWebhook.fetch(*, prefer_auth=True)

### Description
Fetches the current webhook. This is useful for retrieving a full webhook object from a partial one.

### Parameters
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### create_thread(name, auto_archive_duration=..., slowmode_delay=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Creates a public thread from the message. Requires the 'create_public_threads' permission and must be in a TextChannel.

```APIDOC
## create_thread(name, auto_archive_duration=..., slowmode_delay=None, reason=None)

### Description
Creates a public thread from this message.

### Parameters
- **name** (str) - Required - The name of the thread.
- **auto_archive_duration** (int) - Optional - The duration in minutes before a thread is automatically hidden. Must be 60, 1440, 4320, or 10080.
- **slowmode_delay** (Optional[int]) - Optional - The slowmode rate limit for the channel in seconds.
- **reason** (Optional[str]) - Optional - The reason for creating the thread, shown in the audit log.

### Returns
- **Thread** - The created thread.
```

--------------------------------

### archived_threads

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator for archived threads in the forum.

```APIDOC
## async for ... in archived_threads(limit=100, before=None)

### Description
Returns an asynchronous iterator that iterates over all archived threads in this forum in order of decreasing Thread.archive_timestamp. You must have `read_message_history` to do this.

### Parameters
- **limit** (Optional[bool]) - Optional - The number of threads to retrieve.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve archived channels before the given date or ID.

### Yields
- **Thread** - The archived threads.
```

--------------------------------

### Subclassing and Using ActionRow

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates how to create a custom ActionRow subclass with decorated components and how to integrate it directly into a LayoutView.

```python
# you can subclass it and add components with the decorators
class MyActionRow(ui.ActionRow):
    @ui.button(label="Click Me!")
    async def click_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You clicked me!")


# or use it directly on LayoutView
class MyView(ui.LayoutView):
    row = ui.ActionRow()
    # or you can use your subclass:
    # row = MyActionRow()

    # you can add items with row.button and row.select
    @row.button(label="A button!")
    async def row_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You clicked a button!")
```

--------------------------------

### Migrate Extension Loading

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Demonstrates moving extension loading from the global scope to the setup_hook method or using an async context manager.

```python
# before
bot.load_extension("my_extension")


# after using setup_hook
class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("my_extension")


# after using async_with
async def main():
    async with bot:
        await bot.load_extension("my_extension")
        await bot.start(TOKEN)


asyncio.run(main())
```

--------------------------------

### Iterate over reaction users

Source: https://discordpy.readthedocs.io/en/latest/api.html

Asynchronously iterate over users who reacted to a message. Note that this can be memory-intensive for large reaction counts.

```python
async for user in reaction.users():
    await channel.send(f"{user} has reacted with {reaction.emoji}!")
```

--------------------------------

### Send message to a channel

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Fetch a channel by ID and send a message to it.

```python
channel = client.get_channel(12324234183172)
await channel.send("hello")
```

--------------------------------

### Flatten History to List

Source: https://discordpy.readthedocs.io/en/latest/api.html

Collect messages from channel history into a list using an asynchronous list comprehension.

```python
messages = [message async for message in channel.history(limit=123)]
# messages is now a list of Message...
```

--------------------------------

### set_permissions(target, *, overwrite=..., reason=None, **permissions)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the channel specific permission overwrites for a target in the channel.

```APIDOC
## set_permissions(target, *, overwrite=..., reason=None, **permissions)

### Description
Sets the channel specific permission overwrites for a target in the channel. This function is a coroutine and requires manage_roles permission.

### Parameters
- **target** (Union[Member, Role]) - Required - The target member or role.
- **overwrite** (Optional[PermissionOverwrite]) - Optional - The permission overwrite object. If None, overwrites are deleted.
- **reason** (Optional[str]) - Optional - The reason for the change.
- **permissions** (dict) - Optional - Keyword arguments denoting Permissions attributes.
```

--------------------------------

### Invoke a command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands are invoked by the user using the configured prefix followed by the command name and arguments.

```text
$foo abc
```

--------------------------------

### pong()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Pongs the ping interaction.

```APIDOC
## pong()

### Description
Pongs the ping interaction. This should rarely be used.
```

--------------------------------

### Retrieve pinned messages

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Access pinned messages in a channel using an asynchronous iterator.

```python
counter = 0
async for message in channel.pins(limit=250):
    counter += 1
```

```python
messages = [message async for message in channel.pins(limit=50)]
# messages is now a list of Message...
```

--------------------------------

### Registering global command hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use before_invoke and after_invoke decorators on the bot instance to execute logic globally for all commands.

```python
@bot.before_invoke
async def before_any_command(ctx):
    # do something before a command is called
    pass


@bot.after_invoke
async def after_any_command(ctx):
    # do something after a command is called
    pass
```

--------------------------------

### add_roles(*roles, reason=None, atomic=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Gives the member a number of roles. Requires manage_roles permission.

```APIDOC
## add_roles(*roles, reason=None, atomic=True)

### Description
Gives the member a number of Roles. You must have manage_roles to use this, and the added Roles must appear lower in the list of roles than the highest role of the client.

### Parameters
- **roles** (abc.Snowflake) - Required - An argument list of Snowflake representing a Role to give to the member.
- **reason** (Optional[str]) - Optional - The reason for adding these roles. Shows up on the audit log.
- **atomic** (bool) - Optional - Whether to atomically add roles.
```

--------------------------------

### send(content=None, *, ...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that sends a message to the destination with the provided content.

```APIDOC
## await send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, ephemeral=False, silent=False, poll=None)

### Description
Sends a message to the destination with the content given. For interaction based contexts, this handles initial responses, followup messages, or regular sends if the interaction has expired.

### Parameters
- **content** (str) - Optional - The message content.
- **tts** (bool) - Optional - Whether the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed to send.
- **embeds** (List[Embed]) - Optional - A list of rich embeds to send.
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload.
- **ephemeral** (bool) - Optional - Whether the message is visible only to the user.
```

--------------------------------

### Handle presence updates separately

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Presence updates have been moved from on_member_update to the new on_presence_update event.

```python
# before
@client.event
async def on_member_update(self, before, after):
    if before.nick != after.nick:
        await nick_changed(before, after)
    if before.status != after.status:
        await status_changed(before, after)


# after
@client.event
async def on_member_update(self, before, after):
    if before.nick != after.nick:
        await nick_changed(before, after)


@client.event
async def on_presence_update(self, before, after):
    if before.status != after.status:
        await status_changed(before, after)
```

--------------------------------

### Role.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the role with the provided parameters. This is a coroutine that requires the 'manage_roles' permission.

```APIDOC
## await Role.edit(**fields)

### Description
Edits the role. You must have `manage_roles` permission to perform this action. All fields are optional.

### Parameters
- **name** (str) - Optional - The new name of the role.
- **permissions** (Permissions) - Optional - The new permissions for the role.
- **colour** (Union[int, Colour]) - Optional - The new primary colour of the role.
- **color** (Union[int, Colour]) - Optional - Alias for colour.
- **hoist** (bool) - Optional - Whether the role is displayed separately.
- **display_icon** (Union[Asset, str]) - Optional - The new display icon for the role.
- **mentionable** (bool) - Optional - Whether the role can be mentioned.
- **position** (int) - Optional - The new position of the role.
- **reason** (str) - Optional - The reason for the audit log.
- **secondary_color** (Colour) - Optional - The new secondary colour.
- **tertiary_color** (Colour) - Optional - The new tertiary colour.

### Returns
- **Role** - The newly edited role object.
```

--------------------------------

### Flatten reaction users into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Collect all users who reacted into a list to perform operations like random selection. This requires loading all users into memory.

```python
users = [user async for user in reaction.users()]
# users is now a list of User...
winner = random.choice(users)
await channel.send(f"{winner} has won the raffle.")
```

--------------------------------

### @discord.ext.commands.dm_only()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A check that indicates the command must only be used in a DM context.

```APIDOC
## @discord.ext.commands.dm_only()

### Description
A `check()` that indicates this command must only be used in a DM context. Only private messages are allowed when using the command.
```

--------------------------------

### Translator.load()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

An asynchronous setup function for initializing the translation system. This is invoked when a translator is set on a CommandTree.

```APIDOC
## await Translator.load()

### Description
An asynchronous setup function for loading the translation system. The default implementation does nothing.

### Method
Coroutine

### Usage
This is invoked when `CommandTree.set_translator()` is called.
```

--------------------------------

### @discord.app_commands.guild_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates a command should be installed in guilds.

```APIDOC
## @discord.app_commands.guild_install()

### Description
Indicates that this command should be installed in guilds. Verified server-side; ignored in subcommands.
```

--------------------------------

### Migrating channel history iteration

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replaces manual list appending with asynchronous list comprehensions for channel history.

```python
# before
content_of_messages = []
async for content in channel.history().map(lambda m: m.content):
    content_of_messages.append(content)

# after
content_of_messages = [message.content async for message in channel.history()]
```

--------------------------------

### Retrieve guild and channel by name

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use discord.utils.get to find objects by their attributes, ensuring to check for None before accessing properties.

```python
guild = discord.utils.get(client.guilds, name="My Server")

# make sure to check if it's found
if guild is not None:
    # find a channel by name
    channel = discord.utils.get(guild.text_channels, name="cool-channel")
```

--------------------------------

### Implement a custom HelpCommand within a Cog

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates how to subclass MinimalHelpCommand and bind it to a Cog, ensuring the help command is restored when the cog is unloaded.

```python
class MyHelpCommand(commands.MinimalHelpCommand):
    def get_command_signature(self, command):
        return "{0.clean_prefix}{1.qualified_name} {1.signature}".format(self, command)


class MyCog(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command
```

--------------------------------

### follow

Source: https://discordpy.readthedocs.io/en/latest/api.html

Follows a news channel using a webhook.

```APIDOC
## follow(destination, reason)

### Description
Follows a channel using a webhook. Only news channels can be followed. This is a coroutine.

### Parameters
- **destination** (TextChannel) - Required - The channel you would like to follow from.
- **reason** (Optional[str]) - Optional - The reason for following the channel.

### Returns
- Webhook - The created webhook.
```

--------------------------------

### discord.on_interaction

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an interaction happened.

```APIDOC
## discord.on_interaction(interaction)

### Description
Called when an interaction happened. This currently happens due to slash command invocations or components being used.

### Parameters
- **interaction** (Interaction) - The interaction data.
```

--------------------------------

### Attach a select menu to a view

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the @discord.ui.select decorator to define a select menu within a discord.ui.View subclass. The callback receives the interaction and the select instance, allowing access to selected values.

```python
class View(discord.ui.View):
    @discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f"You selected {select.values[0].mention}")
```

--------------------------------

### wait_until_ready()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Waits until the client’s internal cache is all ready.

```APIDOC
## wait_until_ready()

### Description
Waits until the client’s internal cache is all ready. Note: Calling this inside setup_hook() can lead to a deadlock.
```

--------------------------------

### Member.timeout

Source: https://discordpy.readthedocs.io/en/latest/api.html

Applies a timeout to a member.

```APIDOC
## Member.timeout(until, reason=None)

### Description
Applies a time out to a member until the specified date time or for the given datetime.timedelta.

### Parameters
- **until** (datetime.datetime or datetime.timedelta) - Required - The duration or expiration date of the timeout.
- **reason** (Optional[str]) - Optional - The reason for the timeout.
```

--------------------------------

### send()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the member. This method supports various parameters including embeds, files, stickers, and polls.

```APIDOC
## send(content=None, tts=False, embed=None, embeds=None, file=None, files=None, nonce=None, delete_after=None, allowed_mentions=None, reference=None, mention_author=None, view=None, stickers=None, suppress_embeds=False, silent=False, poll=None)

### Description
Sends a message to the member. Returns the sent Message object.

### Parameters
- **content** (str) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload (max 10).
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload (max 10).
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the message to which you are referencing.
- **mention_author** (bool) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of stickers to upload (max 3).
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### Configure custom sharding

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Specify shard counts and specific shard IDs for granular control over sharding behavior.

```python
# launch 10 shards regardless
client = discord.AutoShardedClient(shard_count=10)

# launch specific shard IDs in this process
client = discord.AutoShardedClient(shard_count=10, shard_ids=(1, 2, 5, 6))
```

--------------------------------

### add_user

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a user to the thread.

```APIDOC
## add_user(user)

### Description
Adds a user to this thread. Requires send_messages_in_threads; private threads may require manage_messages.

### Parameters
- **user** (abc.Snowflake) - Required - The user to add to the thread.

### Raises
- **Forbidden** - You do not have permissions to add the user.
- **HTTPException** - Adding the user failed.
```

--------------------------------

### @discord.app_commands.choices

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Instructs parameters to use a specific set of choices for slash command inputs.

```APIDOC
## @discord.app_commands.choices

### Description
Instructs the given parameters by their name to use the given choices for their choices.

### Parameters
- **parameters** (Any) - Required - The choices of the parameters.
```

--------------------------------

### permissions_for(obj, /)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for the Member or Role.

```APIDOC
## permissions_for(obj, /)

### Description
Handles permission resolution for the Member or Role, taking into account guild owner status, roles, channel overrides, and member timeouts.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for.
```

--------------------------------

### Member.kick

Source: https://discordpy.readthedocs.io/en/latest/api.html

Kicks the member from the guild. This is a coroutine.

```APIDOC
## await Member.kick(*, reason=None)

### Description
Kicks this member from the guild. This is a coroutine equivalent to Guild.kick().

### Parameters
- **reason** (str) - Optional - The reason for the kick.
```

--------------------------------

### StreamIntegration.sync

Source: https://discordpy.readthedocs.io/en/latest/api.html

Syncs a stream integration.

```APIDOC
## await StreamIntegration.sync()

### Description
Syncs the stream integration.
```

--------------------------------

### Migrating AsyncIterator.flatten()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replaces the flatten method with a list comprehension using async for.

```python
# before
users = await reaction.users().flatten()

# after
users = [user async for user in reaction.users()]
```

--------------------------------

### Integration.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the integration settings. Requires manage_guild permission.

```APIDOC
## await edit(expire_behaviour=..., expire_grace_period=..., enable_emoticons=...)

### Description
Edits the integration. You must have `manage_guild` to do this.

### Parameters
- **expire_behaviour** (ExpireBehaviour) - Optional - The behaviour when an integration subscription lapses.
- **expire_grace_period** (int) - Optional - The period (in days) where the integration will ignore lapsed subscriptions.
- **enable_emoticons** (bool) - Optional - Where emoticons should be synced for this integration (currently twitch only).

### Raises
- **Forbidden** - You do not have permission to edit the integration.
- **HTTPException** - Editing the guild failed.
- **TypeError** - expire_behaviour did not receive a ExpireBehaviour.
```

--------------------------------

### Define a basic command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands are defined by decorating a function with @bot.command(). The first parameter must always be the context object, ctx.

```python
@bot.command()
async def foo(ctx, arg):
    await ctx.send(arg)
```

--------------------------------

### AppCommand.fetch_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves the command's permissions in a specific guild.

```APIDOC
## await fetch_permissions(guild)

### Description
Retrieves this command's permission in the guild.

### Parameters
- **guild** (Snowflake) - Required - The guild to retrieve the permissions from.

### Returns
- **GuildAppCommandPermissions** - An object representing the application command's permissions in the guild.
```

--------------------------------

### clear_items()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes all items from the view. This function returns the class instance to allow for fluent-style chaining.

```APIDOC
## clear_items()

### Description
Removes all items from the view.
```

--------------------------------

### create_automod_rule()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an automod rule for the guild. Requires Permissions.manage_guild.

```APIDOC
## create_automod_rule()

### Description
Create an automod rule. Requires `Permissions.manage_guild`.

### Parameters
- **name** (str) - Required - The name of the automod rule.
- **event_type** (AutoModRuleEventType) - Required - The type of event that the automod rule will trigger on.
- **trigger** (AutoModTrigger) - Required - The trigger that will trigger the automod rule.
- **actions** (List[AutoModRuleAction]) - Required - The actions that will be taken when the automod rule is triggered.
- **enabled** (bool) - Optional - Whether the automod rule is enabled. Defaults to False.
- **exempt_roles** (Sequence[abc.Snowflake]) - Optional - A list of roles that will be exempt from the automod rule.
- **exempt_channels** (Sequence[abc.Snowflake]) - Optional - A list of channels that will be exempt from the automod rule.
- **reason** (str) - Optional - The reason for creating this automod rule.
```

--------------------------------

### fetch_premium_sticker_packs

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves all available premium sticker packs.

```APIDOC
## fetch_premium_sticker_packs()

### Description
Retrieves all available premium sticker packs.

### Returns
- **List[StickerPack]** - All available premium sticker packs.
```

--------------------------------

### purge(*, limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Purges a list of messages that meet the criteria given by the predicate check. Requires manage_messages and read_message_history permissions.

```APIDOC
## purge(*, limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

### Description
Purges a list of messages that meet the criteria given by the predicate check. If a check is not provided then all messages are deleted without discrimination.

### Parameters
- **limit** (int) - Optional - The number of messages to search through.
- **check** (callable) - Optional - A predicate to check if a message should be deleted.
- **reason** (Optional[str]) - Optional - The reason for purging the messages.
```

--------------------------------

### Register a command with intents

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands require the message_content intent to be enabled in the bot instance. This example demonstrates the standard setup for a bot using the commands extension.

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.command()
async def test(ctx):
    pass
```

--------------------------------

### is_timed_out()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the member is currently timed out.

```APIDOC
## is_timed_out()

### Description
Returns whether this member is timed out.

### Returns
- **bool** - True if the member is timed out, False otherwise.
```

--------------------------------

### SyncWebhook.partial

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial SyncWebhook object using an ID and token.

```APIDOC
## SyncWebhook.partial(id, token, *, session=..., bot_token=None)

### Description
Creates a partial SyncWebhook object. A partial SyncWebhook is a webhook object containing only an ID and a token.

### Parameters
- **id** (int) - Required - The ID of the webhook.
- **token** (str) - Required - The authentication token of the webhook.
- **session** (requests.Session) - Optional - The session to use for requests.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.
```

--------------------------------

### remove_tags

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes the given forum tags from a thread. Requires manage_threads permission or thread ownership.

```APIDOC
## remove_tags(*tags, reason=None)

### Description
Removes the given forum tags from a thread. The parent channel must be a ForumChannel.

### Parameters
- **tags** (abc.Snowflake) - Required - An argument list of abc.Snowflake representing a ForumTag to remove.
- **reason** (Optional[str]) - Optional - The reason for removing these tags.

### Raises
- **Forbidden** - You do not have permissions to remove these tags.
- **HTTPException** - Removing tags failed.
```

--------------------------------

### ForumChannel.overwrites_for

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the channel-specific overwrites for a member or a role.

```APIDOC
## overwrites_for(obj)

### Description
Returns the channel-specific overwrites for a member or a role.

### Parameters
- **obj** (Union[Role, User, Object]) - Required - The role or user to get overwrites for.

### Returns
- **PermissionOverwrite** - The permission overwrites for this object.
```

--------------------------------

### Update Guild.bans usage

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Shows the transition from a direct list return to an asynchronous iterator for guild bans.

```python
# before

bans = await guild.bans()

# after
async for ban in guild.bans(limit=1000):
    ...
```

--------------------------------

### move(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine to move a channel relative to other channels. Requires manage_channels permission.

```APIDOC
## move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. If exact position movement is required, `edit` should be used instead.

### Parameters
- **beginning** (bool) - Optional - Whether to move the channel to the beginning of the channel list.
- **end** (bool) - Optional - Whether to move the channel to the end of the channel list.
- **before** (Snowflake) - Optional - Move the channel before the given channel.
- **after** (Snowflake) - Optional - Move the channel after the given channel.
- **offset** (int) - Optional - The number of channels to offset the move by.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync the permissions with the category.
- **reason** (str) - Optional - The reason for the move.
```

--------------------------------

### AutoShardedClient._edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the application info. This function is a coroutine.

```APIDOC
## _edit(reason=..., custom_install_url=..., description=..., role_connections_verification_url=..., install_params_scopes=..., install_params_permissions=..., flags=..., icon=..., cover_image=..., interactions_endpoint_url=..., tags=..., guild_install_scopes=..., guild_install_permissions=..., user_install_scopes=..., user_install_permissions=...)

### Description
Edits the application info. This function is a coroutine.

### Parameters
- **custom_install_url** (Optional[str]) - Optional - The new custom authorization URL for the application.
- **description** (Optional[str]) - Optional - The new application description.
- **role_connections_verification_url** (Optional[str]) - Optional - The new application’s connection verification URL.
- **install_params_scopes** (Optional[List[str]]) - Optional - The new list of OAuth2 scopes of the install_params.
- **install_params_permissions** (Optional[Permissions]) - Optional - The new permissions of the install_params.
- **flags** (Optional[ApplicationFlags]) - Optional - The new application’s flags.
- **icon** (Optional[bytes]) - Optional - The new application’s icon as a bytes-like object.
- **cover_image** (Optional[bytes]) - Optional - The new application’s cover image as a bytes-like object.
- **interactions_endpoint_url** (Optional[str]) - Optional - The new interactions endpoint url of the application.
- **tags** (Optional[List[str]]) - Optional - The new list of tags describing the functionality of the application.
- **guild_install_scopes** (Optional[List[str]]) - Optional - The new list of OAuth2 scopes of the default guild installation context.
- **guild_install_permissions** (Optional[Permissions]) - Optional - The new permissions of the default guild installation context.
- **user_install_scopes** (Optional[List[str]]) - Optional - The new list of OAuth2 scopes of the default user installation context.
- **user_install_permissions** (Optional[Permissions]) - Optional - The new permissions of the default user installation context.
- **reason** (Optional[str]) - Optional - The reason for editing the application.

### Returns
- **AppInfo** - The newly updated application info.
```

--------------------------------

### Retrieve elements using discord.utils.get

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the first element in an iterable matching all specified attributes, supporting nested attribute lookups via double underscores.

```python
member = discord.utils.get(message.guild.members, name="Foo")
```

```python
channel = discord.utils.get(guild.voice_channels, name="Foo", bitrate=64000)
```

```python
channel = discord.utils.get(client.get_all_channels(), guild__name="Cool", name="general")
```

--------------------------------

### await clone(name=None, category=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the current channel, creating a new one with the same properties. Requires manage_channels permission.

```APIDOC
## await clone(name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. You must have `manage_channels` to do this.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel. If not provided, defaults to this channel name.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to. This parameter is ignored if cloning a category channel.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel. Shows up on the audit log.

### Returns
- **abc.GuildChannel** - The channel that was created.
```

--------------------------------

### reply(content=None, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that acts as a shortcut to send() to reply to the Message referenced by this context.

```APIDOC
## await reply(content=None, **kwargs)

### Description
A shortcut method to send() to reply to the Message referenced by this context. For interaction based contexts, this is the same as send().

### Parameters
- **content** (str) - Optional - The content of the message to send.
- **kwargs** (dict) - Optional - Additional arguments passed to the send method.

### Returns
- **Message** - The message that was sent.

### Raises
- **HTTPException** - Sending the message failed.
- **Forbidden** - You do not have the proper permissions to send the message.
- **ValueError** - The files list is not of the appropriate size.
- **TypeError** - You specified both file and files.
```

--------------------------------

### add_dynamic_items

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers DynamicItem classes for persistent listening.

```APIDOC
## add_dynamic_items(*items)

### Description
Registers `DynamicItem` classes for persistent listening. This method accepts class types rather than instances.

### Parameters
- **items** (Type[DynamicItem]) - Required - The classes of dynamic items to add.
```

--------------------------------

### Button.interaction_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine callback that checks whether the interaction callback should be processed.

```APIDOC
## await interaction_check(interaction)

### Description
A callback that is called when an interaction happens within this item to check if the callback should be processed. Returns True by default.

### Parameters
- **interaction** (Interaction) - The interaction that occurred.

### Returns
- **bool** - Whether the callback should be called.
```

--------------------------------

### Purge messages in a thread

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes messages matching a specific condition within a thread. Requires manage_messages and read_message_history permissions.

```python
def is_me(m):
    return m.author == client.user


deleted = await thread.purge(limit=100, check=is_me)
await thread.send(f"Deleted {len(deleted)} message(s)")
```

--------------------------------

### Guild.edit()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the guild settings. Requires manage_guild permissions.

```APIDOC
## await Guild.edit(**kwargs)

### Description
Edits the guild. You must have `manage_guild` to edit the guild.

### Parameters
- **name** (str) - Optional - The new name of the guild.
- **description** (Optional[str]) - Optional - The new description of the guild.
- **icon** (bytes) - Optional - A bytes-like object representing the icon.
- **banner** (bytes) - Optional - A bytes-like object representing the banner.
- **splash** (bytes) - Optional - A bytes-like object representing the invite splash.
- **discovery_splash** (bytes) - Optional - A bytes-like object representing the discovery splash.
```

--------------------------------

### fetch_channels()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all channels associated with the guild via an API call.

```APIDOC
## await fetch_channels()

### Description
Retrieves all `abc.GuildChannel` that the guild has.

### Returns
- **Sequence[abc.GuildChannel]** - All channels in the guild.
```

--------------------------------

### fetch_member

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a ThreadMember for a given user ID.

```APIDOC
## fetch_member(user_id)

### Description
Retrieves a ThreadMember for the given user ID.

### Parameters
- **user_id** (int) - Required - The user ID to fetch.

### Returns
- **ThreadMember** - The thread member from the user ID.

### Raises
- **NotFound** - The specified user is not a member.
- **HTTPException** - Retrieving the member failed.
```

--------------------------------

### Fetch Guilds Asynchronously

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves an asynchronous iterator for guilds. Note that this is an API call and returns limited guild attributes.

```python
async for guild in client.fetch_guilds(limit=150):
    print(guild.name)
```

```python
guilds = [guild async for guild in client.fetch_guilds(limit=150)]
# guilds is now a list of Guild...
```

--------------------------------

### Wait for a message event

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses wait_for to pause execution until a specific message matching the check function is received.

```python
@client.event
async def on_message(message):
    if message.content.startswith("$greet"):
        channel = message.channel
        await channel.send("Say hello!")

        def check(m):
            return m.content == "hello" and m.channel == channel

        msg = await client.wait_for("message", check=check)
        await channel.send(f"Hello {msg.author}!")
```

--------------------------------

### Initialize Discord UI Module

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Basic imports required to utilize the discord.ui module components.

```python
import discord
from discord import ui
```

--------------------------------

### Restrict command access with has_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses the has_permissions check to verify that the user holds specific Discord permissions.

```python
@tree.command()
@app_commands.checks.has_permissions(manage_messages=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("You can manage messages.")
```

--------------------------------

### fetch_sticker

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a Sticker with the specified ID.

```APIDOC
## await fetch_sticker(sticker_id)

### Description
Retrieves a Sticker with the specified ID.

### Parameters
- **sticker_id** (int) - Required - The sticker ID.

### Returns
- **Union[StandardSticker, GuildSticker]** - The sticker you requested.

### Raises
- **HTTPException** - Retrieving the sticker failed.
- **NotFound** - Invalid sticker ID.
```

--------------------------------

### Update model edit patterns

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Model edit methods now return a new instance instead of modifying the object in-place to prevent race conditions.

```python
# before
await member.edit(nick="new nick")
await member.send(f"Your new nick is {member.nick}")

# after
updated_member = await member.edit(nick="new nick")
await member.send(f"Your new nick is {updated_member.nick}")
```

--------------------------------

### active_threads()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a list of active threads that the client can access.

```APIDOC
## await active_threads()

### Description
Returns a list of active `Thread` that the client can access, including both private and public threads.

### Returns
- **List[Thread]** - The active threads.
```

--------------------------------

### @discord.app_commands.default_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that sets the default permissions required to execute a command.

```APIDOC
## @discord.app_commands.default_permissions(perms_obj=None, **perms)

### Description
Sets the default permissions needed to execute a command. This serves as a hint to the Discord client and can be overridden by administrators.

### Parameters
- **perms_obj** (Permissions) - Optional - A permissions object as a positional argument.
- **perms** (bool) - Optional - Keyword arguments denoting specific permissions to set as default.
```

--------------------------------

### CategoryChannel.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the category channel. Requires manage_channels permission.

```APIDOC
## await edit(**options)

### Description
Edits the channel. You must have `manage_channels` to do this.

### Parameters
- **name** (str) - Optional - The new category’s name.
- **position** (int) - Optional - The new category’s position.
- **nsfw** (bool) - Optional - To mark the category as NSFW or not.
- **reason** (Optional[str]) - Optional - The reason for editing this category. Shows up on the audit log.
- **overwrites** (Mapping) - Optional - A Mapping of target (either a role or a member) to PermissionOverwrite to apply to the channel.

### Returns
- **CategoryChannel** - The newly edited category channel. If the edit was only positional then None is returned instead.
```

--------------------------------

### on_error(interaction, error)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine callback that is called when on_submit() fails with an error.

```APIDOC
## await on_error(interaction, error)

### Parameters
- **interaction** (Interaction) - Required - The interaction that led to the failure.
- **error** (Exception) - Required - The exception that was raised.
```

--------------------------------

### walk_commands()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

An iterator that recursively walks through all commands and subcommands.

```APIDOC
## walk_commands()

### Description
An iterator that recursively walks through all commands and subcommands.

### Yields
- **Union[Command, Group]** - A command or group from the internal list of commands.
```

--------------------------------

### discord.ui.RoleSelect

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of predefined options with the current roles of the guild.

```APIDOC
## class discord.ui.RoleSelect

### Description
Represents a UI select menu with a list of predefined options with the current roles of the guild. Note that if used in a private message, no roles will be displayed.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu. Max 100 characters.
- **placeholder** (Optional[str]) - Optional - Placeholder text. Max 150 characters.
- **min_values** (int) - Optional - Minimum items to choose. Defaults to 1 (0-25).
- **max_values** (int) - Optional - Maximum items to choose. Defaults to 1 (1-25).
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required (only for modals).
- **default_values** (Sequence[Snowflake]) - Optional - List of roles selected by default.
- **row** (Optional[int]) - Optional - Relative row index (0-4).
- **id** (Optional[int]) - Optional - Unique ID of the component.

### Methods
- **callback(interaction)**: Coroutine called when the select menu is interacted with.
- **interaction_check(interaction)**: Coroutine to check if the callback should be processed.
```

--------------------------------

### Disable UI components on timeout

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Loop through view children in on_timeout and edit the original message to reflect the disabled state.

```python
class MyView(discord.ui.View):
    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True

        # Step 3
        await self.message.edit(view=self)

    @discord.ui.button(label="Example")
    async def example_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Hello!", ephemeral=True)


@bot.command()
async def timeout_example(ctx):
    """An example to showcase disabling buttons on timing out"""
    view = MyView()
    # Step 1
    view.message = await ctx.send("Press me!", view=view)
```

--------------------------------

### send_message(content=None, *, embed=..., embeds=..., file=..., files=..., view=..., tts=False, ephemeral=False, allowed_mentions=..., suppress_embeds=False, silent=False, delete_after=None, poll=...)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to the interaction by sending a message.

```APIDOC
## send_message(...)

### Description
Responds to this interaction by sending a message.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message to send.
- **embeds** (List[Embed]) - Optional - A list of embeds to send with the content.
- **embed** (Embed) - Optional - The rich embed for the content to send.
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - The view to send with the message.
- **ephemeral** (bool) - Optional - Indicates if the message should only be visible to the user who started the interaction.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed in this message.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications for the message.
- **delete_after** (float) - Optional - The number of seconds to wait before deleting the message.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### pins

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of the pinned messages in the channel.

```APIDOC
## pins(limit=50, before=None, oldest_first=False)

### Description
Retrieves an asynchronous iterator of the pinned messages in the channel. Requires view_channel and read_message_history permissions.

### Parameters
- **limit** (int) - Optional - The number of messages to retrieve (default 50).
- **before** (Any) - Optional - Retrieve messages before this point.
- **oldest_first** (bool) - Optional - Whether to return messages in oldest-first order.
```

--------------------------------

### ForumChannel.get_thread

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a thread within the forum by its ID.

```APIDOC
## get_thread(thread_id)

### Description
Returns a thread with the given ID. Note that this does not always retrieve archived threads as they are not retained in the internal cache.

### Parameters
- **thread_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Thread]** - The returned thread or None if not found.
```

--------------------------------

### Combine Greedy and Optional converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Mixing Greedy with Optional allows for flexible command invocation syntaxes.

```python
import typing


@bot.command()
async def ban(ctx, members: commands.Greedy[discord.Member], delete_days: typing.Optional[int] = 0, *, reason: str):
    """Mass bans members with an optional delete_days parameter"""
    delete_seconds = delete_days * 86400  # one day
    for member in members:
        await member.ban(delete_message_seconds=delete_seconds, reason=reason)
```

```text
$ban @Member @Member2 spam bot
$ban @Member @Member2 7 spam bot
$ban @Member spam

```

--------------------------------

### discord.on_guild_integrations_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever an integration is created, modified, or removed from a guild. Requires Intents.integrations.

```APIDOC
## discord.on_guild_integrations_update(guild)

### Description
Called whenever an integration is created, modified, or removed from a guild. This requires Intents.integrations to be enabled.

### Parameters
- **guild** (Guild) - The guild that had its integrations updated.
```

--------------------------------

### Retrieving next item from iterator

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Uses anext() or __anext__() to fetch the next item without a full loop.

```python
# before
it = channel.history()
first = await it.next()
if first.content == "do not iterate":
    return
async for message in it:
    ...

# after
it = channel.history()
first = await anext(it)  # await it.__anext__() on Python<3.10
if first.content == "do not iterate":
    return
async for message in it:
    ...
```

--------------------------------

### @discord.app_commands.checks.has_role(item)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member invoking the command has a specific role by name or ID.

```APIDOC
## @discord.app_commands.checks.has_role(item)

### Description
A check that verifies if the member invoking the command has the role specified via the name or ID. Raises `MissingRole` or `NoPrivateMessage` on failure.

### Parameters
- **item** (Union[int, str]) - Required - The name or ID of the role to check.
```

--------------------------------

### Bot.start

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A shorthand coroutine for login() + connect().

```APIDOC
## Bot.start(token, *, reconnect=True)

### Description
A shorthand coroutine for login() + connect().

### Parameters
- **token** (str) - Required - The authentication token.
- **reconnect** (bool) - Optional - If we should attempt reconnecting.
```

--------------------------------

### Wait for a reaction event

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Handle multiple return values from wait_for by unpacking the tuple.

```python
reaction, user = await client.wait_for("reaction_add", check=lambda r, u: u.id == 176995180300206080)

# use user and reaction
```

--------------------------------

### await edit(**fields)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the message content, embeds, attachments, or view. Returns the newly edited message.

```APIDOC
## await edit(**fields)

### Description
Edits the message. The content must be able to be transformed into a string via str(content).

### Parameters
- **content** (Optional[str]) - Optional - The new content to replace the message with.
- **embed** (Optional[Embed]) - Optional - The new embed to replace the original with.
- **embeds** (List[Embed]) - Optional - The new embeds to replace the original with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **suppress** (bool) - Optional - Whether to suppress embeds for the message.
- **delete_after** (Optional[float]) - Optional - Number of seconds to wait before deleting the message.
- **allowed_mentions** (Optional[AllowedMentions]) - Optional - Controls the mentions being processed.
- **view** (Optional[Union[View, LayoutView]]) - Optional - The updated view to update this message with.

### Returns
- **Message** - The newly edited message.
```

--------------------------------

### Messageable.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager to send a typing indicator to the destination.

```APIDOC
## async with Messageable.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination. If used with 'async with', it lasts for the duration of the block. If awaited, it lasts for 10 seconds.
```

--------------------------------

### View.add_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the view.

```APIDOC
## add_item(item)

### Description
Adds an item to the view. Returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to add to the view.
```

--------------------------------

### Attach a View to an Interaction Response

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use this pattern to associate a UI view with a message sent in response to an interaction.

```python
@tree.command()
async def more_timeout_example(interaction):
    """Another example to showcase disabling buttons on timing out"""
    view = MyView()
    callback = await interaction.response.send_message("Press me!", view=view)

    # Step 1
    resource = callback.resource
    # making sure it's an interaction response message
    if isinstance(resource, discord.InteractionMessage):
        view.message = resource
```

--------------------------------

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a given Member or Role, considering guild owner status, roles, channel overrides, and member timeouts.

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for the `Member` or `Role`. This function takes into consideration guild owner status, roles, channel overrides, member overrides, implicit permissions, member timeout, and user installed apps.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for.
```

--------------------------------

### Iterating over channel history

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use asynchronous iteration to process messages from a channel history.

```python
async for message in channel.history():
    print(message)
```

--------------------------------

### permissions_for(obj, /)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for the Member or Role, considering guild owner status, roles, and channel/member overrides.

```APIDOC
## permissions_for(obj, /)

### Description
Handles permission resolution for the Member or Role. This function takes into consideration guild owner status, roles, channel overrides, member overrides, implicit permissions, member timeout, and user installed apps.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for.

### Returns
- **Permissions** - The resolved permissions for the member or role.
```

--------------------------------

### Wait for a reaction event

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses wait_for with a timeout to handle a specific reaction from the message author.

```python
@client.event
async def on_message(message):
    if message.content.startswith("$thumb"):
        channel = message.channel
        await channel.send("Send me that 👍 reaction, mate")

        def check(reaction, user):
            return user == message.author and str(reaction.emoji) == "👍"

        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await channel.send("👎")
        else:
            await channel.send("👍")
```

--------------------------------

### Register a call-once global check with @bot.check_once

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a global check that is executed only once per invoke call, bypassing repeated checks during command execution.

```python
@bot.check_once
def whitelist(ctx):
    return ctx.message.author.id in my_whitelist
```

--------------------------------

### Migrating AsyncIterator.find()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replaces the instance method with discord.utils.find().

```python
def predicate(event):
    return event.reason is not None


# before
event = await guild.audit_logs().find(predicate)

# after
event = await discord.utils.find(predicate, guild.audit_logs())
```

--------------------------------

### discord.on_automod_rule_create(rule)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event triggered when an AutoMod rule is created.

```APIDOC
## discord.on_automod_rule_create(rule)

### Description
Called when an `AutoModRule` is created. Requires `Intents.auto_moderation_configuration` and `manage_guild` permission.

### Parameters
- **rule** (AutoModRule) - Required - The rule that was created.
```

--------------------------------

### delete_messages(messages, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bulk deletes a list of messages. Cannot delete more than 100 messages or messages older than 14 days. Requires manage_messages permission.

```APIDOC
## delete_messages(messages, *, reason=None)

### Description
Deletes a list of messages. This is similar to Message.delete() except it bulk deletes multiple messages.

### Parameters
- **messages** (Iterable[abc.Snowflake]) - Required - An iterable of messages denoting which ones to bulk delete.
- **reason** (Optional[str]) - Optional - The reason for deleting the messages.
```

--------------------------------

### PermissionOverwrite.update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bulk updates this permission overwrite object.

```APIDOC
## update(**kwargs)

### Description
Bulk updates this permission overwrite object using keyword arguments.

### Parameters
- **kwargs** (dict) - A list of key/value pairs to bulk update with.
```

--------------------------------

### Restrict command to owners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses check_any to allow execution if the user is either the bot owner or the guild owner.

```python
@bot.command()
@commands.check_any(commands.is_owner(), is_guild_owner())
async def only_for_owners(ctx):
    await ctx.send("Hello mister owner!")
```

--------------------------------

### Initialize AutoShardedClient

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use AutoShardedClient to handle sharding automatically within a single process.

```python
client = discord.AutoShardedClient()
```

--------------------------------

### AutoShardedClient.fetch_session_start_limits

Source: https://discordpy.readthedocs.io/en/latest/api.html

Get the session start limits for the bot.

```APIDOC
## await fetch_session_start_limits()

### Description
Get the session start limits. This is a coroutine.

### Returns
- **SessionStartLimits** - A class containing the session start limits.

### Raises
- **GatewayNotFound** - The gateway was unreachable.
```

--------------------------------

### Implement a dynamic cooldown for an app command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses a factory function to bypass cooldowns for specific users while applying a 10-second cooldown for everyone else.

```python
def cooldown_for_everyone_but_me(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
    if interaction.user.id == 80088516616269824:
        return None
    return app_commands.Cooldown(1, 10.0)


@tree.command()
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_but_me)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Hello")


@test.error
async def on_test_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
```

--------------------------------

### @client.event

Source: https://discordpy.readthedocs.io/en/latest/api.html

A decorator used to register a coroutine as an event listener.

```APIDOC
## @client.event

### Description
A decorator that registers a coroutine to listen for specific Discord gateway events. The decorated function must be a coroutine.

### Usage Example
```python
@client.event
async def on_ready():
    print('Ready!')
```

### Raises
- **TypeError** - Raised if the decorated function is not a coroutine.
```

--------------------------------

### Send a direct message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Send a DM to a specific user or respond to a message author.

```python
user = client.get_user(381870129706958858)
await user.send('👀')
```

```python
await message.author.send("👋")
```

--------------------------------

### Updating Converter classes

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Converter classes must now implement an asynchronous convert method accepting ctx and argument parameters.

```python
class MyConverter(commands.Converter):
    def convert(self):
        return self.ctx.message.server.me
```

```python
class MyConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.me
```

--------------------------------

### reply(content=None, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Replies to the interaction message.

```APIDOC
## reply(content=None, **kwargs)

### Description
A shortcut method to abc.Messageable.send() to reply to the Message. This is a coroutine.

### Returns
- **Message** - The message that was sent.

### Raises
- **HTTPException** - Sending failed.
- **Forbidden** - Insufficient permissions.
- **ValueError** - Invalid files list size.
- **TypeError** - Conflicting file arguments.
```

--------------------------------

### Member.request_to_speak

Source: https://discordpy.readthedocs.io/en/latest/api.html

Requests to speak in the connected stage channel.

```APIDOC
## Member.request_to_speak()

### Description
Request to speak in the connected channel. Only applies to stage channels.
```

--------------------------------

### Execute coroutine in player after function

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Uses asyncio.run_coroutine_threadsafe to safely execute a coroutine from the music player's non-async thread.

```python
def my_after(error):
    coro = some_channel.send("Song is done!")
    fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
    try:
        fut.result()
    except:
        # an error happened sending the message
        pass


voice.play(discord.FFmpegPCMAudio(url), after=my_after)
```

--------------------------------

### @discord.app_commands.check(predicate)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a custom check to an application command. The predicate must accept an Interaction object and return a boolean; if False, a CheckFailure exception is raised.

```APIDOC
## @discord.app_commands.check(predicate)

### Description
A decorator that adds a check to an application command. These checks should be predicates that take in a single parameter taking a `Interaction`. If the check returns a `False`-like value then during invocation a `CheckFailure` exception is raised.

### Parameters
- **predicate** (Callable[[Interaction], bool]) - Required - The predicate to check if the command should be invoked.
```

--------------------------------

### Create a UI Modal

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Inherit from ui.Modal to define a custom popup window with input fields and a submission handler.

```python
import discord
from discord import ui


class Questionnaire(ui.Modal, title="Questionnaire Response"):
    name = ui.Label(text="Name", component=ui.TextInput())
    answer = ui.Label(text="Answer", component=ui.TextInput(style=discord.TextStyle.paragraph))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Thanks for your response, {self.name.component.value}!", ephemeral=True)
```

--------------------------------

### Assigning Parameter Metadata

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates using parameter() to assist type checkers with custom converters and late binding.

```python
class SomeType:
    foo: int


class MyVeryCoolConverter(commands.Converter[SomeType]): ...  # implementation left as an exercise for the reader


@bot.command()
async def bar(ctx, cool_value: MyVeryCoolConverter):
    cool_value.foo  # type checker warns MyVeryCoolConverter has no value foo (uh-oh)
```

```python
@bot.command()
async def bar(ctx, cool_value: SomeType = commands.parameter(converter=MyVeryCoolConverter)):
    cool_value.foo  # no error (hurray)
```

```python
@bot.command()
async def wave(ctx, to: discord.User = commands.parameter(default=lambda ctx: ctx.author)):
    await ctx.send(f"Hello {to.mention} :wave:")
```

```python
@bot.command()
async def wave(ctx, to: discord.User = commands.Author):
    await ctx.send(f"Hello {to.mention} :wave:")
```

--------------------------------

### Purge messages with a check function

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes messages in a channel that satisfy a specific condition, such as messages sent by the bot.

```python
def is_me(m):
    return m.author == client.user


deleted = await channel.purge(limit=100, check=is_me)
await channel.send(f"Deleted {len(deleted)} message(s)")
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the thread.

```APIDOC
## delete(reason=None)

### Description
Deletes this thread. Requires manage_threads permission.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this thread.

### Raises
- **Forbidden** - You do not have permissions to delete this thread.
- **HTTPException** - Deleting the thread failed.
```

--------------------------------

### add_view

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a View for persistent listening.

```APIDOC
## add_view(view, *, message_id=None)

### Description
Registers a `View` for persistent listening. This should be used for views comprised of components that last longer than the program lifecycle.

### Parameters
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Required - The view to register.
- **message_id** (Optional[int]) - Optional - The message ID the view is attached to.
```

--------------------------------

### get_channel_or_thread(channel_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a channel or thread with the given ID.

```APIDOC
## get_channel_or_thread(channel_id)

### Description
Returns a channel or thread with the given ID.

### Parameters
- **channel_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Union[Thread, abc.GuildChannel]]** - The returned channel or thread or `None` if not found.
```

--------------------------------

### integrations

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a list of all integrations attached to the guild.

```APIDOC
## await integrations()

### Description
Returns a list of all integrations attached to the guild. You must have `manage_guild` to do this.
```

--------------------------------

### Implement Custom Exceptions for Robust Error Handling

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows how to derive from CommandError to provide specific feedback when a check fails.

```python
class NoPrivateMessages(commands.CheckFailure):
    pass


def guild_only():
    async def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessages("Hey no DMs!")
        return True

    return commands.check(predicate)


@bot.command()
@guild_only()
async def test(ctx):
    await ctx.send("Hey this is not a DM! Nice.")


@test.error
async def test_error(ctx, error):
    if isinstance(error, NoPrivateMessages):
        await ctx.send(error)
```

--------------------------------

### Copy Global Commands to a Guild

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use this method to replicate all global commands to a specific guild, typically for development purposes.

```python
tree.copy_global_to(guild=discord.Object(123456789012345678))
```

--------------------------------

### AppCommandThread.resolve()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Resolves the application command channel to the appropriate channel from the cache if it is available.

```APIDOC
## resolve()

### Description
Resolves the application command channel to the appropriate channel from cache if found.

### Returns
- **Optional[abc.GuildChannel]** - The resolved guild channel or None if not found in cache.
```

--------------------------------

### typing(ephemeral=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination. In interaction-based contexts, this is equivalent to a defer() call.

```APIDOC
## typing(ephemeral=False)

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is awaited. In an interaction based context, this is equivalent to a defer() call.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral. Only valid for interaction based contexts.
```

--------------------------------

### get_sticker(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a guild sticker from the cache by its ID.

```APIDOC
## get_sticker(id)

### Description
Returns a guild sticker with the given ID.

### Returns
- **GuildSticker** (Optional) - The sticker or None if not found.
```

--------------------------------

### remove_cog(name, /, *, guild=..., guilds=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a cog from the bot and returns it.

```APIDOC
## remove_cog(name, /, *, guild=..., guilds=...)

### Description
Removes a cog from the bot and returns it. All registered commands and event listeners associated with the cog are removed.

### Parameters
- **name** (str) - Required - The name of the cog to remove.
- **guild** (Optional[Snowflake]) - Optional - The guild where the cog group would be removed from.
- **guilds** (List[Snowflake]) - Optional - The guilds where the cog group would be removed from.
```

--------------------------------

### Handle commands with custom on_message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

When overriding on_message, call bot.process_commands to ensure commands continue to function.

```python
@bot.event
async def on_message(message):
    # do some extra stuff here

    await bot.process_commands(message)
```

--------------------------------

### get_scheduled_event(scheduled_event_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific scheduled event within the guild by its ID.

```APIDOC
## get_scheduled_event(scheduled_event_id)

### Description
Returns a scheduled event with the given ID.

### Parameters
- **scheduled_event_id** (int) - Required - The ID to search for.

### Returns
- **Optional[ScheduledEvent]** - The scheduled event or None if not found.
```

--------------------------------

### Upload files

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Upload single files, multiple files, or files from URLs using discord.File.

```python
await channel.send(file=discord.File("my_file.png"))
```

```python
with open("my_file.png", "rb") as fp:
    await channel.send(file=discord.File(fp, "new_filename.png"))
```

```python
my_files = [
    discord.File("result.zip"),
    discord.File("teaser_graph.png"),
]
await channel.send(files=my_files)
```

```python
import io
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get(my_url) as resp:
        if resp.status != 200:
            return await channel.send("Could not download file...")
        data = io.BytesIO(await resp.read())
        await channel.send(file=discord.File(data, "cool_image.png"))
```

--------------------------------

### webhooks

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the list of webhooks for the guild.

```APIDOC
## await webhooks()

### Description
Gets the list of webhooks from this guild. Requires manage_webhooks permission.

### Returns
- **List[Webhook]** - The webhooks for this guild.
```

--------------------------------

### Updating on_member_ban signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now receives the Guild object and a User or Member object.

```python
async def on_member_ban(member)
```

```python
async def on_member_ban(guild, user)
```

--------------------------------

### Subclassing Context

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates how to extend the default Context class with custom properties.

```python
class MyContext(commands.Context):
    @property
    def secret(self):
        return "my secret here"
```

--------------------------------

### filter_commands(commands, /, *, sort=False, key=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Filters an iterable of commands based on internal checks and visibility settings, with an optional sorting mechanism.

```APIDOC
## filter_commands(commands, /, *, sort=False, key=None)

### Description
Returns a filtered list of commands and optionally sorts them. This takes into account the `verify_checks` and `show_hidden` attributes.

### Parameters
- **commands** (Iterable[Command]) - Required - An iterable of commands that are getting filtered.
- **sort** (bool) - Optional - Whether to sort the result.
- **key** (Optional[Callable[[Command], Any]]) - Optional - An optional key function to pass to `sorted()`. If `sort` is True, this defaults to the command name.

### Returns
- **List[Command]** - A list of commands that passed the filter.
```

--------------------------------

### delete(delay=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the message. Requires manage_messages permission if deleting another user's message.

```APIDOC
## await delete(delay=None)

### Description
Deletes the message. Your own messages can be deleted without specific permissions, but deleting others' messages requires the `manage_messages` permission.

### Parameters
- **delay** (Optional[float]) - Optional - The number of seconds to wait in the background before deleting the message.
```

--------------------------------

### fetch_application_emojis

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves all emojis for the current application.

```APIDOC
## await fetch_application_emojis()

### Description
Retrieves all emojis for the current application.

### Raises
- **MissingApplicationID** - The application ID could not be found.
- **HTTPException** - Retrieving the emojis failed.

### Returns
- **List[Emoji]** - The list of emojis for the current application.
```

--------------------------------

### @discord.app_commands.allowed_contexts

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that restricts a command to specific contexts such as guilds, DMs, or private channels. This is verified server-side by Discord.

```APIDOC
## @discord.app_commands.allowed_contexts(guilds=..., dms=..., private_channels=...)

### Description
Indicates that a command can only be used in certain contexts. This is verified by Discord server-side and does not work on subcommands.

### Parameters
- **guilds** (bool) - Optional - Whether the command is allowed in guilds.
- **dms** (bool) - Optional - Whether the command is allowed in DMs.
- **private_channels** (bool) - Optional - Whether the command is allowed in private channels.
```

--------------------------------

### discord.on_member_join

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Member joins a Guild. Requires Intents.members.

```APIDOC
## discord.on_member_join(member)

### Description
Called when a Member joins a Guild. This requires Intents.members to be enabled.

### Parameters
- **member** (Member) - The member who joined.
```

--------------------------------

### estimate_pruned_members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Estimates how many members would be pruned from the guild without actually performing the action.

```APIDOC
## await estimate_pruned_members(*, days, roles=...)

### Description
Returns how many members it would prune from the guild had prune_members() been called.

### Parameters
- **days** (int) - Required - The number of days before counting as inactive.
- **roles** (List[abc.Snowflake]) - Optional - A list of roles to include in the estimate.

### Returns
- **Optional[int]** - The number of members estimated to be pruned.
```

--------------------------------

### LayoutView.add_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the view, supporting fluent-style chaining.

```APIDOC
## LayoutView.add_item(item)

### Description
Adds an item to the view. Returns the class instance for chaining.

### Parameters
- **item** (Item) - Required - The item to add to the view.

### Raises
- **TypeError** - If an Item was not passed.
- **ValueError** - If the maximum number of children is exceeded or the item is not allowed.
```

--------------------------------

### create_text_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel in the guild. This is a coroutine.

```APIDOC
## create_text_channel(name, *, reason=None, category=None, position=..., topic=..., slowmode_delay=..., nsfw=..., news=..., default_auto_archive_duration=..., default_thread_slowmode_delay=..., overwrites=...)

### Description
Creates a new text channel in the guild.

### Parameters
- **name** (str) - Required - The channel’s name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply upon creation.
- **category** (Optional[CategoryChannel]) - Optional - The category to place the channel under.
- **position** (int) - Optional - The position in the channel list.
- **topic** (str) - Optional - The new channel’s topic.
- **slowmode_delay** (int) - Optional - The slowmode rate limit in seconds.
- **nsfw** (bool) - Optional - Mark the channel as NSFW.
- **news** (bool) - Optional - Whether to create as a news channel.
- **default_auto_archive_duration** (int) - Optional - Default auto archive duration for threads.
- **default_thread_slowmode_delay** (int) - Optional - Default slowmode delay for threads.
- **reason** (Optional[str]) - Optional - The reason for creating this channel.

### Returns
- **TextChannel** - The channel that was just created.
```

--------------------------------

### fetch_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single message from the destination by its ID.

```APIDOC
## fetch_message(id)

### Description
Retrieves a single Message from the destination.

### Parameters
- **id** (int) - Required - The message ID to look for.

### Response
- **Message** - The message asked for.
```

--------------------------------

### autocomplete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by providing autocomplete choices.

```APIDOC
## autocomplete(choices)

### Description
Responds to this interaction by giving the user the choices they can use.

### Parameters
- **choices** (List[Choice]) - Required - The list of new choices as the user is typing.
```

--------------------------------

### bans(limit=1000, before=..., after=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of banned users.

```APIDOC
## async for ... in bans(limit=1000, before=..., after=...)

### Description
Retrieves an asynchronous iterator of the users that are banned from the guild as a `BanEntry`. Requires `ban_members` permission.

### Parameters
- **limit** (int) - Optional - The number of bans to retrieve.
- **before** (abc.Snowflake) - Optional - Retrieve bans before this object.
- **after** (abc.Snowflake) - Optional - Retrieve bans after this object.

### Yields
- **BanEntry** - The ban entry for the user.
```

--------------------------------

### copy_global_to(guild)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Copies all global commands to a specified guild for development or testing purposes.

```APIDOC
## copy_global_to(guild)

### Description
Copies all global commands to the specified guild. This method overrides pre-existing guild commands that conflict.

### Parameters
- **guild** (Snowflake) - Required - The guild to copy the commands to.

### Raises
- **CommandLimitReached** - The maximum number of commands was reached for that guild.
```

--------------------------------

### Implementing Local Error Handlers

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the error decorator to handle exceptions locally within a specific command.

```python
@bot.command()
async def info(ctx, *, member: discord.Member):
    """Tells you some info about the member."""
    msg = f"{member} joined on {member.joined_at} and has {len(member.roles)} roles."
    await ctx.send(msg)


@info.error
async def info_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("I could not find that member...")
```

--------------------------------

### Hybrid command parameter flattening

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates how FlagConverter parameters are flattened in hybrid commands.

```python
class BanFlags(commands.FlagConverter):
    member: discord.Member
    reason: str
    days: int = 1


@commands.hybrid_command()
async def ban(ctx, *, flags: BanFlags): ...
```

```python
@commands.hybrid_command()
async def ban(ctx, member: discord.Member, reason: str, days: int = 1): ...
```

--------------------------------

### View.find_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Gets an item by its ID.

```APIDOC
## find_item(id)

### Description
Gets an item with Item.id set as id, or None if not found.

### Parameters
- **id** (int) - Required - The ID of the component.
```

--------------------------------

### edit(**options)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the channel attributes. Requires the manage_channels permission.

```APIDOC
## await edit(**options)

### Description
Edits the channel. You must have `manage_channels` permission to perform this action. Returns the newly edited channel.
```

--------------------------------

### create_soundboard_sound()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a SoundboardSound for the guild. Requires Permissions.create_expressions.

```APIDOC
## create_soundboard_sound()

### Description
Creates a `SoundboardSound` for the guild. Requires `Permissions.create_expressions`.

### Parameters
- **name** (str) - Required - The name of the sound (2-32 characters).
- **sound** (bytes) - Required - The bytes-like object representing the sound data (MP3/OGG, max 5.2s).
- **volume** (float) - Optional - The volume of the sound (0-1). Defaults to 1.
- **emoji** (Optional[Union[Emoji, PartialEmoji, str]]) - Optional - The emoji of the sound.
- **reason** (Optional[str]) - Optional - The reason for creating the sound.
```

--------------------------------

### get_thread(thread_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a thread with the given ID.

```APIDOC
## get_thread(thread_id)

### Description
Returns a thread with the given ID. Note that this does not always retrieve archived threads.

### Parameters
- **thread_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Thread]** - The returned thread or `None` if not found.
```

--------------------------------

### Updating Event Signatures

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Shows the change in event parameters from single objects to before/after state pairs.

```python
def on_channel_update(channel):
    pass


def on_member_update(member):
    pass


def on_status(member):
    pass


def on_server_role_update(role):
    pass


def on_voice_state_update(member):
    pass


def on_socket_raw_send(payload, is_binary):
    pass
```

```python
def on_channel_update(before, after):
    pass


def on_member_update(before, after):
    pass


def on_server_role_update(before, after):
    pass


def on_voice_state_update(before, after):
    pass


def on_socket_raw_send(payload):
    pass
```

--------------------------------

### get_commands

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves all application commands from the tree.

```APIDOC
## get_commands(*, guild=None, type=None)

### Description
Gets all application commands from the tree.

### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to get the commands from, not including global commands. If not given or None then only global commands are returned.
- **type** (Optional[AppCommandType]) - Optional - The type of commands to get. When not given or None, then all command types are returned.

### Returns
- **List[Union[ContextMenu, Command, Group]]** - The application commands from the tree.
```

--------------------------------

### discord.app_commands.Choice

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents an application command argument choice.

```APIDOC
## class discord.app_commands.Choice(name, value)

### Description
Represents an application command argument choice.

### Parameters
- **name** (Union[str, locale_str]) - Required - The name of the choice for display purposes (up to 100 characters).
- **value** (Union[int, str, float]) - Required - The value of the choice (string up to 100 characters).
- **name_localizations** (Dict[Locale, str]) - Optional - The localised names of the choice.
```

--------------------------------

### templates

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the list of templates for the guild.

```APIDOC
## await templates()

### Description
Gets the list of templates from this guild. Requires manage_guild permission.

### Returns
- **List[Template]** - The templates for this guild.
```

--------------------------------

### get_destination()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the destination where the help command output will be sent.

```APIDOC
## get_destination()

### Description
Returns the `Messageable` where the help command will be output. By default, this returns the context’s channel.

### Returns
- **abc.Messageable** - The destination where the help command will be output.
```

--------------------------------

### Registering a pre-invoke hook with before_invoke

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates using a shared coroutine as a pre-invoke hook for both standalone commands and commands within a Cog.

```python
async def record_usage(ctx):
    print(ctx.author, "used", ctx.command, "at", ctx.message.created_at)


@bot.command()
@commands.before_invoke(record_usage)
async def who(ctx):  # Output: <User> used who at <Time>
    await ctx.send("i am a bot")


class What(commands.Cog):
    @commands.before_invoke(record_usage)
    @commands.command()
    async def when(self, ctx):  # Output: <User> used when at <Time>
        await ctx.send(f"and i have existed since {ctx.bot.user.created_at}")

    @commands.command()
    async def where(self, ctx):  # Output: <Nothing>
        await ctx.send("on Discord")

    @commands.command()
    async def why(self, ctx):  # Output: <Nothing>
        await ctx.send("because someone made me")
```

--------------------------------

### Enable Member Intents

Source: https://discordpy.readthedocs.io/en/latest/intents.html

Enables the privileged members intent by setting the members attribute to True on the Intents object.

```python
import discord

intents = discord.Intents.default()
intents.members = True

# Somewhere else:
# client = discord.Client(intents=intents)
# or
# from discord.ext import commands
# bot = commands.Bot(command_prefix='!', intents=intents)
```

--------------------------------

### discord.on_raw_app_command_permissions_update(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event triggered when application command permissions are updated.

```APIDOC
## discord.on_raw_app_command_permissions_update(payload)

### Description
Called when application command permissions are updated.

### Parameters
- **payload** (RawAppCommandPermissionsUpdateEvent) - Required - The raw event payload data.
```

--------------------------------

### Create a restricted text channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates creating a private channel by providing a dictionary of PermissionOverwrite objects to the overwrites parameter.

```python
overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True)}

channel = await guild.create_text_channel("secret", overwrites=overwrites)
```

--------------------------------

### @discord.ui.select

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a select menu to a component within a discord.ui.View. The decorated function receives the interaction and the select instance as arguments.

```APIDOC
## @discord.ui.select

### Description
A decorator that attaches a select menu to a component. The function being decorated should have three parameters: `self` (the `discord.ui.View`), the `discord.Interaction`, and the chosen select class.

### Parameters
- **cls** (discord.ui.select.Select) - Optional - The class of the select menu to use.
- **options** (List) - Optional - The options available in the select menu.
- **channel_types** (List) - Optional - The types of channels to filter by.
- **placeholder** (str) - Optional - The placeholder text shown when nothing is selected.
- **custom_id** (str) - Optional - The ID of the select menu.
- **min_values** (int) - Optional - The minimum number of items that must be chosen.
- **max_values** (int) - Optional - The maximum number of items that can be chosen.
- **disabled** (bool) - Optional - Whether the select is disabled.
- **default_values** (List) - Optional - A list of default values for the select menu.
- **row** (int) - Optional - The row the select menu should be placed in.
- **id** (int) - Optional - The ID of this select.

### Example
```python
class View(discord.ui.View):

    @discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f'You selected {select.values[0].mention}')
```
```

--------------------------------

### AutoModRule.is_exempt(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if a specific role, channel, or thread is exempt from the auto moderation rule.

```APIDOC
## is_exempt(obj)

### Description
Check if an object is exempt from the automod rule.

### Parameters
- **obj** (`abc.Snowflake`) - Required - The role, channel, or thread to check.

### Returns
- `bool` - Whether the object is exempt from the automod rule.
```

--------------------------------

### PermissionOverwrite.is_empty

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the permission overwrite is currently empty.

```APIDOC
## is_empty()

### Description
Checks if the permission overwrite is currently empty, meaning no overwrites are set to True or False.

### Returns
- **bool** - Indicates if the overwrite is empty.
```

--------------------------------

### kick(user, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Kicks a user from the guild. Requires the kick_members permission.

```APIDOC
## kick(user, *, reason=None)

### Description
Kicks a user from the guild. The user must meet the abc.Snowflake abc. You must have kick_members to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to kick from the guild.
- **reason** (Optional[str]) - Optional - The reason the user got kicked.

### Raises
- **Forbidden** - You do not have the proper permissions to kick.
- **HTTPException** - Kicking failed.
```

--------------------------------

### discord.ui.MentionableSelect

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of predefined options with the current members and roles in the guild.

```APIDOC
## class discord.ui.MentionableSelect(custom_id=..., placeholder=None, min_values=1, max_values=1, disabled=False, required=True, row=None, default_values=..., id=None)

### Description
Represents a UI select menu with a list of predefined options with the current members and roles in the guild. If sent in a private message, it only allows selecting the client or the user themselves.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu received during an interaction (max 100 chars).
- **placeholder** (Optional[str]) - Optional - Placeholder text shown if nothing is selected (max 150 chars).
- **min_values** (int) - Optional - Minimum number of items to be chosen (0-25, default 1).
- **max_values** (int) - Optional - Maximum number of items to be chosen (1-25, default 1).
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required (only for modals).
- **default_values** (Sequence[Snowflake]) - Optional - List of objects representing users/roles selected by default.
- **row** (Optional[int]) - Optional - The relative row index (0-4) for the component.
- **id** (Optional[int]) - Optional - Unique ID of the component.
```

--------------------------------

### Set channel permissions using PermissionOverwrite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Applies a pre-configured PermissionOverwrite object to a channel target.

```python
overwrite = discord.PermissionOverwrite()
overwrite.send_messages = False
overwrite.read_messages = True
await channel.set_permissions(member, overwrite=overwrite)
```

--------------------------------

### discord.on_integration_create

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is created. Requires Intents.integrations.

```APIDOC
## discord.on_integration_create(integration)

### Description
Called when an integration is created. This requires Intents.integrations to be enabled.

### Parameters
- **integration** (Integration) - The integration that was created.
```

--------------------------------

### CategoryChannel.move

Source: https://discordpy.readthedocs.io/en/latest/api.html

A rich interface to help move a channel relative to other channels.

```APIDOC
## await move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. If exact position movement is required, edit should be used instead. You must have manage_channels to do this.

### Parameters
- **beginning** (bool) - Optional - Whether to move the channel to the beginning of the channel list.
- **end** (bool) - Optional - Whether to move the channel to the end of the channel list.
- **before** (Snowflake) - Optional - Whether to move the channel before the given channel.
- **after** (Snowflake) - Optional - Whether to move the channel after the given channel.
- **offset** (int) - Optional - The number of channels to offset the move by.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync the permissions with the category.
- **reason** (str) - Optional - The reason for the move.
```

--------------------------------

### AutoModAction.fetch_rule

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the rule that triggered the specific action. Requires manage_guild permissions.

```APIDOC
## fetch_rule()

### Description
Fetch the rule whose action was taken. You must have `Permissions.manage_guild` to do this.

### Returns
- `AutoModRule` - The rule that was executed.
```

--------------------------------

### archived_threads

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator for archived threads in the channel.

```APIDOC
## archived_threads(private=False, joined=False, limit=100, before=None)

### Description
Returns an asynchronous iterator that iterates over all archived threads in this text channel.

### Parameters
- **limit** (Optional[bool]) - Optional - The number of threads to retrieve.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve threads before the given date or ID.
- **private** (bool) - Optional - Whether to retrieve private archived threads.
- **joined** (bool) - Optional - Whether to retrieve private archived threads that you have joined.

### Yields
- **Thread** - The archived threads.
```

--------------------------------

### LayoutView.find_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves an item by its internal ID.

```APIDOC
## LayoutView.find_item(id)

### Description
Gets an item with Item.id set as id, or None if not found.

### Parameters
- **id** (int) - Required - The ID of the component.

### Returns
- **Optional[Item]** - The item found, or None.
```

--------------------------------

### discord.ext.commands.when_mentioned_or

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A callable that implements when mentioned or other prefixes provided. This is intended to be passed into the Bot.command_prefix attribute.

```APIDOC
## discord.ext.commands.when_mentioned_or(*prefixes)

### Description
A callable that implements when mentioned or other prefixes provided. These are meant to be passed into the Bot.command_prefix attribute.
```

--------------------------------

### await remove_attachments(*attachments)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes specific attachments from the message.

```APIDOC
## await remove_attachments(*attachments)

### Description
Removes attachments from the message.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove from the message.

### Returns
- **Message** - The newly edited message.
```

--------------------------------

### create_integration

Source: https://discordpy.readthedocs.io/en/latest/api.html

Attaches an integration to the guild. Requires manage_guild permission.

```APIDOC
## await create_integration(type, id)

### Description
Attaches an integration to the guild. You must have `manage_guild` to do this.

### Parameters
- **type** (str) - Required - The integration type (e.g. Twitch).
- **id** (int) - Required - The integration ID.
```

--------------------------------

### send_modal

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by sending a modal.

```APIDOC
## send_modal(modal)

### Description
Responds to this interaction by sending a modal.

### Parameters
- **modal** (Modal) - Required - The modal to send.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### CategoryChannel.clone

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the category channel. Requires manage_channels permission.

```APIDOC
## await CategoryChannel.clone(name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. You must have `manage_channels` to do this.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel. If not provided, defaults to this channel name.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel. Shows up on the audit log.

### Returns
- **abc.GuildChannel** - The channel that was created.

### Raises
- **Forbidden** - You do not have the proper permissions to create this channel.
- **HTTPException** - Creating the channel failed.
```

--------------------------------

### defer(*, ephemeral=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that defers interaction-based contexts, typically used when a secondary action will be performed later.

```APIDOC
## await defer(*, ephemeral=False)

### Description
Defers the interaction based contexts. If this isn't an interaction based context then it does nothing.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral.

### Raises
- **HTTPException** - Deferring the interaction failed.
- **InteractionResponded** - This interaction has already been responded to before.
```

--------------------------------

### walk_commands()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns an iterator that recursively walks through all commands and subcommands.

```APIDOC
## walk_commands()

### Description
An iterator that recursively walks through all commands and subcommands.

### Yields
- **Command/Group** (Union) - A command or group from the internal list of commands.
```

--------------------------------

### edit(reason=None, **options)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the channel settings. Requires the 'manage_channels' permission.

```APIDOC
## edit(reason=None, **options)

### Description
Edits the channel. You must have `manage_channels` to do this.

### Parameters
- **name** (`str`) - Optional - The new channel’s name.
- **bitrate** (`int`) - Optional - The new channel’s bitrate.
- **position** (`int`) - Optional - The new channel’s position.
- **nsfw** (`bool`) - Optional - To mark the channel as NSFW or not.
- **user_limit** (`int`) - Optional - The new channel’s user limit.
- **sync_permissions** (`bool`) - Optional - Whether to sync permissions with the category. Defaults to `False`.
- **category** (`Optional[CategoryChannel]`) - Optional - The new category for this channel.
- **slowmode_delay** (`int`) - Optional - Specifies the slowmode rate limit.
- **reason** (`Optional[str]`) - Optional - The reason for editing this channel.
- **overwrites** (`Mapping`) - Optional - A mapping of target to `PermissionOverwrite`.
- **rtc_region** (`Optional[str]`) - Optional - The new region for the stage channel.
- **video_quality_mode** (`VideoQualityMode`) - Optional - The camera video quality.

### Returns
- `Optional[StageChannel]` - The newly edited stage channel, or `None` if only positional changes were made.
```

--------------------------------

### Update Enumeration Usage

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Replaces string-based comparisons with discord.py enumeration types for server regions, member status, and channel types.

```python
server.region == "us-west"
member.status == "online"
channel.type == "text"
```

```python
server.region == discord.ServerRegion.us_west
member.status = discord.Status.online
channel.type == discord.ChannelType.text
```

--------------------------------

### Member.ban

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bans the member from the guild. This is a coroutine.

```APIDOC
## await Member.ban(*, delete_message_days=..., delete_message_seconds=..., reason=None)

### Description
Bans this member from the guild. This is a coroutine equivalent to Guild.ban().

### Parameters
- **delete_message_days** (int) - Optional - Number of days of messages to delete.
- **delete_message_seconds** (int) - Optional - Number of seconds of messages to delete.
- **reason** (str) - Optional - The reason for the ban.
```

--------------------------------

### button(label=None, custom_id=None, disabled=False, style=ButtonStyle.secondary, emoji=None, id=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a button to the action row.

```APIDOC
## button(...)

### Description
A decorator that attaches a button to the action row. The function being decorated should have three parameters: `self`, `discord.Interaction`, and `discord.ui.Button`.

### Parameters
- **label** (Optional[str]) - Optional - The label of the button.
- **custom_id** (Optional[str]) - Optional - The ID of the button received during interaction.
- **style** (`ButtonStyle`) - Optional - The style of the button.
- **disabled** (`bool`) - Optional - Whether the button is disabled.
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the button.
- **id** (Optional[int]) - Optional - The ID of the component.
```

--------------------------------

### invoke(command, *args, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Calls a command with the arguments given, bypassing converters, checks, and hooks.

```APIDOC
## invoke(command, *args, **kwargs)

### Description
Calls a command with the arguments given. This is useful if you want to just call the callback that a Command holds internally. This does not handle converters, checks, cooldowns, pre-invoke, or after-invoke hooks.

### Parameters
- **command** (Command) - Required - The command that is going to be called.
- ***args** - Optional - The arguments to use.
- ****kwargs** - Optional - The keyword arguments to use.
```

--------------------------------

### await remove_reaction(emoji, member)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Remove a reaction by the member from the message.

```APIDOC
## await remove_reaction(emoji, member)

### Description
Remove a reaction by the member from the message. Requires 'manage_messages' if the reaction is not your own.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to remove.
- **member** (abc.Snowflake) - Required - The member for which to remove the reaction.
```

--------------------------------

### fetch_template

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Gets a Template from a discord.new URL or code.

```APIDOC
## await fetch_template(code)

### Description
Gets a Template from a discord.new URL or code.

### Parameters
- **code** (Union[Template, str]) - Required - The Discord Template Code or URL.

### Returns
- **Template** - The template from the URL/code.

### Raises
- **NotFound** - The template is invalid.
- **HTTPException** - Getting the template failed.
```

--------------------------------

### Restrict command access with has_any_role

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses the has_any_role check to ensure the user possesses at least one of the specified roles or IDs.

```python
@tree.command()
@app_commands.checks.has_any_role("Library Devs", "Moderators", 492212595072434186)
async def cool(interaction: discord.Interaction):
    await interaction.response.send_message("You are cool indeed")
```

--------------------------------

### Apply Global Checks to All Commands

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the Bot.check decorator to register a check that runs for every command.

```python
@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None
```

--------------------------------

### ban(user, *, reason=None, delete_message_days=..., delete_message_seconds=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bans a user from the guild. Requires the ban_members permission.

```APIDOC
## ban(user, *, reason=None, delete_message_days=..., delete_message_seconds=...)

### Description
Bans a user from the guild. The user must meet the abc.Snowflake abc. You must have ban_members to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to ban from the guild.
- **delete_message_days** (int) - Optional - The number of days worth of messages to delete from the user in the guild. Deprecated since version 2.1.
- **delete_message_seconds** (int) - Optional - The number of seconds worth of messages to delete from the user in the guild. New in version 2.1.
- **reason** (Optional[str]) - Optional - The reason the user got banned.

### Raises
- **NotFound** - The requested user was not found.
- **Forbidden** - You do not have the proper permissions to ban.
- **HTTPException** - Banning failed.
- **TypeError** - You specified both delete_message_days and delete_message_seconds.
```

--------------------------------

### Restrict Commands via add_cog

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Apply guild restrictions when adding a cog to the bot instance.

```python
class MyCog(commands.Cog):
    @app_commands.command()
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message("Pong!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(...), guild=discord.Object(123456789012345678))
```

--------------------------------

### @discord.ext.commands.command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator that transforms a function into a Command. By default, the help attribute is automatically derived from the function's docstring.

```APIDOC
## @discord.ext.commands.command(name=..., cls=..., **attrs)

### Description
A decorator that transforms a function into a `Command` or `Group` (if called with `group()`). It automatically extracts help text from the function's docstring.

### Parameters
- **name** (str) - Optional - The name to create the command with. Defaults to the function name.
- **cls** (type) - Optional - The class to construct with. Defaults to `Command`.
- **attrs** (dict) - Optional - Keyword arguments to pass into the construction of the class.
```

--------------------------------

### fetch_widget

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Gets a Widget from a guild ID.

```APIDOC
## await fetch_widget(guild_id)

### Description
Gets a Widget from a guild ID. The guild must have the widget enabled.

### Parameters
- **guild_id** (int) - Required - The ID of the guild.

### Returns
- **Widget** - The guild’s widget.

### Raises
- **Forbidden** - The widget for this guild is disabled.
- **HTTPException** - Retrieving the widget failed.
```

--------------------------------

### edit(content=..., embed=..., embeds=..., attachments=..., delete_after=None, allowed_mentions=..., view=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the message content, embeds, attachments, or view.

```APIDOC
## await edit(content=..., embed=..., embeds=..., attachments=..., delete_after=None, allowed_mentions=..., view=...)

### Description
Edits the message. Returns the newly edited message.

### Parameters
- **content** (str) - Optional - New content.
- **embed** (Embed) - Optional - New single embed.
- **embeds** (List[Embed]) - Optional - New list of embeds (max 10).
- **attachments** (List[Union[Attachment, File]]) - Optional - List of attachments.
- **delete_after** (float) - Optional - Seconds to wait before deleting the edited message.
- **allowed_mentions** (AllowedMentions) - Optional - Mentions processing configuration.
- **view** (Union[View, LayoutView]) - Optional - Updated view.

### Returns
- **Message** - The newly edited message.

### Raises
- **HTTPException** - Editing failed.
- **Forbidden** - Insufficient permissions or editing another user's message.
- **NotFound** - Message does not exist.
- **TypeError** - Both `embed` and `embeds` specified.
```

--------------------------------

### Avoid blocking the event loop with sleep

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use asyncio.sleep instead of time.sleep to prevent blocking the event loop.

```python
# bad
time.sleep(10)

# good
await asyncio.sleep(10)
```

--------------------------------

### StageChannel.pins

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of the pinned messages in the channel. Requires view_channel and read_message_history permissions.

```APIDOC
## pins(limit=50, before=None, oldest_first=False)

### Description
Retrieves an asynchronous iterator of the pinned messages in the channel.

### Parameters
- **limit** (Optional[int]) - Optional - The number of pinned messages to retrieve. Defaults to 50.
- **before** (Optional[Union[datetime.datetime, abc.Snowflake]]) - Optional - Retrieve pinned messages before this time or snowflake.
- **oldest_first** (bool) - Optional - If set to True, return messages in oldest pin to newest pin order. Defaults to False.

### Returns
- **AsyncIterator[Message]** - An asynchronous iterator of pinned messages.
```

--------------------------------

### discord.on_webhooks_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever a webhook is created, modified, or removed from a guild channel. Requires Intents.webhooks.

```APIDOC
## discord.on_webhooks_update(channel)

### Description
Called whenever a webhook is created, modified, or removed from a guild channel. This requires Intents.webhooks to be enabled.

### Parameters
- **channel** (abc.GuildChannel) - The channel that had its webhooks updated.
```

--------------------------------

### @error(coro)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that registers a coroutine as a local error handler for a command.

```APIDOC
## @error(coro)

### Description
Registers a local error handler that is invoked when an exception occurs during command execution. The handler must accept two parameters: the interaction and the error (derived from AppCommandError).

### Parameters
- **coro** (coroutine) - Required - The coroutine to register as the local error handler.
```

--------------------------------

### Implement Custom Prefix Callable

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates how to invoke the callable returned by when_mentioned_or within a custom prefix function.

```python
async def get_prefix(bot, message):
    extras = await prefixes_for(message.guild)  # returns a list
    return commands.when_mentioned_or(*extras)(bot, message)
```

--------------------------------

### SKU.subscriptions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of subscriptions associated with the SKU.

```APIDOC
## async for subscription in SKU.subscriptions(limit=50, before=None, after=None, user=None)

### Description
Retrieves an asynchronous iterator of the Subscription that SKU has.

### Parameters
- **limit** (Optional[int]) - Optional - The number of subscriptions to retrieve. Defaults to 100.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve subscriptions before this date or entitlement.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve subscriptions after this date or entitlement.
- **user** (Snowflake) - Optional - The user to filter by.

### Yields
- **Subscription** - The subscription with the SKU.

### Raises
- **HTTPException** - Fetching the subscriptions failed.
- **TypeError** - Both after and before were provided.
```

--------------------------------

### fetch_entitlement

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves an entitlement by its ID.

```APIDOC
## await fetch_entitlement(entitlement_id)

### Description
Retrieves an `Entitlement` with the specified ID.

### Parameters
- **entitlement_id** (int) - Required - The entitlement’s ID to fetch.

### Raises
- **NotFound** - Entitlement does not exist.
- **MissingApplicationID** - Application ID not found.
- **HTTPException** - Fetching failed.

### Returns
- **Entitlement** - The requested entitlement.
```

--------------------------------

### Use Tuple for variadic arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

The tuple annotation enables greedy-like semantics for flag parsing.

```python
from discord.ext import commands
from typing import Tuple
import discord


class BanFlags(commands.FlagConverter):
    members: Tuple[discord.Member, ...]
    reason: str
    days: int = 1
```

```python
# point: 10 11 point: 12 13
class Coordinates(commands.FlagConverter):
    point: Tuple[int, int]
```

--------------------------------

### discord.on_integration_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is updated. Requires Intents.integrations.

```APIDOC
## discord.on_integration_update(integration)

### Description
Called when an integration is updated. This requires Intents.integrations to be enabled.

### Parameters
- **integration** (Integration) - The integration that was updated.
```

--------------------------------

### run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A blocking call that abstracts away the event loop initialization. This must be the last function called in your script.

```APIDOC
## run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

### Description
A blocking call that abstracts away the event loop initialisation. This function also sets up the logging library.

### Parameters
- **token** (str) - Required - The authentication token.
- **reconnect** (bool) - Optional - If we should attempt reconnecting.
- **log_handler** (Optional[logging.Handler]) - Optional - The log handler to use.
- **log_formatter** (logging.Formatter) - Optional - The formatter to use with the given log handler.
- **log_level** (int) - Optional - The default log level for the library's logger.
- **root_logger** (bool) - Optional - Whether to set up the root logger.
```

--------------------------------

### Handle wait_for timeout

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Catch asyncio.TimeoutError when the wait_for operation exceeds the specified timeout duration.

```python
def pred(m):
    return m.author == message.author and m.channel == message.channel


try:
    msg = await client.wait_for("message", check=pred, timeout=60.0)
except asyncio.TimeoutError:
    await channel.send("You took too long...")
else:
    await channel.send("You said {0.content}, {0.author}.".format(msg))
```

--------------------------------

### @autocomplete(name)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that registers a coroutine as an autocomplete prompt for a specific command parameter.

```APIDOC
## @autocomplete(name)

### Description
Registers a coroutine to provide autocomplete suggestions for a command parameter. The callback must accept an Interaction and the current string value, returning a list of Choice objects.

### Parameters
- **name** (str) - Required - The parameter name to register as autocomplete.
```

--------------------------------

### edit(name=..., permissions=..., colour=..., secondary_colour=..., tertiary_colour=..., hoist=..., display_icon=..., mentionable=..., position=..., reason=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the role attributes. Returns the newly edited Role object.

```APIDOC
## edit(name, permissions, colour, secondary_colour, tertiary_colour, hoist, display_icon, mentionable, position, reason)

### Description
Edits the role with the provided parameters. Requires appropriate permissions.

### Parameters
- **name** (str) - Optional - The new role name.
- **permissions** (Permissions) - Optional - The new permissions.
- **colour** (Union[Colour, int]) - Optional - The new colour.
- **secondary_colour** (Optional[Union[Colour, int]]) - Optional - The new secondary colour.
- **tertiary_colour** (Optional[Union[Colour, int]]) - Optional - The new tertiary colour.
- **hoist** (bool) - Optional - Whether the role is shown separately.
- **display_icon** (Optional[Union[bytes, str]]) - Optional - The icon for the role.
- **mentionable** (bool) - Optional - Whether the role is mentionable.
- **position** (int) - Optional - The new position.
- **reason** (Optional[str]) - Optional - Reason for the audit log.

### Returns
- **Role** - The newly edited role.
```

--------------------------------

### is_owner(user)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Checks if a User or Member is the owner of the bot.

```APIDOC
## is_owner(user)

### Description
Checks if a User or Member is the owner of this bot. If an owner_id is not set, it is fetched automatically through the use of application_info().

### Parameters
- **user** (abc.User) - Required - The user to check for.

### Returns
- **bool** - Whether the user is the owner.
```

--------------------------------

### edit_role_positions(positions, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bulk edits the positions of multiple roles in the guild.

```APIDOC
## edit_role_positions(positions, *, reason=None)

### Description
Bulk edits a list of `Role` in the guild. Requires `manage_roles` permission.

### Parameters
- **positions** (`dict`) - Required - A dict of `Role` to `int` to change the positions.
- **reason** (`str`) - Optional - The reason for editing the role positions.

### Returns
- `List[Role]` - A list of all the roles in the guild.
```

--------------------------------

### Implementing Cog-specific hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Define cog_before_invoke and cog_after_invoke methods within a Cog class to handle hooks for all commands inside that Cog.

```python
class MyCog(commands.Cog):
    async def cog_before_invoke(self, ctx):
        ctx.secret_cog_data = "foo"

    async def cog_after_invoke(self, ctx):
        print("{0.command} is done...".format(ctx))

    @commands.command()
    async def foo(self, ctx):
        await ctx.send(ctx.secret_cog_data)
```

--------------------------------

### discord.on_guild_update(before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a guild's information is updated.

```APIDOC
## discord.on_guild_update(before, after)

### Description
Called when a `Guild` updates (e.g., name change, AFK channel change). Requires `Intents.guilds` to be enabled.

### Parameters
- **before** (Guild) - Required - The guild prior to being updated.
- **after** (Guild) - Required - The guild after being updated.
```

--------------------------------

### discord.on_guild_role_update(before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Triggered when a role is updated in a guild.

```APIDOC
## discord.on_guild_role_update(before, after)

### Description
Called when a Role is changed guild-wide.

### Parameters
- **before** (Role) - The updated role’s old info.
- **after** (Role) - The updated role’s updated info.
```

--------------------------------

### @discord.app_commands.user_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates a command should be installed for users.

```APIDOC
## @discord.app_commands.user_install()

### Description
Indicates that this command should be installed for users. Verified server-side; ignored in subcommands.
```

--------------------------------

### Receive a Member object as a command argument

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates using discord.Member as a type hint to automatically convert a string argument into a Member object.

```python
@bot.command()
async def joined(ctx, *, member: discord.Member):
    await ctx.send(f"{member} joined on {member.joined_at}")
```

--------------------------------

### find_item(id)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Gets an item with Item.id set as id, or None if not found.

```APIDOC
## find_item(id)

### Parameters
- **id** (int) - Required - The ID of the component.

### Returns
- **Optional[Item]** - The item found, or None.
```

--------------------------------

### Migrating AsyncIterator.chunk()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replaces the chunk method with discord.utils.as_chunks().

```python
# before
async for leader, *users in reaction.users().chunk(3):
    ...

# after
async for leader, *users in discord.utils.as_chunks(reaction.users(), 3):
    ...
```

--------------------------------

### fetch_guild

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a guild by its ID.

```APIDOC
## await fetch_guild(guild_id, with_counts=True)

### Description
Retrieves a `Guild` from an ID.

### Parameters
- **guild_id** (int) - Required - The guild’s ID.
- **with_counts** (bool) - Optional - Whether to include count information. Defaults to True.

### Raises
- **NotFound** - Guild doesn’t exist or access denied.
- **HTTPException** - Getting the guild failed.

### Returns
- **Guild** - The guild from the ID.
```

--------------------------------

### move(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A rich interface to help move a channel relative to other channels.

```APIDOC
## move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. If exact position movement is required, `edit` should be used instead. You must have `manage_channels` to do this.

### Parameters
- **beginning** (bool) - Optional - Whether to move the channel to the beginning of the channel list.
- **end** (bool) - Optional - Whether to move the channel to the end of the channel list.
- **before** (Snowflake) - Optional - Whether to move the channel before the given channel.
- **after** (Snowflake) - Optional - Whether to move the channel after the given channel.
- **offset** (int) - Optional - The number of channels to offset the move by.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync the permissions with the category.
- **reason** (str) - Optional - The reason for the move.

### Raises
- **ValueError** - An invalid position was given.
- **TypeError** - A bad mix of arguments were passed.
- **Forbidden** - You do not have permissions to move the channel.
- **HTTPException** - Moving the channel failed.
```

--------------------------------

### Using Client.async_event Utility

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Simplifies coroutine event registration by using the provided utility decorator.

```python
@client.async_event
def on_message(message):
    pass
```

--------------------------------

### Cog.get_app_commands()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a list of app commands and groups defined within the cog.

```APIDOC
## Cog.get_app_commands()

### Description
Returns the app commands that are defined inside this cog.

### Returns
- **List[Union[discord.app_commands.Command, discord.app_commands.Group]]** - A list of app commands and groups defined in this cog.
```

--------------------------------

### history

Source: https://discordpy.readthedocs.io/en/latest/api.html

Iterates over message history.

```APIDOC
## history(limit=100, before=None, after=None, around=None, oldest_first=None)

### Description
Returns an asynchronous iterator for the destination's message history. Requires read_message_history permission.

### Parameters
- **limit** (int) - Optional - Max messages to retrieve.
- **before** (Optional) - Optional - Retrieve messages before this ID/object.
- **after** (Optional) - Optional - Retrieve messages after this ID/object.
- **around** (Optional) - Optional - Retrieve messages around this ID/object.
- **oldest_first** (Optional[bool]) - Optional - Whether to return oldest messages first.
```

--------------------------------

### discord.on_guild_role_create(role)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Triggered when a new role is created in a guild.

```APIDOC
## discord.on_guild_role_create(role)

### Description
Called when a Guild creates a new Role.

### Parameters
- **role** (Role) - The role that was created.
```

--------------------------------

### Migrating voice connection and playback

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Voice operations now use VoiceChannel.connect and AudioSource objects instead of player instances.

```python
vc = await client.join_voice_channel(channel)
player = vc.create_ffmpeg_player("testing.mp3", after=lambda: print("done"))
player.start()

player.is_playing()
player.pause()
player.resume()
player.stop()
# ...
```

```python
vc = await channel.connect()
vc.play(discord.FFmpegPCMAudio("testing.mp3"), after=lambda e: print("done", e))
vc.is_playing()
vc.pause()
vc.resume()
vc.stop()
```

--------------------------------

### Migrating filtered channel history

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates filtering logic to use standard Python list comprehension syntax with asynchronous iterators.

```python
def predicate(message):
    return not message.author.bot


# before
user_messages = []
async for message in channel.history().filter(lambda m: not m.author.bot):
    user_messages.append(message)

# after
user_messages = [message async for message in channel.history() if not m.author.bot]
```

--------------------------------

### SyncWebhookMessage.add_files

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds new files to the end of the message attachments.

```APIDOC
## add_files(*files)

### Description
Adds new files to the end of the message attachments.

### Parameters
- **files** (File) - Required - New files to add to the message.

### Returns
- **SyncWebhookMessage** - The newly edited message.

### Raises
- **HTTPException** - Editing the message failed.
- **Forbidden** - Tried to edit a message that isn’t yours.
```

--------------------------------

### add_check(func)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds a check function to the command to determine if it can be executed.

```APIDOC
## add_check(func)

### Description
Adds a check to the command. This is the non-decorator interface for adding validation logic to command execution.

### Parameters
- **func** (function) - Required - The function that will be used as a check.
```

--------------------------------

### launch_activity

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by launching the activity associated with the app.

```APIDOC
## launch_activity()

### Description
Responds to this interaction by launching the activity associated with the app. Only available for apps with activities enabled.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### Restrict command arguments with typing.Literal

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use Literal to restrict command arguments to specific values. If the input does not match, a BadLiteralArgument error is raised.

```python
from typing import Literal


@bot.command()
async def shop(ctx, buy_sell: Literal["buy", "sell"], amount: Literal[1, 2], *, item: str):
    await ctx.send(f"{buy_sell.capitalize()}ing {amount} {item}(s)!")
```

--------------------------------

### @discord.app_commands.allowed_installs

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that specifies whether a command should be installed in guilds or for users.

```APIDOC
## @discord.app_commands.allowed_installs(guilds=..., users=...)

### Description
Indicates the installation context for the command. Valid contexts are guilds and users.

### Parameters
- **guilds** (bool) - Optional - Whether the command is installable in guilds.
- **users** (bool) - Optional - Whether the command is installable for users.
```

--------------------------------

### Implement a custom check for check_any

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Defines a predicate function intended to be used with the check_any decorator to evaluate multiple conditions.

```python
def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)
```

--------------------------------

### Member.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the member's data, such as nickname, roles, voice state, or timeout status. Requires specific permissions depending on the parameters provided.

```APIDOC
## Member.edit(nick=..., mute=..., deafen=..., suppress=..., roles=..., voice_channel=..., timed_out_until=..., bypass_verification=..., avatar=..., banner=..., bio=..., reason=None)

### Description
Edits the member's data. Note that uploading an avatar or banner requires a bytes-like object.

### Parameters
- **nick** (Optional[str]) - Optional - The member's new nickname.
- **mute** (bool) - Optional - Indicates if the member should be guild muted or un-muted.
- **deafen** (bool) - Optional - Indicates if the member should be guild deafened or un-deafened.
- **suppress** (bool) - Optional - Indicates if the member should be suppressed in stage channels.
- **roles** (List[Role]) - Optional - The member's new list of roles.
- **voice_channel** (Optional[Union[VoiceChannel, StageChannel]]) - Optional - The voice channel to move the member to.
- **timed_out_until** (Optional[datetime.datetime]) - Optional - The date the member's timeout should expire.
- **bypass_verification** (bool) - Optional - Indicates if the member should be allowed to bypass guild verification.
- **avatar** (Optional[bytes]) - Optional - Bytes-like object representing the image to upload.
- **banner** (Optional[bytes]) - Optional - Bytes-like object representing the image to upload.
- **bio** (Optional[str]) - Optional - The new bio for the member.
- **reason** (Optional[str]) - Optional - The reason for editing this member for the audit log.

### Returns
- **Optional[Member]** - The newly updated member, if applicable.
```

--------------------------------

### Remove a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Remove a registered cog from the bot by its name.

```python
await bot.remove_cog("Greetings")
```

--------------------------------

### discord.ext.commands.when_mentioned

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A callable that implements a command prefix equivalent to being mentioned. This is intended to be passed into the Bot.command_prefix attribute.

```APIDOC
## discord.ext.commands.when_mentioned(bot, msg, /)

### Description
A callable that implements a command prefix equivalent to being mentioned. These are meant to be passed into the Bot.command_prefix attribute.
```

--------------------------------

### AutoModRule.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits an existing auto moderation rule. Requires manage_guild permissions.

```APIDOC
## edit(name=..., event_type=..., actions=..., trigger=..., enabled=..., exempt_roles=..., exempt_channels=..., reason=...)

### Description
Edits this auto moderation rule. You must have `Permissions.manage_guild` to edit rules.

### Parameters
- **name** (`str`) - Optional - The new name to change to.
- **event_type** (`AutoModRuleEventType`) - Optional - The new event type to change to.
- **actions** (List[`AutoModRuleAction`]) - Optional - The new rule actions to update.
- **trigger** (`AutoModTrigger`) - Optional - The new trigger to update.
- **enabled** (`bool`) - Optional - Whether the rule should be enabled or not.
- **exempt_roles** (Sequence[`abc.Snowflake`]) - Optional - The new roles to exempt from the rule.
- **exempt_channels** (Sequence[`abc.Snowflake`]) - Optional - The new channels to exempt from the rule.
- **reason** (`str`) - Optional - The reason for updating this rule.

### Returns
- `AutoModRule` - The updated auto moderation rule.
```

--------------------------------

### Create and use a Webhook from a URL

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates initializing a Webhook object using a URL and an aiohttp session to send a message.

```python
from discord import Webhook
import aiohttp


async def foo():
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url("url-here", session=session)
        await webhook.send("Hello World", username="Foo")
```

--------------------------------

### find_item(id)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Gets an item with a specific ID.

```APIDOC
## find_item(id)

### Description
Gets an item with `Item.id` set as `id`, or `None` if not found.

### Parameters
- **id** (`int`) - Required - The ID of the component.

### Returns
- **Optional[Item]** - The item found, or `None`.
```

--------------------------------

### ForumChannel.move

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves the channel relative to other channels. This is a coroutine.

```APIDOC
## move(beginning=False, end=False, before=None, after=None, offset=0, category=None, sync_permissions=False, reason=None)

### Description
A rich interface to help move a channel relative to other channels. Requires manage_channels permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning of the list.
- **end** (bool) - Optional - Move to the end of the list.
- **before** (Snowflake) - Optional - Move before the given channel.
- **after** (Snowflake) - Optional - Move after the given channel.
- **offset** (int) - Optional - Number of channels to offset the move.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the category.
- **reason** (str) - Optional - The reason for the move.
```

--------------------------------

### @discord.app_commands.describe

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Describes command parameters for the Discord UI using keyword arguments.

```APIDOC
## @discord.app_commands.describe

### Description
Describes the given parameters by their name using the key of the keyword argument as the name.

### Parameters
- **parameters** (Union[str, locale_str]) - Required - The description of the parameters.
```

--------------------------------

### GuildSticker.edit()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a guild sticker's properties such as name, description, or emoji.

```APIDOC
## await GuildSticker.edit(name=..., description=..., emoji=..., reason=None)

### Description
Edits a GuildSticker for the guild.

### Parameters
- **name** (str) - Optional - The sticker’s new name. Must be at least 2 characters.
- **description** (Optional[str]) - Optional - The sticker’s new description.
- **emoji** (str) - Optional - The name of a unicode emoji that represents the sticker’s expression.
- **reason** (str) - Optional - The reason for editing this sticker. Shows up on the audit log.

### Returns
- **GuildSticker** - The newly modified sticker.

### Raises
- **Forbidden** - You are not allowed to edit stickers.
- **HTTPException** - An error occurred editing the sticker.
```

--------------------------------

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a User. This method is provided for compatibility with other channel types.

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for a User. Since partial messageables cannot reasonably have the concept of permissions, this will always return Permissions.none().

### Parameters
- **obj** (User) - Required - The user to check permissions for.
```

--------------------------------

### Create command groups

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the group decorator to define commands that act as subcommands.

```python
@bot.group()
async def git(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Invalid git command passed...")


@git.command()
async def push(ctx, remote: str, branch: str):
    await ctx.send(f"Pushing to {remote} {branch}")
```

--------------------------------

### StandardSticker.pack()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the sticker pack that a standard sticker belongs to.

```APIDOC
## await StandardSticker.pack()

### Description
Retrieves the sticker pack that this sticker belongs to.

### Returns
- **StickerPack** - The retrieved sticker pack.

### Raises
- **NotFound** - The corresponding sticker pack was not found.
- **HTTPException** - Retrieving the sticker pack failed.
```

--------------------------------

### forward(destination, fail_if_not_exists=True)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Forwards the interaction message to a specified channel.

```APIDOC
## forward(destination, fail_if_not_exists=True)

### Description
Forwards this message to a channel. This is a coroutine.

### Parameters
- **destination** (Messageable) - Required - The channel to forward this message to.
- **fail_if_not_exists** (bool) - Optional - Whether replying using the message reference should raise HTTPException if the message no longer exists.

### Returns
- **Message** - The message sent to the channel.

### Raises
- **HTTPException** - Forwarding the message failed.
```

--------------------------------

### fetch_command(command_id, guild=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches a specific application command from the application, either globally or from a specific guild.

```APIDOC
## fetch_command(command_id, guild=None)

### Description
Fetches an application command from the application. If a guild is provided, it fetches the command from that guild; otherwise, it fetches the global command.

### Parameters
- **command_id** (int) - Required - The ID of the command to fetch.
- **guild** (Optional[Snowflake]) - Optional - The guild to fetch the command from.

### Returns
- **AppCommand** - The application command object.

### Raises
- **HTTPException** - Fetching the command failed.
- **MissingApplicationID** - The application ID could not be found.
- **NotFound** - The application command was not found.
```

--------------------------------

### discord.ext.commands.on_command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

An event called when a command is found and is about to be invoked.

```APIDOC
## discord.ext.commands.on_command(ctx)

### Description
An event that is called when a command is found and is about to be invoked. This event is called regardless of whether the command itself succeeds via error or completes.

### Parameters
- **ctx** (Context) - The invocation context.
```

--------------------------------

### await fetch(prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the current webhook. This is useful for retrieving a full webhook object from a partial one.

```APIDOC
## await fetch(prefer_auth=True)

### Description
Fetches the current webhook. This could be used to get a full webhook from a partial webhook.

### Parameters
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.

### Response
- **Webhook** (Object) - The fetched webhook.
```

--------------------------------

### Iterate over poll voters

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use the voters() asynchronous iterator to retrieve users who voted for a specific poll answer.

```python
async for voter in poll_answer.voters():
    print(f"{voter} has voted for {poll_answer}!")
```

```python
voters = [voter async for voter in poll_answer.voters()]
# voters is now a list of User
```

--------------------------------

### Translator.translate()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Translates a given string to a specified locale.

```APIDOC
## await Translator.translate(string, locale, context)

### Description
Translates the given string to the specified locale. If the string cannot be translated, None should be returned.

### Method
Coroutine

### Parameters
- **string** (locale_str) - Required - The string being translated.
- **locale** (Locale) - Required - The locale being requested for translation.
- **context** (TranslationContext) - Required - The translation context where the string originated from.
```

--------------------------------

### DMChannel.typing()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager to send a typing indicator to the channel.

```APIDOC
## typing()

### Description
Returns an asynchronous context manager that sends a typing indicator. If used as a context manager, it lasts for the duration of the block; if awaited, it lasts for 10 seconds.
```

--------------------------------

### discord.utils.setup_logging

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets up logging for the library, similar to logging.basicConfig but with custom defaults and color support.

```APIDOC
## discord.utils.setup_logging

### Description
A helper function to setup logging. This is superficially similar to logging.basicConfig() but uses different defaults and a colour formatter if the stream can display colour.

### Parameters
- **handler** (logging.Handler) - Optional - The log handler to use for the library’s logger. Defaults to logging.StreamHandler.
- **formatter** (logging.Formatter) - Optional - The formatter to use with the given log handler.
- **level** (int) - Optional - The default log level for the library’s logger. Defaults to logging.INFO.
- **root** (bool) - Optional - Whether to set up the root logger rather than the library logger. Defaults to True.
```

--------------------------------

### Migrate Synchronous Webhooks

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates the webhook initialization to use SyncWebhook instead of RequestsWebhookAdapter.

```python
# before
webhook = discord.Webhook.partial(123456, "token-here", adapter=discord.RequestsWebhookAdapter())
webhook.send("Hello World", username="Foo")

# after
webhook = discord.SyncWebhook.partial(123456, "token-here")
webhook.send("Hello World", username="Foo")
```

--------------------------------

### discord.on_guild_channel_update(before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event triggered when a guild channel is updated.

```APIDOC
## discord.on_guild_channel_update(before, after)

### Description
Called whenever a guild channel is updated (e.g., name, topic, permissions). Requires `Intents.guilds`.

### Parameters
- **before** (abc.GuildChannel) - Required - The updated guild channel’s old info.
- **after** (abc.GuildChannel) - Required - The updated guild channel’s new info.
```

--------------------------------

### discord.ext.commands.on_command_error

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

An event handler called when an error is raised inside a command.

```APIDOC
## discord.ext.commands.on_command_error(ctx, error)

### Description
An error handler that is called when an error is raised inside a command either through user input error, check failure, or an error in your own code.

### Parameters
- **ctx** (Context) - The invocation context.
- **error** (CommandError) - The error that was raised.
```

--------------------------------

### delete(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the role from the guild.

```APIDOC
## delete(reason)

### Description
Deletes the role. Requires manage_roles permission.

### Parameters
- **reason** (Optional[str]) - Optional - Reason for the audit log.
```

--------------------------------

### Registering per-command hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Apply before_invoke and after_invoke decorators directly to specific command functions.

```python
@bot.command()
async def foo(ctx):
    await ctx.send("foo")


@foo.before_invoke
async def before_foo_command(ctx):
    # do something before the foo command is called
    pass


@foo.after_invoke
async def after_foo_command(ctx):
    # do something after the foo command is called
    pass
```

--------------------------------

### Changing Bot Presence

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Update the bot's status and activity using the change_presence coroutine.

```python
game = discord.Game("with the API")
await client.change_presence(status=discord.Status.idle, activity=game)
```

--------------------------------

### Flattening channel history to a list

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Convert an AsyncIterator into a list of messages using the flatten method.

```python
messages = await channel.history().flatten()
for message in messages:
    print(message)
```

--------------------------------

### discord.app_commands.Group

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A class used to group application commands together.

```APIDOC
## class discord.app_commands.Group(name=..., description=..., parent=None, guild_ids=None, guild_only=..., allowed_contexts=..., allowed_installs=..., nsfw=..., auto_locale_strings=True, default_permissions=..., extras=...)

### Description
A class that represents a group of application commands. It allows for hierarchical organization of commands.
```

--------------------------------

### Cog.get_commands()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a list of commands defined within the cog, excluding app commands.

```APIDOC
## Cog.get_commands()

### Description
Returns the commands that are defined inside this cog. This does not include discord.app_commands.Command or discord.app_commands.Group instances.

### Returns
- **List[Command]** - A list of commands defined in this cog.
```

--------------------------------

### Migrating AsyncIterator.get()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replaces the instance method with discord.utils.get().

```python
# before
msg = await channel.history().get(author__name="Dave")

# after
msg = await discord.utils.get(channel.history(), author__name="Dave")
```

--------------------------------

### reaction.users()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of users who have reacted to a specific reaction.

```APIDOC
## reaction.users(limit=None, after=None, type=None)

### Description
Returns an asynchronous iterator of users or members who have reacted to this message with the specified reaction.

### Parameters
- **limit** (Optional[int]) - Optional - The maximum number of results to return.
- **after** (Optional[abc.Snowflake]) - Optional - For pagination, reactions are sorted by member.
- **type** (Optional[ReactionType]) - Optional - The type of reaction to return users from.

### Yields
- **Union[User, Member]** - The member or user that has reacted to this message.

### Raises
- **HTTPException** - Getting the users for the reaction failed.
```

--------------------------------

### Reaction.clear

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears this reaction from the message. Requires manage_messages permission.

```APIDOC
## await Reaction.clear()

### Description
Clears this reaction from the message.

### Raises
- **HTTPException** - Clearing the reaction failed.
- **Forbidden** - You do not have the proper permissions to clear the reaction.
- **NotFound** - The emoji you specified was not found.
- **TypeError** - The emoji parameter is invalid.
```

--------------------------------

### await change_voice_state(channel, self_mute, self_deaf)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Changes the client's voice state in the guild.

```APIDOC
## await change_voice_state(channel, self_mute, self_deaf)

### Description
Changes the client's voice state in the guild.

### Parameters
- **channel** (Optional[abc.Snowflake]) - Channel the client wants to join. Use None to disconnect.
- **self_mute** (bool) - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Indicates if the client should be self-deafened.
```

--------------------------------

### pin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Pins the interaction message in the channel.

```APIDOC
## pin(reason=None)

### Description
Pins the message. Requires 'pin_messages' permission in non-private channel contexts. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message, which appears in the audit log.

### Raises
- **Forbidden** - Insufficient permissions.
- **NotFound** - Message or channel not found.
- **HTTPException** - Pinning failed.
```

--------------------------------

### delete_messages(messages, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a list of messages using bulk delete if applicable. Requires manage_messages permission.

```APIDOC
## await delete_messages(messages, reason=None)

### Description
Deletes a list of messages. This is similar to Message.delete() except it bulk deletes multiple messages. You cannot bulk delete more than 100 messages or messages that are older than 14 days old. You must have `manage_messages` to do this.

### Parameters
- **messages** (Iterable[abc.Snowflake]) - Required - An iterable of messages denoting which ones to bulk delete.
- **reason** (Optional[str]) - Optional - The reason for deleting the messages. Shows up on the audit log.

### Raises
- **ClientException** - The number of messages to delete was more than 100.
- **Forbidden** - You do not have proper permissions to delete the messages.
- **NotFound** - If single delete, then the message was already deleted.
- **HTTPException** - Deleting the messages failed.
```

--------------------------------

### remove_item(item)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes an item from the action row.

```APIDOC
## remove_item(item)

### Description
Removes an item from the action row. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (`Item`) - Required - The item to remove from the action row.
```

--------------------------------

### send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination. This method supports various parameters including content, embeds, files, and UI views.

```APIDOC
## send(content=None, tts=False, embed=None, embeds=None, file=None, files=None, nonce=None, delete_after=None, allowed_mentions=None, reference=None, mention_author=None, view=None, stickers=None, suppress_embeds=False, silent=False, poll=None)

### Description
Sends a message to the channel or user. Returns the sent Message object.

### Parameters
- **content** (str) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload (max 10).
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload (max 10).
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions processed in this message.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the message to reply to.
- **mention_author** (bool) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of stickers to upload (max 3).
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Optional - The poll to send with this message.

### Response
- **Message** - The message that was sent.
```

--------------------------------

### Member.is_on_mobile()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A helper function that determines if a member is active on a mobile device.

```APIDOC
## Member.is_on_mobile()

### Description
A helper function that determines if a member is active on a mobile device.

### Returns
- **bool** - True if the member is active on mobile, False otherwise.
```

--------------------------------

### Member.unban

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unbans the member from the guild. This is a coroutine.

```APIDOC
## await Member.unban(*, reason=None)

### Description
Unbans this member from the guild. This is a coroutine equivalent to Guild.unban().

### Parameters
- **reason** (str) - Optional - The reason for the unban.
```

--------------------------------

### Invite.set_scheduled_event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the scheduled event for the invite.

```APIDOC
## Invite.set_scheduled_event(scheduled_event)

### Description
Sets the scheduled event for this invite.

### Parameters
- **scheduled_event** (Snowflake) - Required - The ID of the scheduled event.

### Returns
- **Invite** - The invite with the new scheduled event.
```

--------------------------------

### Accessing custom context in commands

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Shows how to access properties defined in a custom context subclass.

```python
@bot.command()
async def secret(ctx):
    await ctx.send(ctx.secret)
```

--------------------------------

### MemberCacheFlags.from_intents(intents)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance based on the provided Intents.

```APIDOC
## MemberCacheFlags.from_intents(intents)

### Description
A factory method that creates a MemberCacheFlags instance based on the currently selected Intents.

### Parameters
- **intents** (Intents) - Required - The intents to select from.

### Returns
- **MemberCacheFlags** - The resulting member cache flags.
```

--------------------------------

### invites

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all active instant invites for the guild.

```APIDOC
## await invites()

### Description
Returns a list of all active instant invites from the guild. Requires manage_guild permission.

### Returns
- **List[Invite]** - The list of invites that are currently active.
```

--------------------------------

### add_item(item)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the view. This function returns the class instance to allow for fluent-style chaining.

```APIDOC
## add_item(item)

### Parameters
- **item** (Item) - Required - The item to add to the view.

### Raises
- **TypeError** - An Item was not passed.
- **ValueError** - Maximum number of children has been exceeded, the row the item is trying to be added to is full or the item you tried to add is not allowed in this View.
```

--------------------------------

### remove_dynamic_items(*items)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes DynamicItem classes from persistent listening.

```APIDOC
## remove_dynamic_items(*items)

### Description
Removes DynamicItem classes from persistent listening. Accepts class types rather than instances.

### Parameters
- **items** (Type[DynamicItem]) - Required - The classes of dynamic items to remove.
```

--------------------------------

### fetch_role(role_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a Role object with the specified ID via an API call.

```APIDOC
## fetch_role(role_id)

### Description
Retrieves a `Role` with the specified ID. This is an API call.

### Parameters
- **role_id** (`int`) - Required - The role’s ID.

### Returns
- `Role` - The retrieved role.

### Raises
- **NotFound** - The role requested could not be found.
- **HTTPException** - An error occurred fetching the role.
```

--------------------------------

### overwrites_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the channel-specific overwrites for a member or a role.

```APIDOC
## overwrites_for(obj)

### Description
Returns the channel-specific overwrites for a member or a role.

### Parameters
- **obj** (Union[Role, User, Object]) - Required - The role or user denoting whose overwrite to get.

### Returns
- **PermissionOverwrite** - The permission overwrites for this object.
```

--------------------------------

### create_guild(name, icon=..., code=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a new Guild.

```APIDOC
## create_guild(name, icon=..., code=...)

### Description
Creates a Guild. Bot accounts in more than 10 guilds are not allowed to create guilds.

### Parameters
- **name** (str) - Required - The name of the guild.
- **icon** (Optional[bytes]) - Optional - The bytes-like object representing the icon.
- **code** (str) - Optional - The code for a template to create the guild with.
```

--------------------------------

### StageInstance.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the stage instance. Requires manage_channels permission.

```APIDOC
## await StageInstance.edit(topic=..., privacy_level=..., reason=None)

### Description
Edits the stage instance. You must have `manage_channels` to do this.

### Parameters
- **topic** (str) - Optional - The stage instance’s new topic.
- **privacy_level** (PrivacyLevel) - Optional - The stage instance’s new privacy level.
- **reason** (str) - Optional - The reason the stage instance was edited. Shows up on the audit log.

### Raises
- **TypeError** - If the privacy_level parameter is not the proper type.
- **Forbidden** - You do not have permissions to edit the stage instance.
- **HTTPException** - Editing a stage instance failed.
```

--------------------------------

### Define a LayoutView with a File component

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Example of using the File component within a LayoutView to reference an attachment.

```python
import discord
from discord import ui


class MyView(ui.LayoutView):
    file = ui.File("attachment://file.txt")
    # attachment://file.txt points to an attachment uploaded alongside this view
```

--------------------------------

### move(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves a channel relative to other channels or categories.

```APIDOC
## move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. Requires manage_channels permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning of the list.
- **end** (bool) - Optional - Move to the end of the list.
- **before** (Snowflake) - Optional - Move before the given channel.
- **after** (Snowflake) - Optional - Move after the given channel.
- **offset** (int) - Optional - Number of channels to offset the move.
- **category** (Snowflake) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the category.
- **reason** (str) - Optional - The reason for the move.
```

--------------------------------

### discord.ui.ChannelSelect

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of predefined options with the current channels in the guild.

```APIDOC
## class discord.ui.ChannelSelect

### Description
Represents a UI select menu with a list of predefined options with the current channels in the guild. Note that if used in a private message, no channels will be displayed.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu. Max 100 characters.
- **channel_types** (List[ChannelType]) - Optional - The types of channels to show. Defaults to all.
- **placeholder** (Optional[str]) - Optional - Placeholder text. Max 150 characters.
- **min_values** (int) - Optional - Minimum items to choose. Defaults to 1 (0-25).
- **max_values** (int) - Optional - Maximum items to choose. Defaults to 1 (1-25).
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required (only for modals).
- **default_values** (Sequence[Snowflake]) - Optional - Channels selected by default.
- **row** (Optional[int]) - Optional - Relative row index (0-4).
- **id** (Optional[int]) - Optional - Unique component ID.

### Methods
- **callback(interaction)**: Coroutine. The callback associated with this UI item.
- **interaction_check(interaction)**: Coroutine. Checks whether the callback should be processed.
```

--------------------------------

### @discord.ext.commands.hybrid_command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator that transforms a function into a HybridCommand, which functions as both a regular text command and an application command.

```APIDOC
## @discord.ext.commands.hybrid_command(name=..., *, with_app_command=True, **attrs)

### Description
Transforms a function into a `HybridCommand`. This command type functions as both a regular `Command` and an `app_commands.Command`.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name to create the command with.
- **with_app_command** (bool) - Optional - Whether to register the command also as an application command. Defaults to `True`.
- **attrs** (dict) - Optional - Keyword arguments to pass into the construction of the hybrid command.
```

--------------------------------

### discord.ui.UserSelect

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of predefined options with the current members of the guild.

```APIDOC
## class discord.ui.UserSelect

### Description
Represents a UI select menu with a list of predefined options with the current members of the guild. If sent in a private message, it allows selection of the client or the user themselves.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu. Max 100 characters.
- **placeholder** (Optional[str]) - Optional - Placeholder text. Max 150 characters.
- **min_values** (int) - Optional - Minimum items to choose. Defaults to 1, range 0-25.
- **max_values** (int) - Optional - Maximum items to choose. Defaults to 1, range 1-25.
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required (only for modals).
- **default_values** (Sequence[Snowflake]) - Optional - List of users selected by default.
- **row** (Optional[int]) - Optional - The relative row index (0-4).
- **id** (Optional[int]) - Optional - Unique ID of the component.
```

--------------------------------

### Bot.run

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A blocking call that abstracts away the event loop initialization. This function must be the last function called as it blocks execution.

```APIDOC
## Bot.run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

### Description
A blocking call that abstracts away the event loop initialisation. This function also sets up the logging library.

### Parameters
- **token** (str) - Required - The authentication token.
- **reconnect** (bool) - Optional - If we should attempt reconnecting.
- **log_handler** (Optional[logging.Handler]) - Optional - The log handler to use.
- **log_formatter** (logging.Formatter) - Optional - The formatter to use with the given log handler.
- **log_level** (int) - Optional - The default log level for the library's logger.
- **root_logger** (bool) - Optional - Whether to set up the root logger.
```

--------------------------------

### discord.on_member_remove

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Member leaves a Guild. Requires Intents.members.

```APIDOC
## discord.on_member_remove(member)

### Description
Called when a Member leaves a Guild. This requires Intents.members to be enabled.

### Parameters
- **member** (Member) - The member who left.
```

--------------------------------

### discord.utils.format_dt

Source: https://discordpy.readthedocs.io/en/latest/api.html

Formats a datetime object for presentation within Discord.

```APIDOC
## discord.utils.format_dt(dt, /, style=None)

### Description
A helper function to format a datetime.datetime for presentation within Discord.

### Parameters
- **dt** (datetime.datetime) - Required - The datetime to format.
- **style** (str) - Optional - The style to format the datetime with.

### Returns
- **str** - The formatted string.
```

--------------------------------

### role_member_counts()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a mapping of roles to the number of members that have them.

```APIDOC
## role_member_counts()

### Description
Retrieves a mapping of roles to the number of members that have it.

### Returns
- `Dict[Union[Object, Role], int]` - A mapping of roles to the number of members that have it.
```

--------------------------------

### discord.app_commands.checks.bot_has_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that checks if the bot itself has the specified permissions. It relies on discord.Interaction.app_permissions and raises BotMissingPermissions if the check fails.

```APIDOC
## @discord.app_commands.checks.bot_has_permissions(perms)

### Description
Checks if the bot has the required permissions to execute the command.

### Parameters
- **perms** (discord.Permissions) - Required - The permissions to check for.
```

--------------------------------

### Create an Abstract Cog Mixin

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use CogMeta to create a custom metaclass for abstract cog mixins.

```python
import abc


class CogABCMeta(commands.CogMeta, abc.ABCMeta):
    pass


class SomeMixin(metaclass=abc.ABCMeta):
    pass


class SomeCogMixin(SomeMixin, commands.Cog, metaclass=CogABCMeta):
    pass
```

--------------------------------

### fetch_premium_sticker_pack

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a premium sticker pack with the specified ID.

```APIDOC
## fetch_premium_sticker_pack(sticker_pack_id)

### Description
Retrieves a premium sticker pack with the specified ID.

### Parameters
- **sticker_pack_id** (int) - Required - The sticker pack’s ID to fetch from.

### Returns
- **StickerPack** - The retrieved premium sticker pack.
```

--------------------------------

### View.from_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Converts a message’s components into a View or LayoutView.

```APIDOC
## classmethod from_message(message, *, timeout=180.0)

### Description
Converts a message’s components into a View or LayoutView. This is required to modify and edit message components.

### Parameters
- **message** (discord.Message) - Required - The message with components to convert into a view.
- **timeout** (Optional[float]) - Optional - The timeout of the converted view.
```

--------------------------------

### discord.utils.maybe_coroutine

Source: https://discordpy.readthedocs.io/en/latest/api.html

A helper function that awaits the result of a function if it is a coroutine, or returns the result if it is not.

```APIDOC
## discord.utils.maybe_coroutine

### Description
A helper function that will await the result of a function if it’s a coroutine or return the result if it’s not. This is useful for functions that may or may not be coroutines.

### Parameters
- **f** (Callable) - Required - The function or coroutine to call.
- ***args** - Optional - The arguments to pass to the function.
- ***kwargs** - Optional - The keyword arguments to pass to the function.
```

--------------------------------

### unpin

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Unpins the message from the channel.

```APIDOC
## await unpin(reason=None)

### Description
Unpins the message. Requires pin_messages permission.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for unpinning the message, shown in the audit log.

### Raises
- **Forbidden** - Missing permissions.
- **NotFound** - Message or channel not found.
- **HTTPException** - Unpinning failed.
```

--------------------------------

### from_interaction(interaction)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a context from a discord.Interaction. This only works on application command based interactions.

```APIDOC
## from_interaction(interaction)

### Description
Creates a context from a discord.Interaction. This only works on application command based interactions, such as slash commands or context menus.

### Parameters
- **interaction** (discord.Interaction) - Required - The interaction to create a context with.
```

--------------------------------

### PartialEmoji.save

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the emoji asset into a file-like object.

```APIDOC
## await PartialEmoji.save(fp, *, seek_begin=True)

### Description
Saves this asset into a file-like object. This is a coroutine.

### Parameters
- **fp** (`Union[io.BufferedIOBase, os.PathLike]`) - Required - The file-like object to save this asset to or the filename to use.
- **seek_begin** (`bool`) - Optional - Whether to seek to the beginning of the file after saving is successfully done.

### Returns
- `int` - The number of bytes written.
```

--------------------------------

### discord.ui.Checkbox

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a checkbox component within a modal.

```APIDOC
## class discord.ui.Checkbox(custom_id=..., default=False, id=None)

### Description
Represents a checkbox component within a modal that can only be used in Label.

### Parameters
- **id** (Optional[int]) - Optional - The ID of the component. This must be unique across the view.
- **custom_id** (Optional[str]) - Optional - The custom ID of the component.
- **default** (bool) - Optional - Whether this checkbox is selected by default.
```

--------------------------------

### add_listener

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a coroutine as an event listener.

```APIDOC
## add_listener(func, /, name=...)

### Description
The non-decorator alternative to `listen()`. Registers a function to be called when a specific event occurs.

### Parameters
- **func** (coroutine) - Required - The function to call.
- **name** (str) - Optional - The name of the event to listen for. Defaults to `func.__name__`.
```

--------------------------------

### Basic Integer Converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses type annotations to automatically convert command arguments into integers.

```python
@bot.command()
async def add(ctx, a: int, b: int):
    await ctx.send(a + b)
```

--------------------------------

### publish()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Publishes the message to the channel's followers.

```APIDOC
## publish()

### Description
Publishes this message to the channel’s followers. Must be in a news channel. Requires 'send_messages' permission, and 'manage_messages' if the message is not your own. This is a coroutine.

### Raises
- **Forbidden** - Insufficient permissions or not a news channel.
- **HTTPException** - Publishing failed.
```

--------------------------------

### View.remove_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes an item from the view.

```APIDOC
## remove_item(item)

### Description
Removes an item from the view. Returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to remove from the view.
```

--------------------------------

### reinvoke(call_hooks=False, restart=True)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Calls the command again, bypassing checks, cooldowns, and error handlers.

```APIDOC
## reinvoke(call_hooks=False, restart=True)

### Description
Calls the command again. This is similar to invoke() except that it bypasses checks, cooldowns, and error handlers.

### Parameters
- **call_hooks** (bool) - Optional - Whether to call the before and after invoke hooks.
- **restart** (bool) - Optional - Whether to start the call chain from the very beginning or where we left off.
```

--------------------------------

### webhooks

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the list of webhooks for the channel.

```APIDOC
## webhooks()

### Description
Gets the list of webhooks from this channel. This is a coroutine.

### Returns
- List[Webhook] - The webhooks for this channel.
```

--------------------------------

### fetch_emoji(emoji_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific custom emoji from the guild by its ID.

```APIDOC
## await fetch_emoji(emoji_id)

### Description
Retrieves a custom `Emoji` from the guild.

### Parameters
- **emoji_id** (int) - Required - The emoji’s ID.

### Returns
- **Emoji** - The retrieved emoji.

### Raises
- **NotFound** - The emoji requested could not be found.
- **HTTPException** - An error occurred fetching the emoji.
```

--------------------------------

### discord.ui.Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI container for layout components.

```APIDOC
## class discord.ui.Container

### Description
Represents a UI container. This is a top-level layout component that can only be used on LayoutView and can contain ActionRows, TextDisplays, Sections, MediaGallerys, Files, and Separators.

### Constructor Parameters
- **children** (Any) - Required - The children components to add to the container.
- **accent_colour** (Optional) - Optional - The accent colour of the container.
- **accent_color** (Optional) - Optional - The accent color of the container.
- **spoiler** (bool) - Optional - Whether the container is a spoiler.
- **id** (Optional[int]) - Optional - The ID of the container.
```

--------------------------------

### discord.utils.get

Source: https://discordpy.readthedocs.io/en/latest/api.html

A helper that returns the first element in the iterable that meets all the traits passed in attrs.

```APIDOC
## discord.utils.get(iterable, **attrs)

### Description
A helper that returns the first element in the iterable that meets all the traits passed in attrs. When multiple attributes are specified, they are checked using logical AND.

### Parameters
- **iterable** (Union[Iterable, AsyncIterable]) - Required - The iterable to search through.
- **attrs** (Any) - Optional - Keyword arguments representing attributes to match.
```

--------------------------------

### discord.on_guild_join(guild)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when the client joins a guild or a guild is created.

```APIDOC
## discord.on_guild_join(guild)

### Description
Called when a `Guild` is either created by the `Client` or when the `Client` joins a guild. Requires `Intents.guilds` to be enabled.

### Parameters
- **guild** (Guild) - Required - The guild that was joined.
```

--------------------------------

### Register a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Register a defined cog instance with the bot.

```python
await bot.add_cog(Greetings(bot))
```

--------------------------------

### add_files

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds new files to the end of the message attachments.

```APIDOC
## await add_files(*files)

### Description
Adds new files to the end of the message attachments.

### Parameters
- **files** (File) - Required - New files to add.

### Returns
- **InteractionMessage** - The newly edited message.
```

--------------------------------

### discord.ui.Modal

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI modal. This object must be inherited to create a modal popup window within discord.

```APIDOC
## class discord.ui.Modal(title=..., timeout=None, custom_id=...)

### Description
Represents a UI modal. This object must be inherited to create a modal popup window within discord.

### Parameters
- **title** (str) - Required - The title of the modal. Can only be up to 45 characters.
- **timeout** (Optional[float]) - Optional - Timeout in seconds from last interaction with the UI before no longer accepting input. If None then there is no timeout.
- **custom_id** (str) - Optional - The ID of the modal that gets received during an interaction. If not given then one is generated for you. Can only be up to 100 characters.
```

--------------------------------

### ForumChannel.set_permissions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the permissions for a member or role in the forum channel.

```APIDOC
## async ForumChannel.set_permissions(target, overwrite=None, **permissions, reason=None)

### Description
Sets the permissions for a specific member or role within the forum channel. This method allows for granular control over channel access and actions.

### Parameters
- **target** (Union[Member, Role]) - Required - The member or role to overwrite permissions for.
- **overwrite** (Optional[PermissionOverwrite]) - Optional - The permissions to allow and deny to the target, or None to delete the overwrite.
- **permissions** (dict) - Optional - A keyword argument list of permissions to set for ease of use. Cannot be mixed with overwrite.
- **reason** (Optional[str]) - Optional - The reason for doing this action, which appears in the audit log.

### Raises
- **Forbidden** - You do not have permissions to edit channel specific permissions.
- **HTTPException** - Editing channel specific permissions failed.
- **NotFound** - The role or member being edited is not part of the guild.
- **TypeError** - The overwrite parameter was invalid or the target type was not Role or Member.
- **ValueError** - The overwrite parameter and positions parameters were both unset.
```

--------------------------------

### discord.app_commands.Cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a cooldown object for managing rate limits.

```APIDOC
## class discord.app_commands.Cooldown(rate, per)

### Description
Represents a cooldown configuration.

### Attributes
- **rate** (float) - Total tokens available.
- **per** (float) - Time period in seconds.

### Methods
- **get_tokens(current=None)** - Returns available tokens.
```

--------------------------------

### ui.File

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI file component used within a LayoutView.

```APIDOC
## ui.File

### Description
A top-level layout component representing a file. Used to display media or files within a view.

### Parameters
- **media** (Union[str, UnfurledMediaItem, discord.File]): The file media.
- **spoiler** (bool): Whether to flag as a spoiler.
- **id** (Optional[int]): Unique ID of the component.

### Properties
- **id** (int): The ID of the file component.
- **media** (UnfurledMediaItem): The file media.
- **url** (str): The URL of the file.
- **spoiler** (bool): Whether the file is a spoiler.
```

--------------------------------

### fetch_guild_preview

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a preview of a guild.

```APIDOC
## await fetch_guild_preview(guild_id)

### Description
Retrieves a preview of a `Guild` from an ID. If the guild is discoverable, you don’t have to be a member.

### Parameters
- **guild_id** (int) - Required - The guild’s ID.

### Raises
- **NotFound** - Guild doesn’t exist or is not discoverable.
- **HTTPException** - Getting the guild failed.
```

--------------------------------

### await delete(reason=None, prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the webhook.

```APIDOC
## await delete(reason=None, prefer_auth=True)

### Description
Deletes this Webhook.

### Parameters
- **reason** (str) - Optional - The reason for deleting this webhook. Shows up on the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### MemberCacheFlags.all()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance with all flags enabled.

```APIDOC
## MemberCacheFlags.all()

### Description
A factory method that creates a MemberCacheFlags instance with everything enabled.

### Returns
- **MemberCacheFlags** - The resulting member cache flags object.
```

--------------------------------

### await original_response()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches the original interaction response message associated with the interaction.

```APIDOC
## await original_response()

### Description
Fetches the original interaction response message associated with the interaction. If the response was a newly created message, it returns that message; otherwise, it returns the message that triggered the interaction.

### Returns
- **InteractionMessage** - The original interaction response message.
```

--------------------------------

### clear_reactions()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes all reactions from the message. Requires manage_messages permission.

```APIDOC
## await clear_reactions()

### Description
Removes all the reactions from the message. You must have `manage_messages` permission to perform this action.

### Raises
- **HTTPException** - Removing the reactions failed.
- **Forbidden** - You do not have the proper permissions to remove all the reactions.
```

--------------------------------

### create_guild

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new guild. Note that bot accounts in more than 10 guilds are not allowed to create guilds.

```APIDOC
## await create_guild(name, icon=..., code=...)

### Description
Creates a new Guild. Note that bot accounts in more than 10 guilds are not allowed to create guilds.

### Parameters
- **name** (str) - Required - The name of the guild.
- **icon** (Optional[bytes]) - Optional - The bytes-like object representing the icon.
- **code** (str) - Optional - The code for a template to create the guild with.

### Returns
- **Guild** - The guild created.
```

--------------------------------

### Webhook.partial

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial Webhook object using an ID and token.

```APIDOC
## Webhook.partial(id, token, *, session=..., client=..., bot_token=None)

### Description
Creates a partial Webhook object using the provided ID and authentication token.

### Parameters
- **id** (int) - Required - The ID of the webhook.
- **token** (str) - Required - The authentication token of the webhook.
- **session** (aiohttp.ClientSession) - Optional - The session to use to send requests with.
- **client** (Client) - Optional - The client to initialise this webhook with.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.

### Returns
- **Webhook** - A partial Webhook object.
```

--------------------------------

### GroupChannel.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination.

```APIDOC
## async GroupChannel.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is called using `await`.

### Example Usage
```python
async with channel.typing():
    # simulate something heavy
    await asyncio.sleep(20)

await channel.send('Done!')
```

```python
await channel.typing()
```
```

--------------------------------

### PartialEmoji.read

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the emoji asset as a bytes object.

```APIDOC
## await PartialEmoji.read()

### Description
Retrieves the content of this asset as a `bytes` object. This is a coroutine.

### Returns
- `bytes` - The content of the asset.
```

--------------------------------

### edit(content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, delete_after=None, poll=...)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the content, embeds, attachments, or other properties of the interaction message.

```APIDOC
## edit(content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, delete_after=None, poll=...)

### Description
Edits the message.

### Parameters
- **content** (Optional[str]) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **delete_after** (Optional[float]) - Optional - Seconds to wait before deleting the message.
- **poll** (Poll) - Optional - The poll to create when editing the message.

### Returns
- **InteractionMessage** - The newly edited message.
```

--------------------------------

### Set Default Command Permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use default_permissions to provide a hint to Discord regarding the permissions required to execute a command. These are not enforced as checks and can be overridden by server administrators.

```python
@app_commands.command()
@app_commands.default_permissions(manage_messages=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("You may or may not have manage messages.")
```

```python
ADMIN_PERMS = discord.Permissions(administrator=True)


@app_commands.command()
@app_commands.default_permissions(ADMIN_PERMS, manage_messages=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("You may or may not have manage messages.")
```

--------------------------------

### Transform checks into custom decorators

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Encapsulates a check predicate within a factory function to create a reusable decorator.

```python
def is_me():
    def predicate(ctx):
        return ctx.message.author.id == 85309593344815104

    return commands.check(predicate)


@bot.command()
@is_me()
async def only_me(ctx):
    await ctx.send("Only you!")
```

--------------------------------

### Subclassing ui.Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Define a custom container by subclassing ui.Container and adding components via ActionRow decorators.

```python
# you can subclass it and add components as you would add them
# in a LayoutView
class MyContainer(ui.Container):
    action_row = ui.ActionRow()

    @action_row.button(label="A button in a container!")
    async def a_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You clicked a button!")
```

--------------------------------

### ForumChannel.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the properties of the forum channel.

```APIDOC
## await edit(*, reason=None, **options)

### Description
Edits the forum. Requires manage_channels permission.

### Parameters
- **name** (str) - Optional - The new forum name.
- **topic** (str) - Optional - The new forum’s topic.
- **position** (int) - Optional - The new forum’s position.
- **nsfw** (bool) - Optional - To mark the forum as NSFW or not.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the category.
- **category** (Optional[CategoryChannel]) - Optional - The new category for this forum.
- **slowmode_delay** (int) - Optional - Specifies the slowmode rate limit in seconds.
- **reason** (Optional[str]) - Optional - The reason for editing this forum for the audit log.
- **available_tags** (Sequence[ForumTag]) - Optional - The new available tags for this forum.
```

--------------------------------

### SyncWebhookMessage.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits an existing message sent by the webhook.

```APIDOC
## edit(*, content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, view=...)

### Description
Edits the message content, embeds, attachments, or view.

### Parameters
- **content** (Optional[str]) - Optional - The content to edit the message with or None to clear it.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - The updated view to update this message with.

### Returns
- **SyncWebhookMessage** - The newly edited message.

### Raises
- **HTTPException** - Editing the message failed.
- **Forbidden** - Edited a message that is not yours.
- **TypeError** - You specified both embed and embeds.
- **ValueError** - The length of embeds was invalid or there was no token associated with this webhook.
```

--------------------------------

### pin(*, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Pins the message to the channel.

```APIDOC
## await pin(*, reason=None)

### Description
Pins the message. You must have `pin_messages` permission to do this in a non-private channel.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message, which appears in the audit log.
```

--------------------------------

### discord.ui.Select

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of custom options, displayed as a dropdown menu.

```APIDOC
## class discord.ui.Select

### Description
Represents a UI select menu with a list of custom options. This is represented to the user as a dropdown menu.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu that gets received during an interaction.
- **placeholder** (Optional[str]) - Optional - The placeholder text that is shown if nothing is selected.
- **min_values** (int) - Optional - The minimum number of items that must be chosen (0-25). Defaults to 1.
- **max_values** (int) - Optional - The maximum number of items that must be chosen (1-25). Defaults to 1.
- **options** (List[discord.SelectOption]) - Optional - A list of options that can be selected in this menu.
- **disabled** (bool) - Optional - Whether the select is disabled or not.
- **required** (bool) - Optional - Whether the select is required (only applicable within modals).
- **row** (Optional[int]) - Optional - The relative row this select menu belongs to (0-4).
- **id** (Optional[int]) - Optional - The ID of the component, must be unique across the view.
```

--------------------------------

### bulk_ban(users, *, reason=None, delete_message_seconds=86400)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bans multiple users from the guild. Requires ban_members and manage_guild permissions.

```APIDOC
## bulk_ban(users, *, reason=None, delete_message_seconds=86400)

### Description
Bans multiple users from the guild. The users must meet the abc.Snowflake abc. You must have ban_members and manage_guild to do this. New in version 2.4.

### Parameters
- **users** (Iterable[abc.Snowflake]) - Required - The users to ban from the guild, up to 200 users.
- **delete_message_seconds** (int) - Optional - The number of seconds worth of messages to delete from the user in the guild.
- **reason** (Optional[str]) - Optional - The reason the users got banned.

### Raises
- **Forbidden** - You do not have the proper permissions to ban.
- **HTTPException** - Banning failed.
```

--------------------------------

### Messageable.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination. Supports text content, embeds, files, and various message metadata.

```APIDOC
## await Messageable.send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

### Description
Sends a message to the destination. The content must be convertible to a string. If content is None, an embed must be provided.

### Parameters
- **content** (str) - Optional - The message content.
- **tts** (bool) - Optional - Whether the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - A single embed to send.
- **embeds** (List[Embed]) - Optional - A list of embeds to send.
- **file** (File) - Optional - A single file to upload.
- **files** (List[File]) - Optional - A list of files to upload.
- **stickers** (List[Sticker]) - Optional - A list of stickers to send.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **silent** (bool) - Optional - Whether the message should be sent without triggering a notification.
```

--------------------------------

### Registering multiple event listeners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

The @bot.listen() decorator allows multiple functions to listen to the same event, executing them in an unspecified order.

```python
@bot.listen()
async def on_message(message):
    print("one")


# in some other file...


@bot.listen("on_message")
async def my_message(message):
    print("two")
```

--------------------------------

### discord.opus.load_opus(name)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Loads the libopus shared library for use with voice. If not called, the library attempts to find and load it automatically.

```APIDOC
## discord.opus.load_opus(name)

### Description
Loads the libopus shared library for use with voice. If this function is not called, the library uses `ctypes.util.find_library()` to locate and load it.

### Parameters
- **name** (str) - Required - The filename of the shared library.
```

--------------------------------

### create_template

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new template for the guild.

```APIDOC
## await create_template(*, name, description=...)

### Description
Creates a template for the guild. Requires manage_guild permission.

### Parameters
- **name** (str) - Required - The name of the template.
- **description** (str) - Optional - The description of the template.

### Returns
- **Template** - The created template.
```

--------------------------------

### LayoutView.from_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Converts a message's components into a View or LayoutView to allow for modification and editing.

```APIDOC
## LayoutView.from_message(message, *, timeout=180.0)

### Description
Converts a message's components into a View or LayoutView. This is required to modify or edit message components.

### Parameters
- **message** (discord.Message) - Required - The message with components to convert.
- **timeout** (Optional[float]) - Optional - The timeout of the converted view.

### Returns
- **Union[View, LayoutView]** - The converted view.
```

--------------------------------

### Retrieve a Cog for Inter-command Communication

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Use get_cog to access another cog's methods for sharing data or functionality.

```python
class Economy(commands.Cog):
    ...

    async def withdraw_money(self, member, money):
        # implementation here
        ...

    async def deposit_money(self, member, money):
        # implementation here
        ...


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def coinflip(self):
        return random.randint(0, 1)

    @commands.command()
    async def gamble(self, ctx, money: int):
        """Gambles some money."""
        economy = self.bot.get_cog("Economy")
        if economy is not None:
            await economy.withdraw_money(ctx.author, money)
            if self.coinflip() == 1:
                await economy.deposit_money(ctx.author, money * 1.5)
```

--------------------------------

### Register an autocomplete handler for a command parameter

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the @autocomplete decorator to provide dynamic choices for a command parameter. The callback must return a list of up to 25 Choice objects.

```python
@app_commands.command()
async def fruits(interaction: discord.Interaction, fruit: str):
    await interaction.response.send_message(f"Your favourite fruit seems to be {fruit}")


@fruits.autocomplete("fruit")
async def fruits_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    fruits = ["Banana", "Pineapple", "Apple", "Watermelon", "Melon", "Cherry"]
    return [app_commands.Choice(name=fruit, value=fruit) for fruit in fruits if current.lower() in fruit.lower()]
```

--------------------------------

### invites()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all active instant invites for the channel.

```APIDOC
## invites()

### Description
Returns a list of all active instant invites from this channel. Requires manage_channels permission.

### Returns
- **List[Invite]** - The list of invites that are currently active.
```

--------------------------------

### clear_commands

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Clears all application commands from the tree locally.

```APIDOC
## clear_commands(*, guild, type=None)

### Description
Clears all application commands from the tree. This only removes the commands locally – in order to sync the commands and remove them in the client, sync() must be called.

### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to remove the commands from. If None then it removes all global commands instead.
- **type** (AppCommandType) - Optional - The type of command to clear. If not given or None then it removes all commands regardless of the type.
```

--------------------------------

### Emoji.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the custom emoji's name or allowed roles.

```APIDOC
## await edit(*, name=..., roles=..., reason=None)

### Description
Edits the custom emoji. You must have `manage_emojis` to do this.

### Parameters
- **name** (str) - Optional - The new emoji name.
- **roles** (List[Snowflake]) - Optional - A list of roles that can use this emoji. An empty list can be passed to make it available to everyone. This does not apply if `is_application_owned()` is `True`.
- **reason** (Optional[str]) - Optional - The reason for editing this emoji. Shows up on the audit log. This does not apply if `is_application_owned()` is `True`.

### Returns
- **Emoji** - The newly updated emoji.
```

--------------------------------

### Define a GroupCog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Create a cog that functions as a parent group for application commands.

```python
from discord import app_commands
from discord.ext import commands


@app_commands.guild_only()
class MyCog(commands.GroupCog, group_name="my-cog"):
    pass
```

--------------------------------

### get_channel

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a channel or thread with the given ID.

```APIDOC
## get_channel(id)

### Description
Returns a channel or thread with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[Union[abc.GuildChannel, Thread, abc.PrivateChannel]]** - The returned channel or None if not found.
```

--------------------------------

### create_entitlement(sku, owner, owner_type)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a test Entitlement for the application.

```APIDOC
## create_entitlement(sku, owner, owner_type)

### Description
Creates a test Entitlement for the application.

### Parameters
- **sku** (Snowflake) - Required - The SKU to create the entitlement for.
- **owner** (Snowflake) - Required - The ID of the owner.
- **owner_type** (EntitlementOwnerType) - Required - The type of the owner.
```

--------------------------------

### discord.on_audit_log_entry_create

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild gets a new audit log entry. Requires Intents.moderation.

```APIDOC
## discord.on_audit_log_entry_create(entry)

### Description
Called when a Guild gets a new audit log entry. You must have view_audit_log to receive this. This requires Intents.moderation to be enabled.

### Parameters
- **entry** (AuditLogEntry) - The audit log entry that was created.
```

--------------------------------

### discord.ui.CheckboxGroup

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a checkbox group component within a modal.

```APIDOC
## class discord.ui.CheckboxGroup(custom_id=..., required=True, min_values=None, max_values=None, options=..., id=None)

### Description
Represents a checkbox group component within a modal that can only be used in Label.

### Parameters
- **id** (Optional[int]) - Optional - The ID of the component.
- **custom_id** (Optional[str]) - Optional - The custom ID of the component.
- **options** (List[discord.CheckboxGroupOption]) - Required - A list of options that can be selected.
- **max_values** (Optional[int]) - Optional - The maximum number of options that can be selected.
- **min_values** (Optional[int]) - Optional - The minimum number of options that must be selected.
- **required** (bool) - Optional - Whether this component is required.

### Methods
- **add_option(label, value=..., description=None, default=False)**: Adds an option to the checkbox group.
- **append_option(option)**: Appends an option to the checkbox group.
```

--------------------------------

### remove_check(func, /, *, call_once=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a global check from the bot.

```APIDOC
## remove_check(func, /, *, call_once=False)

### Description
Removes a global check from the bot. This function is idempotent.

### Parameters
- **func** (Callable) - Required - The function to remove from the global checks.
- **call_once** (bool) - Optional - Whether the function was added with call_once=True.
```

--------------------------------

### Pass Metaclass Attributes

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Pass metaclass attributes as keyword-only arguments during class creation.

```python
class MyCog(commands.Cog, name="My Cog"):
    pass
```

--------------------------------

### Restrict Application Commands to a Guild

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Register commands to specific guilds using decorators or class-level configuration to limit their availability.

```python
@app_commands.command()  # or @tree.command()
@app_commands.guilds(123456789012345678)  # or @app_commands.guilds(discord.Object(123456789012345678))
async def ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")


# or GroupCog (applies to all subcommands):


@app_commands.guilds(123456789012345678)
class MyGroup(commands.GroupCog):
    @app_commands.command()
    async def pong(self, interaction: Interaction):
        await interaction.response.send_message("Ping!")
```

--------------------------------

### Create a custom converter by extending MemberConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows how to build a custom converter by inheriting from an existing converter and overriding the convert method.

```python
class MemberRoles(commands.MemberConverter):
    async def convert(self, ctx, argument):
        member = await super().convert(ctx, argument)
        return [role.name for role in member.roles[1:]]  # Remove everyone role!


@bot.command()
async def roles(ctx, *, member: MemberRoles):
    """Tells you a member's roles."""
    await ctx.send("I see the following roles: " + ", ".join(member))
```

--------------------------------

### forward(destination, *, fail_if_not_exists=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Forwards the message to a specified channel.

```APIDOC
## await forward(destination, *, fail_if_not_exists=True)

### Description
Forwards this message to a channel.

### Parameters
- **destination** (Messageable) - Required - The channel to forward this message to.
- **fail_if_not_exists** (bool) - Optional - Whether replying using the message reference should raise `HTTPException` if the message no longer exists.
```

--------------------------------

### Use List for repeated flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Using typing.List allows a flag to be passed multiple times in a command.

```python
from discord.ext import commands
from typing import List
import discord


class BanFlags(commands.FlagConverter):
    members: List[discord.Member] = commands.flag(name="member")
    reason: str
    days: int = 1


@commands.command()
async def ban(ctx, *, flags: BanFlags):
    for member in flags.members:
        await member.ban(reason=flags.reason, delete_message_days=flags.days)

    members = ", ".join(str(member) for member in flags.members)
    plural = f"{flags.days} days" if flags.days != 1 else f"{flags.days} day"
    await ctx.send(f"Banned {members} for {flags.reason!r} (deleted {plural} worth of messages)")
```

--------------------------------

### await edit_original_response(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the original interaction response message.

```APIDOC
## await edit_original_response(**kwargs)

### Description
Edits the original interaction response message. This is a lower-level interface to InteractionMessage.edit() and is the only way to edit ephemeral messages.

### Parameters
- **content** (Optional[str]) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Optional[Union[View, LayoutView]]) - Optional - The updated view to update this message with.
- **poll** (Poll) - Optional - The poll to create when editing the message.

### Returns
- **InteractionMessage** - The newly edited message.
```

--------------------------------

### Delete channel permission overwrites

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes existing permission overwrites for a specific target by setting the overwrite parameter to None.

```python
await channel.set_permissions(member, overwrite=None)
```

--------------------------------

### create_tag

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new tag in the forum channel. Requires manage_channels permission.

```APIDOC
## await create_tag(name, emoji=None, moderated=False, reason=None)

### Description
Creates a new tag in this forum. You must have `manage_channels` to do this.

### Parameters
- **name** (str) - Required - The name of the tag. Can only be up to 20 characters.
- **emoji** (Optional[Union[str, PartialEmoji]]) - Optional - The emoji to use for the tag.
- **moderated** (bool) - Optional - Whether the tag can only be applied by moderators.
- **reason** (Optional[str]) - Optional - The reason for creating this tag. Shows up on the audit log.

### Returns
- **ForumTag** - The newly created tag.
```

--------------------------------

### Restrict Installation Contexts

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use allowed_installs to specify whether a command is installable in guilds, by users, or both. This decorator is ignored when applied to subcommands.

```python
@app_commands.command()
@app_commands.allowed_installs(guilds=False, users=True)
async def my_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in users by default!")
```

--------------------------------

### @discord.app_commands.context_menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Creates an application command context menu from a function. The function must accept an Interaction as the first parameter and a Member, User, or Message as the second.

```APIDOC
## @discord.app_commands.context_menu

### Description
Creates an application command context menu from a regular function.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the context menu command.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **auto_locale_strings** (bool) - Optional - Whether to wrap translatable strings in locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary to store extraneous data.
```

--------------------------------

### discord.on_bulk_message_delete(messages)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when multiple messages are bulk deleted. Requires at least one message to be in the internal message cache and Intents.messages to be enabled.

```APIDOC
## discord.on_bulk_message_delete(messages)

### Description
Called when messages are bulk deleted. If none of the messages are found in the internal message cache, this event will not be called.

### Parameters
- **messages** (List[Message]) - Required - The messages that have been deleted.
```

--------------------------------

### unban(user, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unbans a user from the guild. Requires the ban_members permission.

```APIDOC
## unban(user, *, reason=None)

### Description
Unbans a user from the guild. The user must meet the abc.Snowflake abc. You must have ban_members to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to unban.
- **reason** (Optional[str]) - Optional - The reason for doing this action.

### Raises
- **NotFound** - The requested unban was not found.
- **Forbidden** - You do not have the proper permissions to unban.
- **HTTPException** - Unbanning failed.
```

--------------------------------

### Implement Custom Audio Probing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Define a custom callable to determine codec and bitrate information for an audio source.

```python
def custom_probe(source, executable):
    # some analysis code here
    return codec, bitrate


source = await discord.FFmpegOpusAudio.from_probe("song.webm", method=custom_probe)
voice_client.play(source)
```

--------------------------------

### ForumChannel.clone

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a copy of the current forum channel.

```APIDOC
## await clone(*, name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. Requires manage_channels permission.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel for the audit log.

### Returns
- **abc.GuildChannel** - The channel that was created.
```

--------------------------------

### fetch_webhook

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a Webhook with the specified ID.

```APIDOC
## await fetch_webhook(webhook_id)

### Description
Retrieves a Webhook with the specified ID.

### Parameters
- **webhook_id** (int) - Required - The webhook ID.

### Returns
- **Webhook** - The webhook you requested.

### Raises
- **HTTPException** - Retrieving the webhook failed.
- **NotFound** - Invalid webhook ID.
- **Forbidden** - You do not have permission to fetch this webhook.
```

--------------------------------

### select(cls, options, channel_types, placeholder, custom_id, min_values, max_values, disabled, default_values, id)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a select menu to the action row. The decorated function receives the ActionRow instance, the Interaction, and the select class instance.

```APIDOC
## select(cls, options, channel_types, placeholder, custom_id, min_values, max_values, disabled, default_values, id)

### Description
A decorator that attaches a select menu to the action row. The function being decorated should have three parameters: self (the ActionRow), the Interaction, and the chosen select class.

### Parameters
- **cls** (Union[Type[Select], ...]) - Optional - The class to use for the select menu. Defaults to discord.ui.Select.
- **placeholder** (Optional[str]) - Optional - The placeholder text shown if nothing is selected (max 150 chars).
- **custom_id** (str) - Optional - The ID of the select menu received during interaction (max 100 chars).
- **min_values** (int) - Optional - Minimum number of items to be chosen (0-25). Defaults to 1.
- **max_values** (int) - Optional - Maximum number of items to be chosen (1-25). Defaults to 1.
- **options** (List[SelectOption]) - Optional - List of options for standard Select instances (max 25).
- **channel_types** (List[ChannelType]) - Optional - Types of channels to show for ChannelSelect instances.
- **disabled** (bool) - Optional - Whether the select is disabled. Defaults to False.
- **default_values** (Sequence[Snowflake]) - Optional - List of objects representing default values.
- **id** (Optional[int]) - Optional - Unique ID of the component.
```

--------------------------------

### discord.on_raw_poll_vote_add(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a poll gains a vote, regardless of cache state. Requires Intents.message_content and Intents.polls to be enabled.

```APIDOC
## discord.on_raw_poll_vote_add(payload)

### Description
Called when a Poll gains a vote. This is called regardless of the state of the internal user and message cache.

### Parameters
- **payload** (RawPollVoteActionEvent) - Required - The raw event payload data.
```

--------------------------------

### discord.on_raw_integration_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is deleted. Requires Intents.integrations.

```APIDOC
## discord.on_raw_integration_delete(payload)

### Description
Called when an integration is deleted. This requires Intents.integrations to be enabled.

### Parameters
- **payload** (RawIntegrationDeleteEvent) - The raw event payload data.
```

--------------------------------

### add_item(item)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the action row. Returns the class instance for fluent-style chaining.

```APIDOC
## add_item(item)

### Description
Adds an item to this action row. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (`Item`) - Required - The item to add to the action row.

### Raises
- **TypeError** - An `Item` was not passed.
- **ValueError** - Maximum number of children has been exceeded (5) or (40) for the entire view.
```

--------------------------------

### PermissionOverwrite.from_pair

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an overwrite from an allow/deny pair of Permissions.

```APIDOC
## from_pair(allow, deny)

### Description
Creates an overwrite from an allow/deny pair of Permissions.

### Parameters
- **allow** (Permissions) - The permissions to allow.
- **deny** (Permissions) - The permissions to deny.
```

--------------------------------

### Transform command arguments with typing.Annotated

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Annotated allows the library to use a specific converter while keeping the type hint clean for static analysis.

```python
from typing import Annotated


@bot.command()
async def fun(ctx, arg: Annotated[str, lambda s: s.upper()]):
    await ctx.send(arg)
```

--------------------------------

### Define a LayoutView with a Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Example of defining a custom LayoutView subclass with a container containing a text display.

```python
class MyView(ui.LayoutView):
    container = ui.Container(ui.TextDisplay("I am a text display on a container!"))
    # or you can use your subclass:
    # container = MyContainer()
```

--------------------------------

### Get sent message ID

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Access the ID of a message after sending it.

```python
message = await channel.send("hmm…")
message_id = message.id
```

--------------------------------

### SyncWebhook.from_url

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial SyncWebhook from a provided webhook URL.

```APIDOC
## SyncWebhook.from_url(url, *, session=..., bot_token=None)

### Description
Creates a partial SyncWebhook from a webhook URL.

### Parameters
- **url** (str) - Required - The URL of the webhook.
- **session** (requests.Session) - Optional - The session to use for requests.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.
```

--------------------------------

### remove_roles(*roles, reason=None, atomic=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes roles from the member. Requires manage_roles permission.

```APIDOC
## remove_roles(*roles, reason=None, atomic=True)

### Description
Removes Roles from this member. You must have manage_roles to use this, and the removed Roles must appear lower in the list of roles than the highest role of the client.

### Parameters
- **roles** (abc.Snowflake) - Required - An argument list of Snowflake representing a Role to remove from the member.
- **reason** (Optional[str]) - Optional - The reason for removing these roles. Shows up on the audit log.
- **atomic** (bool) - Optional - Whether to atomically remove roles.
```

--------------------------------

### create_text_channel(name, ...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel within the guild.

```APIDOC
## create_text_channel(name, *, reason=None, category=None, news=False, position=..., topic=..., slowmode_delay=..., nsfw=..., overwrites=..., default_auto_archive_duration=..., default_thread_slowmode_delay=...)

### Description
Creates a TextChannel for the guild. Requires manage_channels permission.

### Parameters
- **name** (str) - Required - The name of the channel.
- **reason** (str) - Optional - The reason for creating the channel.
- **category** (CategoryChannel) - Optional - The category to place the channel in.
- **news** (bool) - Optional - Whether the channel is a news channel.
- **overwrites** (dict) - Optional - A dictionary of permission overwrites.
```

--------------------------------

### create_instance(topic, privacy_level=..., send_start_notification=False, scheduled_event=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new stage instance for the channel. Requires the 'manage_channels' permission.

```APIDOC
## create_instance(topic, privacy_level=..., send_start_notification=False, scheduled_event=..., reason=None)

### Description
Creates a stage instance. You must have `manage_channels` to do this.

### Parameters
- **topic** (`str`) - Required - The stage instance’s topic.
- **privacy_level** (`PrivacyLevel`) - Optional - The stage instance’s privacy level. Defaults to `PrivacyLevel.guild_only`.
- **send_start_notification** (`bool`) - Optional - Whether to send a start notification. Defaults to `False`.
- **scheduled_event** (`Snowflake`) - Optional - The guild scheduled event associated with the stage instance.
- **reason** (`str`) - Optional - The reason the stage instance was created.

### Returns
- `StageInstance` - The newly created stage instance.
```

--------------------------------

### fetch_application_emoji

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a specific emoji for the current application.

```APIDOC
## await fetch_application_emoji(emoji_id)

### Description
Retrieves an emoji for the current application.

### Parameters
- **emoji_id** (int) - Required - The emoji ID to retrieve.

### Raises
- **MissingApplicationID** - The application ID could not be found.
- **HTTPException** - Retrieving the emoji failed.

### Returns
- **Emoji** - The emoji requested.
```

--------------------------------

### Button.callback

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

The coroutine callback associated with the UI item, which can be overridden by subclasses.

```APIDOC
## await callback(interaction)

### Description
The callback associated with this UI item. This function is a coroutine and can be overridden by subclasses.

### Parameters
- **interaction** (Interaction) - The interaction that triggered this UI item.
```

--------------------------------

### end_poll()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends the poll attached to the message.

```APIDOC
## await end_poll()

### Description
Ends the `Poll` attached to this message. Can only be performed by the message author.

### Returns
- **Message** - The updated message.
```

--------------------------------

### close

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Closes the connection to Discord.

```APIDOC
## await close()

### Description
Closes the connection to Discord.
```

--------------------------------

### create_custom_emoji(name, image, roles=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new custom emoji for the guild.

```APIDOC
## await create_custom_emoji(name, image, roles=..., reason=None)

### Description
Creates a custom `Emoji` for the guild. Requires `manage_emojis` permission.

### Parameters
- **name** (str) - Required - The emoji name.
- **image** (bytes) - Required - The bytes-like object representing the image data.
- **roles** (List[Role]) - Optional - A list of roles that can use this emoji.
- **reason** (Optional[str]) - Optional - The reason for creating this emoji.

### Returns
- **Emoji** - The created emoji.

### Raises
- **Forbidden** - You are not allowed to create emojis.
- **HTTPException** - An error occurred creating an emoji.
```

--------------------------------

### Reaction.users

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator representing the users that have reacted to the message.

```APIDOC
## async for ... in Reaction.users(*, limit=None, after=None, type=None)

### Description
Returns an asynchronous iterator representing the users that have reacted to the message.

### Parameters
- **limit** (int) - Optional - The maximum number of users to retrieve.
- **after** (abc.Snowflake) - Optional - Retrieve users after this specific user.
- **type** (ReactionType) - Optional - The type of reaction to filter by.
```

--------------------------------

### Update Message Sending Syntax

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The send_message and send_file methods have been merged into a single send() method on the channel object.

```python
# before
await client.send_message(channel, "Hello")

# after
await channel.send("Hello")
```

```python
e = discord.Embed(title="foo")
await channel.send("Hello", embed=e)
```

```python
# before
await client.send_file(channel, "cool.png", filename="testing.png", content="Hello")

# after
await channel.send("Hello", file=discord.File("cool.png", "testing.png"))
```

```python
my_files = [
    discord.File("cool.png", "testing.png"),
    discord.File(some_fp, "cool_filename.png"),
]

await channel.send("Your images:", files=my_files)
```

--------------------------------

### Use local files in embeds

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Upload a file and reference it in the embed URL using the attachment:// scheme.

```python
file = discord.File("path/to/my/image.png", filename="image.png")
embed = discord.Embed()
embed.set_image(url="attachment://image.png")
await channel.send(file=file, embed=embed)
```

--------------------------------

### Define a basic command converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates a simple command using a custom converter class.

```python
@bot.command()
async def slap(ctx, *, reason: Slapper()):
    await ctx.send(reason)
```

--------------------------------

### Create a reusable application command check decorator

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Wraps a predicate function inside a custom decorator to simplify applying the same check to multiple commands.

```python
def is_me():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == 85309593344815104

    return app_commands.check(predicate)


@tree.command()
@is_me()
async def only_me(interaction: discord.Interaction):
    await interaction.response.send_message("Only you!")
```

--------------------------------

### Restrict Commands via Decorator Argument

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Apply guild restrictions directly within the command decorator.

```python
@tree.command(guild=discord.Object(123456789012345678))
async def ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")
```

--------------------------------

### get_guild(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a guild from the cache by its ID.

```APIDOC
## get_guild(id)

### Description
Returns a guild with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Guild** (Optional) - The guild or None if not found.
```

--------------------------------

### delete_sticker

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a custom sticker from the guild.

```APIDOC
## await delete_sticker(sticker, reason)

### Description
Deletes the custom `Sticker` from the guild. You must have `manage_emojis_and_stickers` to do this.

### Parameters
- **sticker** (abc.Snowflake) - Required - The sticker you are deleting.
- **reason** (str) - Optional - The reason for deleting this sticker.
```

--------------------------------

### Update Embed title handling

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Demonstrates the change from using discord.Embed.Empty to None for clearing embed titles.

```python
# before
embed = discord.Embed(title="foo")
embed.title = discord.Embed.Empty
embed == embed.copy()  # False

# after
embed = discord.Embed(title="foo")
embed.title = None
embed == embed.copy()  # True
{embed, embed}  # Raises TypeError
```

--------------------------------

### Migrate Asynchronous Webhooks

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates the webhook initialization to remove the explicit AsyncWebhookAdapter.

```python
# before
async with aiohttp.ClientSession() as session:
    webhook = discord.Webhook.from_url("url-here", adapter=discord.AsyncWebhookAdapter(session))
    await webhook.send("Hello World", username="Foo")

# after
async with aiohttp.ClientSession() as session:
    webhook = discord.Webhook.from_url("url-here", session=session)
    await webhook.send("Hello World", username="Foo")
```

--------------------------------

### to_reference

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Creates a MessageReference from the current message.

```APIDOC
## to_reference(fail_if_not_exists=True, type=MessageReferenceType.default)

### Description
Creates a MessageReference from the current message.

### Parameters
- **fail_if_not_exists** (bool) - Optional - Whether the referenced message should raise HTTPException if the message no longer exists.
- **type** (MessageReferenceType) - Optional - The type of message reference.

### Returns
- **MessageReference** - The reference to this message.
```

--------------------------------

### Client.login

Source: https://discordpy.readthedocs.io/en/latest/api.html

Logs the client into Discord using the provided authentication token and triggers the setup hook.

```APIDOC
## login(token)

### Description
Logs in the client with the specified credentials and calls the setup_hook().

### Parameters
- **token** (str) - Required - The authentication token. Do not prefix this token with anything.

### Raises
- **LoginFailure** - The wrong credentials are passed.
- **HTTPException** - An unknown HTTP related error occurred.
```

--------------------------------

### fetch_instance()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the currently running stage instance for the channel.

```APIDOC
## fetch_instance()

### Description
Gets the running `StageInstance`.

### Returns
- `StageInstance` - The stage instance.
```

--------------------------------

### VoiceChannel.send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the voice channel. If content is None, an embed must be provided.

```APIDOC
## VoiceChannel.send

### Description
Sends a message to the destination with the content given. This is a coroutine.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload (max 10).
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload (max 10).
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of stickers to upload (max 3).
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the message to which you are replying.
- **mention_author** (Optional[bool]) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **Message** - The message that was sent.

### Raises
- **HTTPException** - Sending the message failed.
- **Forbidden** - You do not have the proper permissions.
- **NotFound** - The message with the same nonce was deleted.
- **ValueError** - Invalid size for files or embeds list.
- **TypeError** - Invalid combination of parameters or invalid reference object.
```

--------------------------------

### get_cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Gets the cog instance requested.

```APIDOC
## get_cog(name)

### Description
Gets the cog instance requested. If the cog is not found, None is returned.

### Parameters
- **name** (str) - Required - The name of the cog you are requesting.

### Returns
- **Optional[Cog]** - The cog that was requested.
```

--------------------------------

### history(limit, before, after, around, oldest_first)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator to retrieve the message history of a channel. Requires read_message_history permission.

```APIDOC
## history(limit, before, after, around, oldest_first)

### Description
Returns an asynchronous iterator that enables receiving the destination's message history.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to retrieve.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this date or message.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this date or message.
- **around** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this date or message.
- **oldest_first** (Optional[bool]) - Optional - If set to True, return messages in oldest->newest order.

### Raises
- **Forbidden** - You do not have permissions to get channel message history.
- **HTTPException** - The request to get message history failed.

### Yields
- **Message** - The message with the message data parsed.
```

--------------------------------

### Client Constructor

Source: https://discordpy.readthedocs.io/en/latest/api.html

The Client class constructor accepts various configuration parameters to manage connection settings, caching, intents, and gateway behavior.

```APIDOC
## Client Constructor

### Description
Initializes the discord.py Client with specific configuration for gateway connections, caching, and event handling.

### Parameters
- **max_messages** (int) - Optional - Maximum number of messages to store in the internal cache. Defaults to 1000.
- **proxy** (str) - Optional - Proxy URL.
- **proxy_auth** (aiohttp.BasicAuth) - Optional - Proxy HTTP Basic Authorization object.
- **shard_id** (int) - Optional - Integer ID for sharding.
- **shard_count** (int) - Optional - Total number of shards.
- **application_id** (int) - Required - The client's application ID.
- **intents** (Intents) - Required - The intents enabled for the session.
- **member_cache_flags** (MemberCacheFlags) - Optional - Control over member caching behavior.
- **chunk_guilds_at_startup** (bool) - Optional - Whether to chunk guilds at startup. Defaults to True if Intents.members is True.
- **status** (Status) - Optional - Initial presence status.
- **activity** (BaseActivity) - Optional - Initial presence activity.
- **allowed_mentions** (AllowedMentions) - Optional - Default mention handling.
- **heartbeat_timeout** (float) - Optional - Seconds before timing out the WebSocket. Defaults to 60.
- **guild_ready_timeout** (float) - Optional - Seconds to wait for GUILD_CREATE stream. Defaults to 2.
- **assume_unsync_clock** (bool) - Optional - Whether to assume the system clock is unsynced. Defaults to True.
- **enable_debug_events** (bool) - Optional - Whether to enable raw socket events. Defaults to False.
- **enable_raw_presences** (bool) - Optional - Whether to enable on_raw_presence_update events.
- **http_trace** (aiohttp.TraceConfig) - Optional - Trace configuration for HTTP requests.
- **max_ratelimit_timeout** (float) - Optional - Maximum seconds to wait for non-global rate limits.
- **connector** (aiohttp.BaseConnector) - Optional - aiohttp connector for underlying network control.
```

--------------------------------

### callback(interaction)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

The callback associated with the UI item, triggered when an interaction occurs.

```APIDOC
## await callback(interaction)

### Description
The callback associated with this UI item. This can be overridden by subclasses to handle the interaction.

### Parameters
- **interaction** (Interaction) - Required - The interaction that triggered this UI item.
```

--------------------------------

### Configure Bot Prefix with when_mentioned_or

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Sets the command prefix to allow mentions or a specific string.

```python
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"))
```

--------------------------------

### User.mentioned_in

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the user is mentioned in a specific message.

```APIDOC
## mentioned_in(message)

### Description
Checks if the user is mentioned in the specified message.

### Parameters
- **message** (Message) - Required - The message to check if you're mentioned in.

### Returns
- **bool** - Indicates if the user is mentioned in the message.
```

--------------------------------

### Use parameter() for late binding defaults

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates using commands.parameter with a lambda to dynamically set a default value based on the invocation context.

```python
@bot.command()
async def wave(ctx, to: discord.User = commands.parameter(default=lambda ctx: ctx.author)):
    await ctx.send(f"Hello {to.mention} :wave:")
```

--------------------------------

### Define a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

A basic cog implementation containing a listener and a command.

```python
class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(f"Welcome {member.mention}.")

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member = None):
        """Says hello"""
        member = member or ctx.author
        if self._last_member is None or self._last_member.id != member.id:
            await ctx.send(f"Hello {member.name}~")
        else:
            await ctx.send(f"Hello {member.name}... This feels familiar.")
        self._last_member = member
```

--------------------------------

### fetch_soundboard_sound()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a SoundboardSound with the specified ID.

```APIDOC
## fetch_soundboard_sound(sound_id)

### Description
Retrieves a `SoundboardSound` with the specified ID.

### Parameters
- **sound_id** (Any) - Required - The ID of the sound to retrieve.
```

--------------------------------

### delete(*, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the channel. Requires manage_channels permission.

```APIDOC
## delete(*, reason=None)

### Description
Deletes the channel. This function is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this channel. Shows up on the audit log.

### Raises
- **Forbidden** - You do not have proper permissions to delete the channel.
- **NotFound** - The channel was not found or was already deleted.
- **HTTPException** - Deleting the channel failed.
```

--------------------------------

### Cog.listener(name=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Decorator that marks a function as an event listener within the cog.

```APIDOC
## Cog.listener(name=None)

### Description
A decorator that marks a function as a listener. This is the cog equivalent of Bot.listen().

### Parameters
- **name** (str) - Optional - The name of the event being listened to. Defaults to the function's name.
```

--------------------------------

### create_forum

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a ForumChannel within the category.

```APIDOC
## await create_forum(name, **options)

### Description
A shortcut method to create a ForumChannel in the category.

### Parameters
- **name** (str) - Required - The name of the forum channel.
- **options** (dict) - Optional - Additional options for channel creation.

### Returns
- **ForumChannel** - The channel that was just created.
```

--------------------------------

### Webhook.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message via the webhook. Supports various parameters like content, embeds, files, and thread management.

```APIDOC
## Webhook.send

### Description
Sends a message to the webhook. If `wait` is set to `True`, it returns a `WebhookMessage` object; otherwise, it returns `None`.

### Parameters
- **content** (str) - Optional - The content of the message to send.
- **wait** (bool) - Optional - Whether the server should wait before sending a response.
- **username** (str) - Optional - The username to send with this message.
- **avatar_url** (str) - Optional - The avatar URL to send with this message.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **ephemeral** (bool) - Optional - Indicates if the message should only be visible to the user.
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to send.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to send.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - The view to send with the message.
- **thread** (Snowflake) - Optional - The thread to send this webhook to.
- **thread_name** (str) - Optional - The thread name to create if the webhook belongs to a ForumChannel.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **applied_tags** (List[ForumTag]) - Optional - Tags to apply to the thread.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **Optional[WebhookMessage]** - The message that was sent if wait is True, otherwise None.
```

--------------------------------

### Add reactions to a message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Demonstrates adding custom emojis to a message using IDs, lookups, or raw emoji strings.

```python
# if you have the ID already
emoji = client.get_emoji(310177266011340803)
await message.add_reaction(emoji)

# no ID, do a lookup
emoji = discord.utils.get(guild.emojis, name="LUL")
if emoji:
    await message.add_reaction(emoji)

# if you have the name and ID of a custom emoji:
emoji = "<:python3:232720527448342530>"
await message.add_reaction(emoji)
```

--------------------------------

### Guild.delete()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the guild. You must be the guild owner to perform this action.

```APIDOC
## await Guild.delete()

### Description
Deletes the guild. You must be the guild owner to delete the guild.

### Raises
- **HTTPException** - Deleting the guild failed.
- **Forbidden** - You do not have permissions to delete the guild.
```

--------------------------------

### Asset.replace()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a new asset with the specified components replaced.

```APIDOC
## replace(size=None, format=None, static_format=None)

### Description
Returns a new asset with the passed components replaced.

### Parameters
- **size** (int) - Optional - The new size of the asset.
- **format** (str) - Optional - The new format to change it to.
- **static_format** (str) - Optional - The new format to change it to if the asset isn't animated.

### Returns
- **Asset** - The newly updated asset.
```

--------------------------------

### Define Parameter Choices

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Provides selectable choices for command parameters using the choices decorator, typing.Literal, or enum.Enum.

```python
@app_commands.command()
@app_commands.describe(fruits="fruits to choose from")
@app_commands.choices(
    fruits=[
        Choice(name="apple", value=1),
        Choice(name="banana", value=2),
        Choice(name="cherry", value=3),
    ]
)
async def fruit(interaction: discord.Interaction, fruits: Choice[int]):
    await interaction.response.send_message(f"Your favourite fruit is {fruits.name}.")
```

```python
@app_commands.command()
@app_commands.describe(fruits="fruits to choose from")
async def fruit(interaction: discord.Interaction, fruits: Literal["apple", "banana", "cherry"]):
    await interaction.response.send_message(f"Your favourite fruit is {fruits}.")
```

```python
class Fruits(enum.Enum):
    apple = 1
    banana = 2
    cherry = 3


@app_commands.command()
@app_commands.describe(fruits="fruits to choose from")
async def fruit(interaction: discord.Interaction, fruits: Fruits):
    await interaction.response.send_message(f"Your favourite fruit is {fruits}.")
```

--------------------------------

### PartialEmoji.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the asset into a File object suitable for sending.

```APIDOC
## await PartialEmoji.to_file(*, filename=None, description=None, spoiler=False)

### Description
Converts the asset into a `File` suitable for sending via `abc.Messageable.send()`. This is a coroutine.

### Parameters
- **filename** (`Optional[str]`) - Optional - The filename of the file.
- **description** (`Optional[str]`) - Optional - The description for the file.
- **spoiler** (`bool`) - Optional - Whether the file is a spoiler.

### Returns
- `File` - The asset as a file suitable for sending.
```

--------------------------------

### StageChannel.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the StageChannel. This is a coroutine that supports text content, embeds, files, stickers, and UI views.

```APIDOC
## StageChannel.send

### Description
Sends a message to the destination with the content given. This function is a coroutine.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload (max 10).
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload (max 10).
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of stickers to upload (max 3).
- **delete_after** (float) - Optional - Number of seconds to wait before deleting the message.
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the message to which you are referencing.
- **mention_author** (Optional[bool]) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **Message** - The message that was sent.

### Raises
- **HTTPException** - Sending the message failed.
- **Forbidden** - You do not have the proper permissions.
- **NotFound** - Message with the same nonce was deleted.
- **ValueError** - Invalid size for files or embeds list.
- **TypeError** - Invalid parameters or reference object.
```

--------------------------------

### fetch_member(member_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific member from the guild by ID.

```APIDOC
## await fetch_member(member_id)

### Description
Retrieves a `Member` from a guild ID and a member ID.

### Parameters
- **member_id** (int) - Required - The member’s ID to fetch from.

### Returns
- **Member** - The member from the member ID.
```

--------------------------------

### discord.utils.find

Source: https://discordpy.readthedocs.io/en/latest/api.html

A helper to return the first element found in the sequence that meets the predicate.

```APIDOC
## discord.utils.find(predicate, iterable)

### Description
A helper to return the first element found in the sequence that meets the predicate. If an entry is not found, then None is returned.

### Parameters
- **predicate** (Callable) - Required - A function that returns a boolean-like result.
- **iterable** (Union[Iterable, AsyncIterable]) - Required - The iterable to search through.
```

--------------------------------

### PartialEmoji.from_str

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts a Discord string representation of an emoji to a PartialEmoji object.

```APIDOC
## PartialEmoji.from_str(value, *, client=None)

### Description
Converts a Discord string representation of an emoji to a `PartialEmoji`.

### Parameters
- **value** (`str`) - Required - The string representation of an emoji (e.g., 'a:name:id').
- **client** (`Client`) - Optional - The client to initialise this emoji with.

### Returns
- `PartialEmoji` - The partial emoji from this string.
```

--------------------------------

### AutoShardedClient.change_presence

Source: https://discordpy.readthedocs.io/en/latest/api.html

Changes the client's presence.

```APIDOC
## await change_presence(activity=None, status=None, shard_id=None)

### Description
Changes the client's presence. This is a coroutine.

### Parameters
- **activity** (Activity) - Optional - The activity to set.
- **status** (Status) - Optional - The status to set.
- **shard_id** (int) - Optional - The specific shard ID to change presence for.
```

--------------------------------

### Member.move_to

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves a member to a new voice channel.

```APIDOC
## Member.move_to(channel, reason=None)

### Description
Moves a member to a new voice channel. The member must be connected to a voice channel first.

### Parameters
- **channel** (Optional[Union[VoiceChannel, StageChannel]]) - Required - The new voice channel to move the member to.
- **reason** (Optional[str]) - Optional - The reason for doing this action.
```

--------------------------------

### defer(ephemeral=False, thinking=False)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Defers the interaction response. This is used when the interaction is acknowledged and a secondary action will be performed later.

```APIDOC
## defer(ephemeral=False, thinking=False)

### Description
Defers the interaction response. This is typically used when the interaction is acknowledged and a secondary action will be done later.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral.
- **thinking** (bool) - Optional - Indicates whether the deferred type should be deferred_channel_message instead of the default deferred_message_update.

### Returns
- **InteractionCallbackResponse** - The interaction callback resource, or None.
```

--------------------------------

### Define an Application Command Group

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Inherit from app_commands.Group to create a command group, applying decorators like guild_only() to the class.

```python
from discord import app_commands


@app_commands.guild_only()
class MyGroup(app_commands.Group):
    pass
```

--------------------------------

### play(source, *, after=None, application='audio', bitrate=128, fec=True, expected_packet_loss=0.15, bandwidth='full', signal_type='auto')

Source: https://discordpy.readthedocs.io/en/latest/api.html

Plays an AudioSource. The finalizer 'after' is called after the source has been exhausted or an error occurred.

```APIDOC
## play(source, *, after=None, application='audio', bitrate=128, fec=True, expected_packet_loss=0.15, bandwidth='full', signal_type='auto')

### Description
Plays an AudioSource. The finalizer, after is called after the source has been exhausted or an error occurred.

### Parameters
- **source** (AudioSource) - Required - The audio source we’re reading from.
- **after** (Callable[[Optional[Exception]], Any]) - Optional - The finalizer that is called after the stream is exhausted.
- **application** (str) - Optional - Configures the encoder’s intended application. Defaults to 'audio'.
- **bitrate** (int) - Optional - Configures the bitrate in the encoder. Defaults to 128.
- **fec** (bool) - Optional - Configures the encoder’s use of inband forward error correction. Defaults to True.
- **expected_packet_loss** (float) - Optional - Configures the encoder’s expected packet loss percentage. Defaults to 0.15.
- **bandwidth** (str) - Optional - Configures the encoder’s bandpass. Defaults to 'full'.
- **signal_type** (str) - Optional - Configures the type of signal being encoded. Defaults to 'auto'.
```

--------------------------------

### GuildSticker.delete()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a custom sticker from the guild.

```APIDOC
## await GuildSticker.delete(reason=None)

### Description
Deletes the custom Sticker from the guild. Requires manage_emojis_and_stickers permission.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this sticker. Shows up on the audit log.

### Raises
- **Forbidden** - You are not allowed to delete stickers.
- **HTTPException** - An error occurred deleting the sticker.
```

--------------------------------

### login(token)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Logs in the client with the specified credentials.

```APIDOC
## login(token)

### Description
Logs in the client with the specified credentials and calls the setup_hook().

### Parameters
- **token** (str) - Required - The authentication token.
```

--------------------------------

### Member.mentioned_in

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the member is mentioned in a specific message.

```APIDOC
## Member.mentioned_in(message)

### Description
Checks if the member is mentioned in the specified message.

### Parameters
- **message** (Message) - Required - The message to check if you are mentioned in.

### Response
- **bool** - Indicates if the member is mentioned in the message.
```

--------------------------------

### remove_user

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a user from the thread.

```APIDOC
## remove_user(user)

### Description
Removes a user from this thread. Requires manage_threads or thread ownership.

### Parameters
- **user** (abc.Snowflake) - Required - The user to remove from the thread.

### Raises
- **Forbidden** - You do not have permissions to remove the user.
- **HTTPException** - Removing the user failed.
```

--------------------------------

### discord.app_commands.ContextMenu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A class that implements a context menu application command. These are typically created using the context_menu() decorator.

```APIDOC
## class discord.app_commands.ContextMenu(name, callback, type=..., nsfw=False, guild_ids=None, allowed_contexts=None, allowed_installs=None, auto_locale_strings=True, extras=...)

### Description
A class that implements a context menu application command. These are usually not created manually, instead they are created using one of the following decorators: `context_menu()` or `CommandTree.context_menu`.

### Parameters
- **name** (Union[str, locale_str]) - Required - The name of the context menu.
- **callback** (coroutine) - Required - The coroutine that is executed when the command is called.
- **type** (AppCommandType) - Optional - The type of context menu application command.
- **auto_locale_strings** (bool) - Optional - If True, translatable strings will implicitly be wrapped into locale_str. Defaults to True.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **extras** (dict) - Optional - A dictionary that can be used to store extraneous data.

### Methods
- **add_check(func)**: Adds a check to the command.
- **remove_check(func)**: Removes a check from the command.
- **@error(coro)**: A decorator that registers a coroutine as a local error handler.
```

--------------------------------

### Update command message sending

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Replaces the deprecated bot.say with the Context.send method.

```python
# before
@bot.command()
async def foo():
    await bot.say("Hello")


# after
@bot.command()
async def foo(ctx):
    await ctx.send("Hello")
```

--------------------------------

### fetch_invite

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Gets an Invite from a discord.gg URL or ID.

```APIDOC
## fetch_invite(url, with_counts=True, with_expiration=True, scheduled_event_id=None)

### Description
Gets an Invite from a discord.gg URL or ID.

### Parameters
- **url** (Union[Invite, str]) - Required - The Discord invite ID or URL.
- **with_counts** (bool) - Optional - Whether to include count information in the invite.
- **with_expiration** (bool) - Optional - Whether to include the expiration date of the invite.
- **scheduled_event_id** (Optional[int]) - Optional - The ID of the scheduled event this invite is for.

### Returns
- **Invite** - The invite from the URL/ID.
```

--------------------------------

### @command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that creates an application command from a regular function under this group.

```APIDOC
## @command(name=..., description=..., nsfw=False, auto_locale_strings=True, extras=...)

### Description
A decorator that creates an application command from a regular function under this group.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the application command.
- **description** (Union[str, locale_str]) - Optional - The description of the application command.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **auto_locale_strings** (bool) - Optional - Whether to implicitly wrap translatable strings into locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary to store extraneous data.
```

--------------------------------

### discord.on_poll_vote_add(user, answer)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a poll gains a vote. Requires Intents.message_content and Intents.polls to be enabled.

```APIDOC
## discord.on_poll_vote_add(user, answer)

### Description
Called when a Poll gains a vote. If the user or answer's poll parent message are not cached, this event will not be called.

### Parameters
- **user** (Union[User, Member]) - Required - The user that performed the action.
- **answer** (PollAnswer) - Required - The answer the user voted for.
```

--------------------------------

### get_max_size(commands, /)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Calculates the maximum name length of a provided list of commands.

```APIDOC
## get_max_size(commands, /)

### Description
Returns the largest name length of the specified command list.

### Parameters
- **commands** (Sequence[Command]) - Required - A sequence of commands to check for the largest size.

### Returns
- **int** - The maximum width of the commands.
```

--------------------------------

### discord.ui.FileUpload

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a file upload component within a modal.

```APIDOC
## class discord.ui.FileUpload(custom_id=..., required=True, min_values=None, max_values=None, id=None)

### Description
Represents a file upload component within a modal. New in version 2.7.

### Parameters
- **id** (Optional[int]) - Optional - The ID of the component. This must be unique across the view.
- **custom_id** (Optional[str]) - Optional - The custom ID of the file upload component.
- **max_values** (Optional[int]) - Optional - The maximum number of files that can be uploaded in this component. Must be between 1 and 10. Defaults to 1.
- **min_values** (Optional[int]) - Optional - The minimum number of files that must be uploaded in this component. Must be between 0 and 10. Defaults to 0.
- **required** (bool) - Required - Whether this component is required to be filled before submitting the modal. Defaults to True.
```

--------------------------------

### edit(content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the webhook message with new content, embeds, attachments, or view components.

```APIDOC
## edit(content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None)

### Description
Edits the message content, embeds, attachments, or view components. Note that `embed` and `embeds` should not be mixed.

### Parameters
- **content** (str) - Optional - The content to edit the message with or None to clear it.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Embed) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (View) - Optional - The updated view to update this message with.

### Returns
- **WebhookMessage** - The newly edited message.
```

--------------------------------

### Define case-insensitive settings flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Enables case-insensitive parsing for flag names.

```python
class Settings(commands.FlagConverter, case_insensitive=True):
    topic: Optional[str]
    nsfw: Optional[bool]
    slowmode: Optional[int]
```

--------------------------------

### get_emoji(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a custom emoji from the cache by its ID.

```APIDOC
## get_emoji(id)

### Description
Returns an emoji with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Emoji** (Optional) - The custom emoji or None if not found.
```

--------------------------------

### create_role(**fields)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new role for the guild with optional configuration.

```APIDOC
## create_role(**fields)

### Description
Creates a `Role` for the guild. Requires `manage_roles` permission.

### Parameters
- **name** (`str`) - Optional - The role name.
- **permissions** (`Permissions`) - Optional - The permissions to have.
- **colour** (`Union[Colour, int]`) - Optional - The colour for the role.
- **hoist** (`bool`) - Optional - Indicates if the role should be shown separately in the member list.
- **display_icon** (`Union[bytes, str]`) - Optional - Icon for the role.
- **mentionable** (`bool`) - Optional - Indicates if the role should be mentionable.
- **reason** (`str`) - Optional - The reason for creating this role.

### Returns
- `Role` - The newly created role.
```

--------------------------------

### ForumChannel.get_tag

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific tag associated with the forum by its ID.

```APIDOC
## get_tag(tag_id)

### Description
Returns the tag with the given ID.

### Parameters
- **tag_id** (int) - Required - The ID to search for.

### Returns
- **Optional[ForumTag]** - The tag with the given ID, or None if not found.
```

--------------------------------

### Registering an event listener

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use the @client.event decorator to register a coroutine that triggers when a specific event occurs.

```python
@client.event
async def on_ready():
    print("Ready!")
```

--------------------------------

### get_role(role_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a role with the given ID.

```APIDOC
## get_role(role_id)

### Description
Returns a role with the given ID.

### Parameters
- **role_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Role]** - The role or `None` if not found.
```

--------------------------------

### discord.ui.TextInput

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI text input component used within a view.

```APIDOC
## class discord.ui.TextInput

### Description
Represents a UI text input component. This is a top-level layout component.

### Constructor Parameters
- **label** (Optional[str]) - Optional - The label to display above the text input (Deprecated since 2.6).
- **custom_id** (str) - Optional - The ID of the text input received during an interaction.
- **style** (discord.TextStyle) - Optional - The style of the text input.
- **placeholder** (Optional[str]) - Optional - The placeholder text to display when empty.
- **default** (Optional[str]) - Optional - The default value of the text input.
- **required** (bool) - Optional - Whether the text input is required.
- **min_length** (Optional[int]) - Optional - The minimum length of the text input.
- **max_length** (Optional[int]) - Optional - The maximum length of the text input.
- **row** (Optional[int]) - Optional - The relative row this text input belongs to.
- **id** (Optional[int]) - Optional - The unique ID of the component (New in 2.6).
```

--------------------------------

### Bot.unload_extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Unloads an extension, removing all commands, listeners, and cogs associated with it.

```APIDOC
## Bot.unload_extension(name, *, package=None)

### Description
Unloads an extension. When the extension is unloaded, all commands, listeners, and cogs are removed from the bot and the module is un-imported.

### Parameters
- **name** (str) - Required - The extension name to unload.
- **package** (Optional[str]) - Optional - The package name to resolve relative imports with.
```

--------------------------------

### delete(delay=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the webhook message.

```APIDOC
## delete(delay=None)

### Description
Deletes the message. This is a coroutine.

### Parameters
- **delay** (float) - Optional - Number of seconds to wait before deleting.
```

--------------------------------

### @discord.app_commands.rename

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Renames parameters in the Discord UI while keeping the original function parameter name for decorators.

```APIDOC
## @discord.app_commands.rename

### Description
Renames the given parameters by their name using the key of the keyword argument as the name.

### Parameters
- **parameters** (Union[str, locale_str]) - Required - The name of the parameters.
```

--------------------------------

### discord.ext.commands.parameter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Assigns custom metadata for a command's parameter, allowing for custom converters, default values, and display names.

```APIDOC
## discord.ext.commands.parameter

### Description
A function used to assign custom metadata for a Command's parameter.

### Parameters
- **converter** (Any) - Optional - The converter to use for this parameter.
- **default** (Any) - Optional - The default value for the parameter. If callable or coroutine, it is called with a positional Context argument.
- **description** (str) - Optional - The description of this parameter.
- **displayed_default** (str) - Optional - The displayed default in Command.signature.
- **displayed_name** (str) - Optional - The name that is displayed to the user.
```

--------------------------------

### SyncWebhook.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the webhook.

```APIDOC
## SyncWebhook.delete(*, reason=None, prefer_auth=True)

### Description
Deletes this webhook from Discord.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this webhook, which appears in the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### Updating VoiceClient audio source and volume

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use PCMVolumeTransformer to dynamically adjust the volume of an active voice source.

```python
vc.source = discord.PCMVolumeTransformer(vc.source)
vc.source.volume = 0.6
```

--------------------------------

### Custom Function Converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates using a custom function as a converter via type annotations to transform input strings.

```python
def to_upper(argument):
    return argument.upper()


@bot.command()
async def up(ctx, *, content: to_upper):
    await ctx.send(content)
```

--------------------------------

### end_poll()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Ends the poll attached to the message. Only the message author can perform this action.

```APIDOC
## end_poll()

### Description
Ends the Poll attached to this message.

### Returns
- **Message** - The updated message.
```

--------------------------------

### Onboarding.get_prompt()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific onboarding prompt by its ID.

```APIDOC
## Onboarding.get_prompt(prompt_id)

### Description
Retrieves the prompt with the given ID, if found.

### Parameters
- **prompt_id** (int) - Required - The ID of the prompt to retrieve.

### Returns
- **Optional[OnboardingPrompt]** - The prompt with the given ID, if found.
```

--------------------------------

### get_command(name)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a command or subcommand by its name.

```APIDOC
## get_command(name)

### Description
Get a `Command` from the internal list of commands. The name could be fully qualified (e.g. 'foo bar') to get the subcommand 'bar' of the group command 'foo'.

### Parameters
- **name** (`str`) - Required - The name of the command to get.

### Returns
- **Command** (Optional) - The command that was requested. If not found, returns `None`.
```

--------------------------------

### Update Converter Metaclass

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates custom converter metaclasses to inherit from the base converter type due to the transition to runtime-checkable protocols.

```python
# before
class SomeConverterMeta(type): ...


class SomeConverter(commands.Converter, metaclass=SomeConverterMeta): ...


# after
class SomeConverterMeta(type(commands.Converter)): ...


class SomeConverter(commands.Converter, metaclass=SomeConverterMeta): ...
```

--------------------------------

### get_user(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a user from the cache by its ID.

```APIDOC
## get_user(id)

### Description
Returns a user with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **User** (Optional) - The user or None if not found.
```

--------------------------------

### Search for a message using discord.utils.get

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a message from a channel history matching the specified author name.

```python
msg = await discord.utils.get(channel.history(), author__name="Dave")
```

--------------------------------

### discord.on_raw_message_edit(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is edited, regardless of the internal message cache state. Requires Intents.messages to be enabled.

```APIDOC
## discord.on_raw_message_edit(payload)

### Description
Called when a message is edited. This is called regardless of the state of the internal message cache.

### Parameters
- **payload** (RawMessageUpdateEvent) - Required - The raw event payload data.
```

--------------------------------

### create_voice_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new voice channel in the guild. This is a coroutine.

```APIDOC
## create_voice_channel(name, *, reason=None, category=None, position=..., bitrate=..., user_limit=..., rtc_region=..., video_quality_mode=..., overwrites=..., nsfw=...)

### Description
Creates a new voice channel in the guild.

### Parameters
- **name** (str) - Required - The channel’s name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply upon creation.
- **category** (Optional[CategoryChannel]) - Optional - The category to place the channel under.
- **position** (int) - Optional - The position in the channel list.
- **bitrate** (int) - Optional - The channel’s preferred audio bitrate.
- **user_limit** (int) - Optional - The channel’s limit for number of members.
- **rtc_region** (Optional[str]) - Optional - The region for the voice channel’s communication.
- **video_quality_mode** (VideoQualityMode) - Optional - The camera video quality.
- **nsfw** (bool) - Optional - Mark the channel as NSFW.
- **reason** (Optional[str]) - Optional - The reason for creating this channel.

### Returns
- **VoiceChannel** - The channel that was just created.
```

--------------------------------

### fetch_user

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a User based on their ID.

```APIDOC
## await fetch_user(user_id)

### Description
Retrieves a User based on their ID. This method is an API call.

### Parameters
- **user_id** (int) - Required - The user’s ID to fetch from.

### Returns
- **User** - The user you requested.

### Raises
- **NotFound** - A user with this ID does not exist.
- **HTTPException** - Fetching the user failed.
```

--------------------------------

### Integration.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a guild integration. Requires the manage_guild permission.

```APIDOC
## await Integration.delete(reason=None)

### Description
Deletes the integration. You must have `manage_guild` to do this.

### Parameters
- **reason** (str) - Optional - The reason the integration was deleted. Shows up on the audit log.
```

--------------------------------

### Use Greedy converters for multiple arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Greedy attempts to convert as many arguments as possible until it can no longer convert them.

```python
@bot.command()
async def slap(ctx, members: commands.Greedy[discord.Member], *, reason="no reason"):
    slapped = ", ".join(x.name for x in members)
    await ctx.send(f"{slapped} just got slapped for {reason}")
```

--------------------------------

### Client.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Establishes a websocket connection to Discord and starts the event loop.

```APIDOC
## connect(*, reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord. This is a loop that runs the entire event system. Control is not resumed until the WebSocket connection is terminated.
```

--------------------------------

### StreamIntegration.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a stream integration.

```APIDOC
## await StreamIntegration.edit(**kwargs)

### Description
Edits the stream integration.
```

--------------------------------

### fetch_channel

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a channel by its ID.

```APIDOC
## await fetch_channel(channel_id)

### Description
Retrieves a `abc.GuildChannel`, `abc.PrivateChannel`, or `Thread` with the specified ID.

### Parameters
- **channel_id** (int) - Required - The ID of the channel to fetch.

### Raises
- **InvalidData** - An unknown channel type was received.
- **HTTPException** - Retrieving the channel failed.
- **NotFound** - Invalid Channel ID.
- **Forbidden** - Permission denied.

### Returns
- **Union[abc.GuildChannel, abc.PrivateChannel, Thread]** - The channel from the ID.
```

--------------------------------

### get_partial_messageable(id, *, guild_id=None, type=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a partial messageable object for a given channel ID without performing an API call.

```APIDOC
## get_partial_messageable(id, *, guild_id=None, type=None)

### Description
Returns a partial messageable with the given channel ID. This is useful if you have a channel_id but don't want to do an API call to send messages to it.

### Parameters
- **id** (int) - Required - The channel ID.
- **guild_id** (int) - Optional - The guild ID.
- **type** (Any) - Optional - The type of the messageable.
```

--------------------------------

### Retrieve file attachments with discord.Attachment

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

The Attachment converter retrieves files uploaded with the message. It can be combined with Optional to make the attachment non-mandatory.

```python
import discord


@bot.command()
async def upload(ctx, attachment: discord.Attachment):
    await ctx.send(f"You have uploaded <{attachment.url}>")
```

```python
import typing
import discord
```

--------------------------------

### Updating on_voice_state_update signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now accepts a Member object followed by before and after VoiceState objects.

```python
async def on_voice_state_update(before, after)
```

```python
async def on_voice_state_update(member, before, after)
```

--------------------------------

### Retrieving a single element from history

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Find a specific message in history using the get method.

```python
my_last_message = await channel.history().get(author=client.user)
```

--------------------------------

### ui.Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a container component that can hold multiple items. Provides methods to manipulate the collection of children.

```APIDOC
## ui.Container

### Description
A container component that holds children items. It supports adding, removing, and finding items, as well as recursive iteration.

### Methods
- **add_item(item)**: Adds an item to the container. Returns the instance for chaining.
- **remove_item(item)**: Removes an item from the container. Returns the instance for chaining.
- **find_item(id)**: Finds an item by its ID.
- **clear_items()**: Removes all items from the container.
- **content_length()**: Returns the total length of all text content.
- **interaction_check(interaction)**: Coroutine to check if an interaction should be processed.

### Properties
- **id** (int): The unique ID of the component.
- **children** (List[Item]): The list of children items.
- **accent_colour** (Optional[Union[Colour, int]]): The colour of the container.
- **spoiler** (bool): Whether the container is a spoiler.
```

--------------------------------

### forward()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Forwards the message to a specified channel.

```APIDOC
## await forward(destination, fail_if_not_exists=True)

### Description
Forwards this message to a channel.

### Parameters
- **destination** (`Messageable`) - Required - The channel to forward this message to.
- **fail_if_not_exists** (`bool`) - Optional - Whether to raise an error if the message no longer exists.

### Returns
- **Message** - The message sent to the channel.
```

--------------------------------

### remove_check(func)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes a check function from the command.

```APIDOC
## remove_check(func)

### Description
Removes a check from the command. This function is idempotent and will not raise an exception if the function is not present.

### Parameters
- **func** (function) - Required - The function to remove from the checks.
```

--------------------------------

### Implement an advanced converter class

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a separate converter class inheriting from MemberConverter to transform member data into a custom object.

```python
class JoinDistance:
    def __init__(self, joined, created):
        self.joined = joined
        self.created = created

    @property
    def delta(self):
        return self.joined - self.created


class JoinDistanceConverter(commands.MemberConverter):
    async def convert(self, ctx, argument):
        member = await super().convert(ctx, argument)
        return JoinDistance(member.joined_at, member.created_at)


@bot.command()
async def delta(ctx, *, member: JoinDistanceConverter):
    is_new = member.delta.days < 100
    if is_new:
        await ctx.send("Hey you're pretty new!")
    else:
        await ctx.send("Hm you're not so new.")
```

--------------------------------

### Configure Guild Installation

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Apply guild_install to make a command available for installation in guilds. This decorator does not function on subcommands.

```python
@app_commands.command()
@app_commands.guild_install()
async def my_guild_install_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in guilds by default!")
```

--------------------------------

### discord.on_raw_bulk_message_delete(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a bulk delete is triggered, regardless of the internal message cache state. Requires Intents.messages to be enabled.

```APIDOC
## discord.on_raw_bulk_message_delete(payload)

### Description
Called when a bulk delete is triggered. Unlike on_bulk_message_delete(), this is called regardless of the messages being in the internal message cache or not.

### Parameters
- **payload** (RawBulkMessageDeleteEvent) - Required - The raw event payload data.
```

--------------------------------

### Accessing Voice State Attributes

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Access voice attributes through the Member.voice attribute, checking for None to avoid errors.

```python
# before
member.deaf
member.voice.voice_channel

# after
if member.voice:  # can be None
    member.voice.deaf
    member.voice.channel
```

--------------------------------

### AutoModRule.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the auto moderation rule. Requires manage_guild permissions.

```APIDOC
## delete(reason=...)

### Description
Deletes the auto moderation rule. You must have `Permissions.manage_guild` to delete rules.

### Parameters
- **reason** (`str`) - Optional - The reason for deleting this rule.
```

--------------------------------

### MemberCacheFlags.none()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance with all flags disabled.

```APIDOC
## MemberCacheFlags.none()

### Description
A factory method that creates a MemberCacheFlags instance with everything disabled.

### Returns
- **MemberCacheFlags** - The resulting member cache flags object.
```

--------------------------------

### StageChannel.purge

Source: https://discordpy.readthedocs.io/en/latest/api.html

Purges a list of messages that meet the criteria given by the predicate check. Requires manage_messages and read_message_history permissions.

```APIDOC
## purge(limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

### Description
Purges a list of messages that meet the criteria given by the predicate check. If a check is not provided then all messages are deleted.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to search through.
- **check** (Callable[[Message], bool]) - Optional - The function used to check if a message should be deleted.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this time or snowflake.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this time or snowflake.
- **around** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this time or snowflake.
- **oldest_first** (Optional[bool]) - Optional - If set to True, return messages in oldest to newest order.
- **bulk** (bool) - Optional - If True, use bulk delete. Defaults to True.
- **reason** (Optional[str]) - Optional - The reason for purging the messages for the audit log.

### Returns
- **List[Message]** - The list of messages that were deleted.
```

--------------------------------

### Use and configure built-in converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows usage of the clean_content converter with and without custom configuration parameters.

```python
@bot.command()
async def clean(ctx, *, content: commands.clean_content):
    await ctx.send(content)


# or for fine-tuning


@bot.command()
async def clean(ctx, *, content: commands.clean_content(use_nicknames=False)):
    await ctx.send(content)
```

--------------------------------

### discord.app_commands.checks.dynamic_cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a dynamic cooldown to a command based on a factory function.

```APIDOC
## @discord.app_commands.checks.dynamic_cooldown(factory, *, key=...)

### Description
Applies a cooldown determined by a factory function that returns a Cooldown object or None.

### Parameters
- **factory** (Callable) - Required - Function returning a Cooldown or None.
- **key** (Callable) - Optional - Function returning a key for the cooldown mapping.
```

--------------------------------

### Webhook.fetch_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single WebhookMessage owned by the webhook.

```APIDOC
## Webhook.fetch_message

### Description
Retrieves a single `WebhookMessage` owned by this webhook.

### Parameters
- **id** (int) - Required - The message ID to look for.
- **thread** (Snowflake) - Optional - The thread to look in.

### Returns
- **WebhookMessage** - The message asked for.
```

--------------------------------

### Access original message in context

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Retrieve the original message object via the message attribute of the command context.

```python
@bot.command()
async def length(ctx):
    await ctx.send(f"Your message is {len(ctx.message.content)} characters long.")
```

--------------------------------

### fetch_voice()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the current voice state from this member.

```APIDOC
## fetch_voice()

### Description
Retrieves the current voice state from this member.

### Returns
- **VoiceState** - The current voice state of the member.
```

--------------------------------

### purge

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes messages from the channel based on provided criteria.

```APIDOC
## purge(limit, check, before, after, around, oldest_first, bulk, reason)

### Description
Deletes messages that match the specified criteria. This is a coroutine.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to search through.
- **check** (Callable[[Message], bool]) - Required - The function used to check if a message should be deleted.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Search messages before this ID or time.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Search messages after this ID or time.
- **around** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Search messages around this ID or time.
- **oldest_first** (Optional[bool]) - Optional - Whether to search oldest messages first.
- **bulk** (bool) - Required - If True, use bulk delete.
- **reason** (Optional[str]) - Optional - The reason for purging the messages.

### Returns
- List[Message] - The list of messages that were deleted.
```

--------------------------------

### load_extension(name, package=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Loads an extension (a python module containing commands, cogs, or listeners).

```APIDOC
## load_extension(name, package=None)

### Description
Loads an extension. An extension is a python module that contains commands, cogs, or listeners. An extension must have a global function, setup defined as the entry point.

### Parameters
- **name** (str) - Required - The extension name to load.
- **package** (Optional[str]) - Optional - The package name to resolve relative imports with.
```

--------------------------------

### clear_reaction(emoji)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears a specific reaction from the message.

```APIDOC
## clear_reaction(emoji)

### Description
Clears a specific reaction from the message. This is a coroutine.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to clear.
```

--------------------------------

### edit_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by editing the original message of a component or modal interaction.

```APIDOC
## edit_message(content=..., embed=..., embeds=..., attachments=..., view=..., allowed_mentions=..., delete_after=None, suppress_embeds=...)

### Description
Responds to this interaction by editing the original message of a component or modal interaction.

### Parameters
- **content** (Optional[str]) - Optional - The new content to replace the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **view** (Optional[Union[View, LayoutView]]) - Optional - The updated view to update this message with.
- **allowed_mentions** (Optional[AllowedMentions]) - Optional - Controls the mentions being processed in this message.
- **delete_after** (float) - Optional - Number of seconds to wait before deleting the message.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.

### Returns
- **InteractionCallbackResponse** - The interaction callback data, or None if editing was not possible.
```

--------------------------------

### add_reaction(emoji)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a reaction to the message.

```APIDOC
## add_reaction(emoji)

### Description
Adds a reaction to the message. The emoji may be a unicode emoji or a custom guild Emoji. This is a coroutine.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to react with.
```

--------------------------------

### discord.app_commands.checks.cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a fixed cooldown to a command, limiting usage frequency.

```APIDOC
## @discord.app_commands.checks.cooldown(rate, per, *, key=...)

### Description
Limits the number of times a command can be used within a specific time frame.

### Parameters
- **rate** (int) - Required - Number of uses allowed.
- **per** (float) - Required - Time frame in seconds.
- **key** (Callable) - Optional - Function returning a key for the cooldown mapping.
```

--------------------------------

### discord.Attachment.read

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the attachment as a bytes object.

```APIDOC
## await discord.Attachment.read(*, use_cached=False)

### Description
Retrieves the content of this attachment as a bytes object. This is a coroutine.

### Parameters
- **use_cached** (bool) - Optional - Whether to use proxy_url rather than url when downloading the attachment.

### Returns
- **bytes** - The contents of the attachment.

### Raises
- **HTTPException** - Downloading the attachment failed.
- **Forbidden** - You do not have permissions to access this attachment.
- **NotFound** - The attachment was deleted.
```

--------------------------------

### discord.ui.button

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a button to a component. The decorated function should accept self, interaction, and the button instance.

```APIDOC
## @discord.ui.button(label=None, custom_id=None, disabled=False, style=ButtonStyle.secondary, emoji=None, row=None, id=None)

### Description
A decorator that attaches a button to a component. Note that buttons with a URL or an SKU cannot be created with this function.

### Parameters
- **label** (Optional[str]) - The label of the button.
- **custom_id** (Optional[str]) - The ID of the button received during an interaction.
- **disabled** (bool) - Whether the button is disabled.
- **style** (discord.ButtonStyle) - The style of the button.
- **emoji** (Optional[Union[PartialEmoji, Emoji, str]]) - The emoji of the button.
- **row** (Optional[int]) - The relative row this button belongs to (0-4).
- **id** (Optional[int]) - The unique ID of this component.
```

--------------------------------

### AppCommand.edit

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the application command with new attributes.

```APIDOC
## await edit(*, name=..., description=..., default_member_permissions=..., dm_permission=..., options=...)

### Description
Edits the application command.

### Parameters
- **name** (str) - Optional - The new name for the application command.
- **description** (str) - Optional - The new description for the application command.
- **default_member_permissions** (Optional[Permissions]) - Optional - The new default permissions needed to use this application command.
- **dm_permission** (bool) - Optional - Indicates if the application command can be used in DMs.
- **options** (List[Union[Argument, AppCommandGroup]]) - Optional - List of new options for this application command.

### Returns
- **AppCommand** - The newly edited application command.
```

--------------------------------

### Define a Hybrid Command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the hybrid_command decorator to create a command that can be invoked via text or slash interaction.

```python
@bot.hybrid_command()
async def test(ctx):
    await ctx.send("This is a hybrid command!")
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the message.

```APIDOC
## await delete(delay=None)

### Description
Deletes the message, optionally after a delay.

### Parameters
- **delay** (Optional[float]) - Optional - Seconds to wait before deleting.
```

--------------------------------

### PollAnswer.voters

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of users who have voted on a specific poll answer.

```APIDOC
## async PollAnswer.voters(limit=None, after=None)

### Description
Returns an asynchronous iterator representing the users that have voted on this answer. This can only be called when the parent poll was sent to a message.

### Parameters
- **limit** (Optional[int]) - Optional - The maximum number of results to return. If not provided, returns all the users who voted on this poll answer.
- **after** (Optional[abc.Snowflake]) - Optional - For pagination, voters are sorted by member.

### Yields
- Union[User, Member] - The member (if retrievable) or the user that has voted on this poll answer.

### Raises
- **HTTPException** - Retrieving the users failed.
```

--------------------------------

### @command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator used to create an application command from a function within a CommandTree.

```APIDOC
## @command(*, name=..., description=..., nsfw=False, guild=..., guilds=..., auto_locale_strings=True, extras=...)

### Description
A decorator that creates an application command from a regular function directly under a CommandTree.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the application command. Defaults to the lower-case callback name.
- **description** (Union[str, locale_str]) - Optional - The description of the application command. Defaults to the first line of the callback's docstring.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **guild** (Optional[Snowflake]) - Optional - The guild to add the command to. If None, it becomes a global command.
- **guilds** (List[Snowflake]) - Optional - A list of guilds to add the command to.
- **auto_locale_strings** (bool) - Optional - If True, translatable strings are wrapped in locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary for storing extraneous data.
```

--------------------------------

### create_stage_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new stage channel in the guild. This is a coroutine.

```APIDOC
## create_stage_channel(name, *, reason=None, category=None, position=..., bitrate=..., user_limit=..., rtc_region=..., video_quality_mode=..., overwrites=..., nsfw=...)

### Description
Creates a new stage channel in the guild.

### Parameters
- **name** (str) - Required - The channel’s name.
- **reason** (Optional[str]) - Optional - The reason for creating this channel.
- **category** (Optional[CategoryChannel]) - Optional - The category to place the channel under.
- **position** (int) - Optional - The position in the channel list.
- **bitrate** (int) - Optional - The channel’s preferred audio bitrate.
- **user_limit** (int) - Optional - The channel’s limit for number of members.
- **rtc_region** (Optional[str]) - Optional - The region for the voice channel’s communication.
- **video_quality_mode** (VideoQualityMode) - Optional - The camera video quality.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply upon creation.
- **nsfw** (bool) - Optional - Mark the channel as NSFW.
```

--------------------------------

### Define a Cog with special methods

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Example of a custom Cog class implementing various special methods for checks, error handling, and invocation hooks, along with a listener.

```python
class MyCog(commands.Cog, name="Example Cog"):
    def cog_unload(self):
        print("cleanup goes here")

    def bot_check(self, ctx):
        print("bot check")
        return True

    def bot_check_once(self, ctx):
        print("bot check once")
        return True

    async def cog_check(self, ctx):
        print("cog local check")
        return await ctx.bot.is_owner(ctx.author)

    async def cog_command_error(self, ctx, error):
        print("Error in {0.command.qualified_name}: {1}".format(ctx, error))

    async def cog_before_invoke(self, ctx):
        print("cog local before: {0.command.qualified_name}".format(ctx))

    async def cog_after_invoke(self, ctx):
        print("cog local after: {0.command.qualified_name}".format(ctx))

    @commands.Cog.listener()
    async def on_message(self, message):
        pass
```

--------------------------------

### Member.create_dm()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a DMChannel with the member. This is typically handled transparently by the library.

```APIDOC
## await Member.create_dm()

### Description
Creates a `DMChannel` with this user. This should be rarely called, as this is done transparently for most people.

### Returns
- **DMChannel** - The channel that was created.
```

--------------------------------

### discord.on_reaction_add(reaction, user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Triggered when a reaction is added to a message. Requires the message to be in the internal cache.

```APIDOC
## discord.on_reaction_add(reaction, user)

### Description
Called when a message has a reaction added to it. If the message is not found in the internal message cache, this event will not be triggered.

### Parameters
- **reaction** (Reaction) - The current state of the reaction.
- **user** (Union[Member, User]) - The user who added the reaction.
```

--------------------------------

### Probe Audio Source with FFmpeg

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use the fallback method when ffprobe is unavailable on Windows systems.

```python
source = await discord.FFmpegOpusAudio.from_probe("song.webm", method="fallback")
voice_client.play(source)
```

--------------------------------

### clear_reactions()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes all reactions from the message.

```APIDOC
## clear_reactions()

### Description
Removes all the reactions from the message. Requires manage_messages permission.

### Raises
- **HTTPException** - Removing the reactions failed.
- **Forbidden** - You do not have the proper permissions to remove all the reactions.
```

--------------------------------

### PermissionOverwrite.pair

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the (allow, deny) pair from this overwrite.

```APIDOC
## pair()

### Description
Returns the (allow, deny) pair from this overwrite.

### Returns
- **Tuple[Permissions, Permissions]** - The (allow, deny) pair.
```

--------------------------------

### Use typing.Union for multiple converter types

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Allows a parameter to accept multiple types by attempting conversions from left to right.

```python
import typing


@bot.command()
async def union(ctx, what: typing.Union[discord.TextChannel, discord.Member]):
    await ctx.send(what)
```

--------------------------------

### Define a command with a Range parameter

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the Range annotation to restrict numeric input within specific bounds.

```python
@app_commands.command()
async def range(interaction: discord.Interaction, value: app_commands.Range[int, 10, 12]):
    await interaction.response.send_message(f"Your value is {value}", ephemeral=True)
```

--------------------------------

### add_command(command)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a Command object to the internal list of commands. It is recommended to use the @command or @group decorators instead of calling this directly.

```APIDOC
## add_command(command)

### Description
Adds a `Command` into the internal list of commands. This is usually not called, instead the `command()` or `group()` shortcut decorators are used instead.

### Parameters
- **command** (`Command`) - Required - The command to add.

### Raises
- **CommandRegistrationError** - If the command or its alias is already registered by different command.
- **TypeError** - If the command passed is not a subclass of `Command`.
```

--------------------------------

### Restrict Command Contexts

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use allowed_contexts to restrict command usage to specific environments like guilds or DMs. This decorator is ignored when applied to subcommands.

```python
@app_commands.command()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def my_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am only available in guilds and private channels!")
```

--------------------------------

### clone(name=None, category=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the current channel, creating a new channel with the same properties.

```APIDOC
## clone(name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. You must have `manage_channels` to do this.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel. If not provided, defaults to this channel name.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to. This parameter is ignored if cloning a category channel.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel. Shows up on the audit log.

### Returns
- **abc.GuildChannel** - The channel that was created.

### Raises
- **Forbidden** - You do not have the proper permissions to create this channel.
- **HTTPException** - Creating the channel failed.
```

--------------------------------

### get_command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Get a Command from the internal list of commands.

```APIDOC
## get_command(name)

### Description
Get a Command from the internal list of commands. This can be used to get aliases or fully qualified subcommands.

### Parameters
- **name** (str) - Required - The name of the command to get.

### Returns
- **Command** - The command object or None if not found.
```

--------------------------------

### discord.on_message_delete(message)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is deleted. Requires the message to be in the internal message cache and Intents.messages to be enabled.

```APIDOC
## discord.on_message_delete(message)

### Description
Called when a message is deleted. If the message is not found in the internal message cache, this event will not be called.

### Parameters
- **message** (Message) - Required - The deleted message.
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the channel.

```APIDOC
## await delete(reason=None)

### Description
Deletes the channel. You must have `manage_channels` to do this.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this channel.
```

--------------------------------

### discord.ext.commands.flag

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator used to override default functionality and parameters of FlagConverter class attributes.

```APIDOC
## discord.ext.commands.flag

### Description
Overrides default functionality and parameters of the underlying `FlagConverter` class attributes.

### Parameters
- **name** (str) - Optional - The flag name. If not given, defaults to the attribute name.
- **aliases** (List[str]) - Optional - Aliases to the flag name.
- **default** (Any) - Optional - The default parameter. Can be a value or a callable that takes `Context`.
- **max_args** (int) - Optional - The maximum number of arguments the flag can accept.
- **override** (bool) - Optional - Whether multiple given values overrides the previous value.
- **converter** (Any) - Optional - The converter to use for this flag.
- **description** (str) - Optional - The description of the flag.
- **positional** (bool) - Optional - Whether the flag is positional.
```

--------------------------------

### delete_emoji(emoji, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a custom emoji from the guild.

```APIDOC
## await delete_emoji(emoji, reason=None)

### Description
Deletes the custom `Emoji` from the guild. Requires `manage_emojis` permission.

### Parameters
- **emoji** (abc.Snowflake) - Required - The emoji you are deleting.
- **reason** (Optional[str]) - Optional - The reason for deleting this emoji.

### Raises
- **Forbidden** - You are not allowed to delete emojis.
- **HTTPException** - An error occurred deleting the emoji.
```

--------------------------------

### remove_attachments

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes attachments from the message.

```APIDOC
## await remove_attachments(*attachments)

### Description
Removes specified attachments from the message.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove.

### Returns
- **InteractionMessage** - The newly edited message.
```

--------------------------------

### create_application_emoji(name, image)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates an emoji for the current application.

```APIDOC
## create_application_emoji(name, image)

### Description
Create an emoji for the current application.

### Parameters
- **name** (str) - Required - The emoji name. Must be between 2 and 32 characters long.
- **image** (bytes) - Required - The bytes-like object representing the image data to use. Only JPG, PNG and GIF images are supported.
```

--------------------------------

### AutoShardedClient.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a websocket connection to Discord.

```APIDOC
## await connect(reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord. This is a coroutine.

### Parameters
- **reconnect** (bool) - Optional - If we should attempt reconnecting.

### Raises
- **GatewayNotFound** - If the gateway to connect to Discord is not found.
- **ConnectionClosed** - The websocket connection has been terminated.
```

--------------------------------

### Define a Custom Transformer

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Implement a custom Transformer by subclassing app_commands.Transformer and overriding the transform method. Use the Transform type hint in command parameters to apply the transformation.

```python
class Point(typing.NamedTuple):
    x: int
    y: int


class PointTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> Point:
        (x, _, y) = value.partition(",")
        return Point(x=int(x.strip()), y=int(y.strip()))


@app_commands.command()
async def graph(
    interaction: discord.Interaction,
    point: app_commands.Transform[Point, PointTransformer],
):
    await interaction.response.send_message(str(point))
```

--------------------------------

### discord.app_commands.Group

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A class that implements an application command group. These are usually inherited rather than created manually.

```APIDOC
## class discord.app_commands.Group

### Description
A class that implements an application command group. These are usually inherited rather than created manually.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the group.
- **description** (Union[str, locale_str]) - Optional - The description of the group.
- **auto_locale_strings** (bool) - Optional - Whether to implicitly wrap translatable strings into locale_str. Defaults to True.
- **default_permissions** (Optional[Permissions]) - Optional - The default permissions that can execute this group.
- **guild_only** (bool) - Optional - Whether the group should only be usable in guild contexts. Defaults to False.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **parent** (Optional[Group]) - Optional - The parent application command.
- **extras** (dict) - Optional - A dictionary to store extraneous data.
```

--------------------------------

### Define Context Menus

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the @context_menu decorator to create context menu interactions. The callback must accept an Interaction as the first argument and a target (Member, User, or Message) as the second.

```python
@app_commands.context_menu()
async def react(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message("Very cool message!", ephemeral=True)


@app_commands.context_menu()
async def ban(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message(f"Should I actually ban {user}...", ephemeral=True)
```

--------------------------------

### CommandTree.set_translator

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Sets the translator to use for translating commands.

```APIDOC
## await CommandTree.set_translator(translator)

### Description
Sets the translator to use for translating commands. If a translator was previously set, it will be unloaded using its Translator.unload() method.

### Parameters
#### Parameters
- **translator** (Optional[Translator]) - Required - The translator to use. If None then the translator is just removed and unloaded.

### Raises
- **TypeError** - The translator was not None or a Translator instance.
```

--------------------------------

### reload_extension(name, *, package=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Atomically reloads an extension, replacing it with a refreshed version.

```APIDOC
## reload_extension(name, *, package=None)

### Description
Atomically reloads an extension. If an operation fails mid-reload, the bot rolls back to the prior working state.

### Parameters
- **name** (str) - Required - The extension name to reload (dot-separated).
- **package** (Optional[str]) - Optional - The package name to resolve relative imports with.
```

--------------------------------

### Rename Command Parameters

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Renames parameters in the Discord UI while maintaining the original function parameter name for decorators.

```python
@app_commands.command()
@app_commands.rename(the_member_to_ban="member")
async def ban(interaction: discord.Interaction, the_member_to_ban: discord.Member):
    await interaction.response.send_message(f"Banned {the_member_to_ban}")
```

--------------------------------

### discord.Attachment.save

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the attachment content to a file-like object or path.

```APIDOC
## await discord.Attachment.save(fp, *, seek_begin=True, use_cached=False)

### Description
Saves this attachment into a file-like object. This is a coroutine.

### Parameters
- **fp** (Union[io.BufferedIOBase, os.PathLike]) - Required - The file-like object to save this attachment to or the filename to use.
- **seek_begin** (bool) - Optional - Whether to seek to the beginning of the file after saving is successfully done.
- **use_cached** (bool) - Optional - Whether to use proxy_url rather than url when downloading the attachment.

### Returns
- **int** - The number of bytes written.

### Raises
- **HTTPException** - Saving the attachment failed.
- **NotFound** - The attachment was deleted.
```

--------------------------------

### CategoryChannel.create_text_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shortcut method to create a TextChannel in the category.

```APIDOC
## await create_text_channel(name, **options)

### Description
A shortcut method to Guild.create_text_channel() to create a TextChannel in the category.

### Returns
- **TextChannel** - The channel that was just created.
```

--------------------------------

### Using custom context in Bot

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Configures the bot to use a custom Context subclass via get_context.

```python
class MyBot(commands.Bot):
    async def on_message(self, message):
        ctx = await self.get_context(message, cls=MyContext)
        await self.invoke(ctx)
```

--------------------------------

### AutoShardedClient.get_shard

Source: https://discordpy.readthedocs.io/en/latest/api.html

Gets the shard information at a given shard ID.

```APIDOC
## get_shard(shard_id)

### Description
Gets the shard information at a given shard ID or None if not found.

### Parameters
- **shard_id** (int) - Required - The ID of the shard to retrieve.
```

--------------------------------

### Advanced Converter Class

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Implements the Converter interface to perform asynchronous processing or access context-specific data.

```python
import random


class Slapper(commands.Converter):
    async def convert(self, ctx, argument):
        to_slap = random.choice(ctx.guild.members)
        return f"{ctx.author} slapped {to_slap} because *{argument}*"


@bot.command()
async def slap(ctx, *, reason: Slapper):
    await ctx.send(reason)
```

--------------------------------

### @discord.ext.commands.dynamic_cooldown(cooldown, type)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator that adds a dynamic cooldown to a Command. It takes a function that accepts a Context and returns a Cooldown or None.

```APIDOC
## @discord.ext.commands.dynamic_cooldown(cooldown, type)

### Description
A decorator that adds a dynamic cooldown to a `Command`. This differs from `cooldown()` in that it takes a function that accepts a single parameter of type `Context` and must return a `Cooldown` or `None`.

### Parameters
- **cooldown** (Callable[[Context], Optional[Cooldown]]) - Required - A function that takes a message and returns a cooldown that will apply to this invocation or `None` if the cooldown should be bypassed.
- **type** (BucketType) - Required - The type of cooldown to have.
```

--------------------------------

### HybridCommand

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A class representing a command that functions as both an application command and a regular text command.

```APIDOC
## HybridCommand

### Description
A class that is both an application command and a regular text command. It supports the same parameters and attributes as a regular Command but doubles as an application command.

### Methods
- **@after_invoke(coro)**: Registers a coroutine as a post-invoke hook.
- **@autocomplete(name)**: Registers a coroutine as an autocomplete prompt for a parameter.
- **@before_invoke(coro)**: Registers a coroutine as a pre-invoke hook.
- **@error(coro)**: Registers a coroutine as a local error handler.
- **can_run(ctx)**: Checks if the command can be executed by checking predicates and disabled status.
```

--------------------------------

### HybridGroup

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A class representing a group of commands that functions as both an application command group and a regular text group.

```APIDOC
## HybridGroup

### Description
A class that is both an application command group and a regular text group. It inherits functionality from Group and ensures invoke_without_command is set to True.

### Key Methods
- **@command(...)**: Decorator to add a command to the group.
- **@group(...)**: Decorator to add a sub-group to the group.
- **add_check(func)**: Adds a check to the group.
- **remove_command(name)**: Removes a command from the group.
```

--------------------------------

### discord.on_raw_reaction_add(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Triggered when a reaction is added to a message, regardless of cache state.

```APIDOC
## discord.on_raw_reaction_add(payload)

### Description
Called when a message has a reaction added. Unlike on_reaction_add, this is called regardless of the state of the internal message cache.

### Parameters
- **payload** (RawReactionActionEvent) - The raw event payload data.
```

--------------------------------

### remove_attachments(*attachments)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes specific attachments from the message.

```APIDOC
## remove_attachments(*attachments)

### Description
Removes specified attachments from the message. This is a coroutine.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove from the message.

### Returns
- **WebhookMessage** - The newly edited message.
```

--------------------------------

### Edit Welcome Screen

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the welcome screen description and channels. Requires appropriate permissions and may raise HTTPException, Forbidden, or NotFound.

```python
await welcome_screen.edit(
    description="This is a very cool community server!",
    welcome_channels=[
        WelcomeChannel(channel=rules_channel, description="Read the rules!", emoji="👨‍🏫"),
        WelcomeChannel(channel=announcements_channel, description="Watch out for announcements!", emoji=custom_emoji),
    ],
)
```

--------------------------------

### Asset.save()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the asset into a file-like object.

```APIDOC
## await save(fp, seek_begin=True)

### Description
Saves this asset into a file-like object.

### Parameters
- **fp** (Union[io.BufferedIOBase, os.PathLike]) - Required - The file-like object to save this asset to or the filename to use.
- **seek_begin** (bool) - Optional - Whether to seek to the beginning of the file after saving is successfully done.

### Returns
- **int** - The number of bytes written.
```

--------------------------------

### Define Posix-style flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a space delimiter and double-dash prefix for command flags.

```python
class PosixLikeFlags(commands.FlagConverter, delimiter=" ", prefix="--"):
    hello: str
```

--------------------------------

### @context_menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator used to create an application command context menu from a function.

```APIDOC
## @context_menu(*, name=..., nsfw=False, guild=..., guilds=..., auto_locale_strings=True, extras=...)

### Description
A decorator that creates an application command context menu from a regular function. The function must accept an Interaction as the first parameter and a Member, User, or Message as the second.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the context menu.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **guild** (Optional[Snowflake]) - Optional - The guild to add the context menu to.
- **guilds** (List[Snowflake]) - Optional - A list of guilds to add the context menu to.
- **auto_locale_strings** (bool) - Optional - If True, translatable strings are wrapped in locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary for storing extraneous data.
```

--------------------------------

### connect(timeout, reconnect, cls, self_deaf, self_mute)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects to a voice channel and creates a VoiceClient to establish a connection to the voice server.

```APIDOC
## connect(timeout, reconnect, cls, self_deaf, self_mute)

### Description
Connects to voice and creates a VoiceClient to establish your connection to the voice server. This requires voice_states.

### Parameters
- **timeout** (float) - Optional - The timeout in seconds to wait the connection to complete. Defaults to 30.0.
- **reconnect** (bool) - Optional - Whether the bot should automatically attempt a reconnect. Defaults to True.
- **cls** (Type[VoiceProtocol]) - Optional - A type that subclasses VoiceProtocol to connect with. Defaults to VoiceClient.
- **self_mute** (bool) - Optional - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Optional - Indicates if the client should be self-deafened.

### Raises
- **asyncio.TimeoutError** - Could not connect to the voice channel in time.
- **ClientException** - You are already connected to a voice channel.
- **OpusNotLoaded** - The opus library has not been loaded.

### Returns
- **VoiceProtocol** - A voice client that is fully connected to the voice server.
```

--------------------------------

### discord.on_invite_create

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an Invite is created. Requires Intents.invites.

```APIDOC
## discord.on_invite_create(invite)

### Description
Called when an Invite is created. You must have manage_channels to receive this. This requires Intents.invites to be enabled.

### Parameters
- **invite** (Invite) - The invite that was created.
```

--------------------------------

### get_member(user_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a member with the given ID.

```APIDOC
## get_member(user_id)

### Description
Returns a member with the given ID.

### Parameters
- **user_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Member]** - The member or `None` if not found.
```

--------------------------------

### create_dm(user)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a DMChannel with the specified user.

```APIDOC
## create_dm(user)

### Description
Creates a DMChannel with this user.

### Parameters
- **user** (Snowflake) - Required - The user to create a DM with.
```

--------------------------------

### SoundEffect.read()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the sound effect asset as a bytes object.

```APIDOC
## await SoundEffect.read()

### Description
Retrieves the content of this asset as a bytes object.

### Returns
- **bytes** - The content of the asset.

### Raises
- **DiscordException** - There was no internal connection state.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
```

--------------------------------

### Accessing Iterable Attributes

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Shows invalid indexing on iterable attributes and the correct approach using list casting.

```python
if client.servers[0].name == "test":
    # do something
```

```python
servers = list(client.servers)
# work with servers
```

--------------------------------

### discord.SelectOption

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents an option within a select menu. Users can construct these to define the choices available to end-users.

```APIDOC
## class discord.SelectOption(label, value=..., description=None, emoji=None, default=False)

### Description
Represents a select menu’s option. These can be created by users.

### Parameters
- **label** (str) - Required - The label of the option (up to 100 characters).
- **value** (str) - Optional - The value of the option (up to 100 characters). Defaults to label if not provided.
- **description** (Optional[str]) - Optional - An additional description of the option (up to 100 characters).
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the option.
- **default** (bool) - Optional - Whether this option is selected by default.
```

--------------------------------

### InteractionMessage

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents the original interaction response message, allowing for editing, deleting, and reaction management.

```APIDOC
## InteractionMessage

### Description
Represents the original interaction response message. Inherits from discord.Message with specialized edit and delete functionality.

### Methods
- **add_reaction(emoji)** (coroutine) - Adds a reaction to the message.
- **clear_reaction(emoji)** (coroutine) - Clears a specific reaction from the message.
- **clear_reactions()** (coroutine) - Removes all reactions from the message.

### Properties
- **clean_content** (str) - Returns the message content with mentions transformed into display names.
```

--------------------------------

### Emoji.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the custom emoji. Requires the manage_emojis permission if the emoji is not application-owned.

```APIDOC
## await delete(*, reason=None)

### Description
Deletes the custom emoji. You must have `manage_emojis` to do this if `is_application_owned()` is `False`.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this emoji. Shows up on the audit log. This does not apply if `is_application_owned()` is `True`.

### Raises
- **Forbidden** - You are not allowed to delete emojis.
- **HTTPException** - An error occurred deleting the emoji.
- **MissingApplicationID** - The emoji is owned by an application but the application ID is missing.
```

--------------------------------

### Registering Event Listeners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use add_listener to register coroutines as event handlers without using decorators.

```python
async def on_ready():
    pass


async def my_message(message):
    pass


bot.add_listener(on_ready)
bot.add_listener(my_message, "on_message")
```

--------------------------------

### VoiceChannel.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the voice channel with the provided options. Requires manage_channels permission.

```APIDOC
## await edit(**options)

### Description
Edits the channel properties. This is a coroutine.

### Parameters
- **name** (str) - Optional - The new channel name.
- **bitrate** (int) - Optional - The new channel bitrate.
- **nsfw** (bool) - Optional - Mark the channel as NSFW.
- **user_limit** (int) - Optional - The new user limit.
- **position** (int) - Optional - The new channel position.
- **sync_permissions** (bool) - Optional - Sync permissions with category.
- **category** (Optional[CategoryChannel]) - Optional - The new category.
- **slowmode_delay** (int) - Optional - Slowmode rate limit in seconds.
- **reason** (Optional[str]) - Optional - Reason for audit log.
- **overwrites** (Mapping) - Optional - Permission overwrites.
- **rtc_region** (Optional[str]) - Optional - Voice region.
- **video_quality_mode** (VideoQualityMode) - Optional - Camera video quality.
- **status** (Optional[str]) - Optional - Voice channel status.

### Returns
- **VoiceChannel** (Optional) - The edited channel or None if only position changed.
```

--------------------------------

### discord.PCMVolumeTransformer

Source: https://discordpy.readthedocs.io/en/latest/api.html

A transformer class that adds volume control capabilities to an existing AudioSource.

```APIDOC
## class discord.PCMVolumeTransformer(original, volume=1.0)

### Description
Transforms an existing AudioSource to include volume controls. Note that this does not work on audio sources where is_opus() returns True.

### Parameters
- **original** (AudioSource) - Required - The original audio source to be transformed.
- **volume** (float) - Optional - The initial volume level as a floating point percentage (e.g., 1.0 for 100%).

### Attributes
- **volume** (float) - Retrieves or sets the volume as a floating point percentage.

### Methods
- **read()** - Reads 20ms worth of audio data.
- **cleanup()** - Performs necessary cleanup for buffer data or processes.
```

--------------------------------

### Webhook.from_url

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial Webhook object from a provided webhook URL.

```APIDOC
## Webhook.from_url(url, *, session=..., client=..., bot_token=None)

### Description
Creates a partial Webhook from a webhook URL. This is used to initialize a webhook object for sending messages.

### Parameters
- **url** (str) - Required - The URL of the webhook.
- **session** (aiohttp.ClientSession) - Optional - The session to use to send requests with.
- **client** (Client) - Optional - The client to initialise this webhook with.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.

### Returns
- **Webhook** - A partial Webhook object.
```

--------------------------------

### get_command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves a specific application command from the tree.

```APIDOC
## get_command(command, *, guild=None, type=AppCommandType.chat_input)

### Description
Gets an application command from the tree.

### Parameters
- **command** (str) - Required - The name of the root command to get.
- **guild** (Optional[Snowflake]) - Optional - The guild to get the command from. If not given or None then it gets a global command instead.
- **type** (AppCommandType) - Optional - The type of command to get. Defaults to chat_input.

### Returns
- **Optional[Union[Command, ContextMenu, Group]]** - The application command that was found. If nothing was found then None is returned instead.
```

--------------------------------

### AllowedMentions

Source: https://discordpy.readthedocs.io/en/latest/api.html

A class representing allowed mentions in a message, configurable globally or per-message.

```APIDOC
## AllowedMentions(everyone=True, users=True, roles=True, replied_user=True)

### Description
A class that represents what mentions are allowed in a message.

### Attributes
- **everyone** (bool) - Whether to allow everyone and here mentions.
- **users** (Union[bool, Sequence[abc.Snowflake]]) - Controls the users being mentioned.
- **roles** (Union[bool, Sequence[abc.Snowflake]]) - Controls the roles being mentioned.
- **replied_user** (bool) - Whether to mention the author of the message being replied to.

### Methods
- **all()**: Factory method returning an AllowedMentions object with all fields set to True.
- **none()**: Factory method returning an AllowedMentions object with all fields set to False.
```

--------------------------------

### fetch_soundboard_default_sounds

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves all default soundboard sounds.

```APIDOC
## fetch_soundboard_default_sounds()

### Description
Retrieves all default soundboard sounds.

### Returns
- **List[SoundboardDefaultSound]** - All default soundboard sounds.
```

--------------------------------

### Apply Command Attributes to a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use command_attrs to set default attributes for all commands within a cog, which can be overridden by individual command definitions.

```python
class MyCog(commands.Cog, command_attrs=dict(hidden=True)):
    @commands.command()
    async def foo(self, ctx):
        pass  # hidden -> True

    @commands.command(hidden=False)
    async def bar(self, ctx):
        pass  # hidden -> False
```

--------------------------------

### discord.ext.commands.Parameter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A class that stores information on a Command's parameter, providing access to metadata and default value resolution.

```APIDOC
## discord.ext.commands.Parameter

### Methods
- **get_default(ctx)**: A coroutine that gets this parameter's default value using the provided invocation context.
- **replace(**kwargs)**: Creates a customized copy of the Parameter.

### Properties
- **name** (str): The parameter's name.
- **kind** (Any): The parameter's kind.
- **default** (Any): The parameter's default value.
- **annotation** (Any): The parameter's annotation.
- **required** (bool): Whether this parameter is required.
- **converter** (Any): The converter used for this parameter.
- **description** (Optional[str]): The description of this parameter.
- **displayed_default** (Optional[str]): The displayed default in Command.signature.
- **displayed_name** (Optional[str]): The name displayed to the user.
```

--------------------------------

### Checking Channel Types

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use isinstance() with specific channel classes or abstract base classes to identify channel types after the v1.0 split.

```python
isinstance(channel, discord.abc.GuildChannel)
```

```python
isinstance(channel, discord.abc.PrivateChannel)
```

```python
isinstance(channel, discord.TextChannel)
```

--------------------------------

### discord.utils.resolve_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves an invite from an Invite object, URL, or code.

```APIDOC
## discord.utils.resolve_invite(invite)

### Description
Resolves an invite from a Invite, URL or code. Returns a ResolvedInvite data class.

### Parameters
- **invite** (Union[Invite, str]) - Required - The invite.

### Returns
- **ResolvedInvite** - A data class containing the invite code and the event ID.
```

--------------------------------

### Implement a static cooldown for an app command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses the cooldown decorator to limit command usage to once every 5 seconds per member, with an error handler to notify the user when the cooldown is active.

```python
@tree.command()
@app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Hello")


@test.error
async def on_test_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
```

--------------------------------

### create_webhook

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new webhook for the channel.

```APIDOC
## create_webhook(name, avatar, reason)

### Description
Creates a webhook for this channel. This is a coroutine.

### Parameters
- **name** (str) - Required - The webhook’s name.
- **avatar** (Optional[bytes]) - Optional - A bytes-like object representing the webhook’s default avatar.
- **reason** (Optional[str]) - Optional - The reason for creating this webhook.

### Returns
- Webhook - The created webhook.
```

--------------------------------

### fetch_ban(user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the ban entry for a specific user.

```APIDOC
## await fetch_ban(user)

### Description
Retrieves the `BanEntry` for a user. Requires `ban_members` permission.

### Parameters
- **user** (abc.Snowflake) - Required - The user to get ban information from.

### Returns
- **BanEntry** - The `BanEntry` object for the specified user.
```

--------------------------------

### get_member_named(name)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Searches for a member in the guild by their name, nickname, or global name.

```APIDOC
## get_member_named(name)

### Description
Returns the first member found that matches the name provided. The lookup order includes nickname, global name, and username.

### Parameters
- **name** (str) - Required - The name of the member to lookup.

### Returns
- **Optional[Member]** - The member in this guild with the associated name, or None if not found.
```

--------------------------------

### Inline flag descriptions

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Passing descriptions directly to the flag() function.

```python
class BanFlags(commands.FlagConverter):
    member: discord.Member = commands.flag(description="The member to ban")
    reason: str = commands.flag(description="The reason for the ban")
    days: int = commands.flag(default=1, description="The number of days worth of messages to delete")


@commands.hybrid_command()
async def ban(ctx, *, flags: BanFlags): ...
```

--------------------------------

### discord.on_socket_raw_send(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a send operation is performed on the WebSocket.

```APIDOC
## discord.on_socket_raw_send(payload)

### Description
Called whenever a send operation is done on the WebSocket before the message is sent. Requires `enable_debug_events` to be set in the `Client`.

### Parameters
- **payload** (Union[bytes, str]) - Required - The message being sent to the WebSocket.
```

--------------------------------

### Reload an extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

Use the reload_extension method to apply changes to an extension without restarting the bot.

```python
>>> await bot.reload_extension('hello')
```

--------------------------------

### remove_reaction(emoji, member)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes a reaction from the message for a specific member.

```APIDOC
## remove_reaction(emoji, member)

### Description
Remove a reaction by the member from the message. Requires 'manage_messages' if the reaction is not your own. This is a coroutine.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to remove.
- **member** (abc.Snowflake) - Required - The member for which to remove the reaction.

### Raises
- **HTTPException** - Removing the reaction failed.
- **Forbidden** - Insufficient permissions.
- **NotFound** - Member or emoji not found.
- **TypeError** - Invalid emoji parameter.
```

--------------------------------

### Hybrid command parameter description

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Using app_commands.describe with a FlagConverter in a hybrid command.

```python
class BanFlags(commands.FlagConverter):
    member: discord.Member
    reason: str
    days: int = 1


@commands.hybrid_command()
@app_commands.describe(
    member="The member to ban",
    reason="The reason for the ban",
    days="The number of days worth of messages to delete",
)
async def ban(ctx, *, flags: BanFlags): ...
```

--------------------------------

### edit_welcome_screen(**fields)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the guild's welcome screen configuration.

```APIDOC
## edit_welcome_screen(**fields)

### Description
A shorthand method to edit the welcome screen. Requires `COMMUNITY` feature and `manage_guild` permission.

### Returns
- `WelcomeScreen` - The edited welcome screen.
```

--------------------------------

### Asset.read()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the asset as a bytes object.

```APIDOC
## await read()

### Description
Retrieves the content of this asset as a bytes object.

### Returns
- **bytes** - The content of the asset.
```

--------------------------------

### discord.on_raw_message_delete(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is deleted, regardless of the internal message cache state. Requires Intents.messages to be enabled.

```APIDOC
## discord.on_raw_message_delete(payload)

### Description
Called when a message is deleted. Unlike on_message_delete(), this is called regardless of the message being in the internal message cache or not.

### Parameters
- **payload** (RawMessageDeleteEvent) - Required - The raw event payload data.
```

--------------------------------

### SoundEffect.save()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the sound effect asset into a file-like object.

```APIDOC
## await SoundEffect.save(fp, *, seek_begin=True)

### Description
Saves this asset into a file-like object.

### Parameters
- **fp** (Union[io.BufferedIOBase, os.PathLike]) - Required - The file-like object to save this asset to or the filename to use.
- **seek_begin** (bool) - Optional - Whether to seek to the beginning of the file after saving is successfully done.

### Returns
- **int** - The number of bytes written.
```

--------------------------------

### Define Windows-style flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses an empty delimiter and forward-slash prefix for command flags.

```python
class WindowsLikeFlags(commands.FlagConverter, prefix="/", delimiter=""):
    make: str
```

--------------------------------

### FFmpegOpusAudio.from_probe

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine factory method that creates an FFmpegOpusAudio instance by probing the input source for codec and bitrate information, allowing for optimized audio streaming.

```APIDOC
## FFmpegOpusAudio.from_probe

### Description
Creates an FFmpegOpusAudio instance by probing the source for audio metadata. This is the recommended way to initialize audio to avoid unnecessary re-encoding.

### Parameters
- **source** (str | io.BufferedIOBase) - Required - The input source to probe.
- **method** (str) - Optional - The probing method.
- **kwargs** (dict) - Optional - Additional arguments passed to the constructor.

### Example
```python
source = await discord.FFmpegOpusAudio.from_probe("song.webm")
voice_client.play(source)
```
```

--------------------------------

### PartialMessage

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents a partial message to aid with working with messages when only a message and channel ID are present.

```APIDOC
## class discord.PartialMessage

### Description
Represents a partial message to aid with working with messages when only a message and channel ID are present. This class is trimmed down and has no rich attributes.

### Attributes
- **channel** (Union[PartialMessageable, TextChannel, StageChannel, VoiceChannel, Thread, DMChannel]) - The channel associated with this partial message.
- **id** (int) - The message ID.
- **guild** (Optional[Guild]) - The guild that the partial message belongs to, if applicable.
- **created_at** (datetime.datetime) - The partial message’s creation time in UTC.
- **jump_url** (str) - A URL that allows the client to jump to this message.

### Methods
#### await fetch()
Fetches the partial message to a full Message object.

**Raises:**
- **NotFound** - The message was not found.
- **Forbidden** - You do not have the permissions required to get a message.
- **HTTPException** - Retrieving the message failed.
```

--------------------------------

### discord.on_socket_raw_receive(msg)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is received from the WebSocket before parsing.

```APIDOC
## discord.on_socket_raw_receive(msg)

### Description
Called whenever a message is completely received from the WebSocket, before it is processed and parsed. Requires `enable_debug_events` to be set in the `Client`.

### Parameters
- **msg** (str) - Required - The message passed in from the WebSocket library.
```

--------------------------------

### send_audio_packet(data, *, encode=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends an audio packet composed of the data. You must be connected to play audio.

```APIDOC
## send_audio_packet(data, *, encode=True)

### Description
Sends an audio packet composed of the data. You must be connected to play audio.

### Parameters
- **data** (bytes) - Required - The bytes-like object denoting PCM or Opus voice data.
- **encode** (bool) - Optional - Indicates if data should be encoded into Opus.
```

--------------------------------

### Use typing.Optional for default values on conversion failure

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Enables back-referencing behavior where a default value is used if the primary conversion fails.

```python
import typing


@bot.command()
async def bottles(ctx, amount: typing.Optional[int] = 99, *, liquid="beer"):
    await ctx.send(f"{amount} bottles of {liquid} on the wall!")
```

--------------------------------

### discord.ui.RadioGroup

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a radio group component within a modal.

```APIDOC
## class discord.ui.RadioGroup(custom_id=..., required=True, options=..., id=None)

### Description
Represents a radio group component within a modal that can only be used in Label. New in version 2.7.

### Parameters
- **id** (Optional[int]) - Optional - The ID of the component. This must be unique across the view.
- **custom_id** (Optional[str]) - Optional - The custom ID of the component.
- **options** (List[discord.RadioGroupOption]) - Required - A list of options that can be selected in this radio group. Can contain between 2 and 10 items.
- **required** (bool) - Required - Whether this component is required to be filled before submitting the modal. Defaults to True.

### Methods
#### add_option(label, value=..., description=None, default=False)
Adds an option to the group.
- **label** (str) - Required - The label of the option.
- **value** (str) - Optional - The value of the option. Defaults to the label.
- **description** (Optional[str]) - Optional - An additional description of the option.
- **default** (bool) - Optional - Whether this option is selected by default.

#### append_option(option)
Appends an option to the group.
- **option** (discord.RadioGroupOption) - Required - The option to append to the group.
```

--------------------------------

### discord.utils.time_snowflake

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a numeric snowflake pretending to be created at the given date.

```APIDOC
## discord.utils.time_snowflake

### Description
Returns a numeric snowflake pretending to be created at the given date.

### Parameters
- **dt** (datetime.datetime) - Required - A datetime object to convert to a snowflake.
- **high** (bool) - Optional - Whether or not to set the lower 22 bit to high or low.
```

--------------------------------

### remove_command(name)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a command from the internal list by its name.

```APIDOC
## remove_command(name)

### Description
Remove a `Command` from the internal list of commands. This could also be used as a way to remove aliases.

### Parameters
- **name** (`str`) - Required - The name of the command to remove.

### Returns
- **Command** (Optional) - The command that was removed. If the name is not valid then `None` is returned instead.
```

--------------------------------

### Add reaction to a message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Add a reaction to a message using unicode or custom emoji.

```python
emoji = "\N{THUMBS UP SIGN}"
# or '\U0001f44d' or '👍'
await message.add_reaction(emoji)
```

--------------------------------

### edit_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a message sent by a webhook. This method allows updating content, embeds, attachments, and views.

```APIDOC
## edit_message(message_id, content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None, thread=None)

### Description
Edits an existing webhook message. You can update the content, embeds, attachments, and components of the message.

### Parameters
- **message_id** (int) - Required - The message ID to edit.
- **content** (str) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Embed) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Union[View, LayoutView]) - Optional - The updated view to update this message with.
- **thread** (Snowflake) - Optional - The thread the webhook message belongs to.

### Returns
- **WebhookMessage** - The newly edited webhook message.
```

--------------------------------

### discord.utils.remove_markdown

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes markdown characters from a string.

```APIDOC
## discord.utils.remove_markdown

### Description
A helper function that removes markdown characters.

### Parameters
- **text** (str) - Required - The text to process.
- **ignore_links** (bool) - Optional - Whether to ignore links.
```

--------------------------------

### Reaction.remove

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a specific user's reaction from the message. Requires manage_messages permission if removing a reaction that is not your own.

```APIDOC
## await Reaction.remove(user)

### Description
Removes the reaction by the provided User from the message.

### Parameters
- **user** (abc.Snowflake) - Required - The user or member from which to remove the reaction.

### Raises
- **HTTPException** - Removing the reaction failed.
- **Forbidden** - You do not have the proper permissions to remove the reaction.
- **NotFound** - The user you specified, or the reaction’s message was not found.
```

--------------------------------

### change_presence

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Changes the client's presence status and activity.

```APIDOC
## await change_presence(*, activity=None, status=None)

### Description
Changes the client's presence status and activity.

### Parameters
- **activity** (Optional[BaseActivity]) - Optional - The activity to set.
- **status** (Optional[Status]) - Optional - The status to set.
```

--------------------------------

### Define a Hybrid Command Group

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the hybrid_group decorator to create command groups with sub-commands, utilizing the fallback parameter for group invocation.

```python
@bot.hybrid_group(fallback="get")
async def tag(ctx, name):
    await ctx.send(f"Showing tag: {name}")


@tag.command()
async def create(ctx, name):
    await ctx.send(f"Created tag: {name}")
```

--------------------------------

### InteractionCallbackResponse

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents an interaction response callback, providing access to the interaction ID, response type, and associated resources.

```APIDOC
## InteractionCallbackResponse

### Description
Represents an interaction response callback. Provides methods to check the state of the response.

### Methods
- **is_thinking()** (bool) - Returns whether the response was a thinking defer.
- **is_ephemeral()** (bool) - Returns whether the response was ephemeral.
```

--------------------------------

### remove_command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes an application command from the tree locally. Note that sync() must be called to reflect changes in the client.

```APIDOC
## remove_command(command, *, guild=None, type=AppCommandType.chat_input)

### Description
Removes an application command from the tree locally. This only removes the command locally – in order to sync the commands and remove them in the client, sync() must be called.

### Parameters
- **command** (str) - Required - The name of the root command to remove.
- **guild** (Optional[Snowflake]) - Optional - The guild to remove the command from. If not given or None then it removes a global command instead.
- **type** (AppCommandType) - Optional - The type of command to remove. Defaults to chat_input.

### Returns
- **Optional[Union[Command, ContextMenu, Group]]** - The application command that got removed. If nothing was removed then None is returned instead.
```

--------------------------------

### SoundboardSound.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a soundboard sound.

```APIDOC
## await SoundboardSound.delete(reason=None)

### Description
Deletes the soundboard sound. You must have `manage_expressions` to delete the sound. If the sound was created by the client, you must have either `manage_expressions` or `create_expressions`.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this sound. Shows up on the audit log.
```

--------------------------------

### Define a basic FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

A simple example of a FlagConverter class with positional and boolean flags.

```python
class Greeting(commands.FlagConverter):
    text: str = commands.flag(positional=True)
    bold: bool = False
```

--------------------------------

### add_option

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an option to the select menu.

```APIDOC
## add_option(label, value=..., description=None, emoji=None, default=False)

### Description
Adds an option to the select menu.

### Parameters
- **label** (str) - Required - The label of the option displayed to users.
- **value** (str) - Optional - The value of the option not displayed to users.
- **description** (Optional[str]) - Optional - An additional description of the option.
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the option.
- **default** (bool) - Optional - Whether this option is selected by default.
```

--------------------------------

### get_soundboard_sound(sound_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific soundboard sound within the guild by its ID.

```APIDOC
## get_soundboard_sound(sound_id)

### Description
Returns a soundboard sound with the given ID.

### Parameters
- **sound_id** (int) - Required - The ID to search for.

### Returns
- **Optional[SoundboardSound]** - The soundboard sound or None if not found.
```

--------------------------------

### Webhook.edit_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a message owned by the webhook using its ID.

```APIDOC
## Webhook.edit_message

### Description
Edits a message owned by this webhook. This is a lower level interface to `WebhookMessage.edit()`.

### Parameters
- **message_id** (int) - Required - The ID of the message to edit.
- **content** (str) - Optional - The new content.
- **embeds** (List[Embed]) - Optional - The new list of embeds.
- **embed** (Embed) - Optional - The new embed.
- **attachments** (List[Attachment]) - Optional - The new attachments.
- **view** (View) - Optional - The new view.
- **allowed_mentions** (AllowedMentions) - Optional - The new allowed mentions.
- **thread** (Snowflake) - Optional - The thread containing the message.
```

--------------------------------

### discord.FFmpegOpusAudio.from_probe

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an FFmpegOpusAudio instance by probing the input source for codec and bitrate information.

```APIDOC
## discord.FFmpegOpusAudio.from_probe(source, method=None, **kwargs)

### Description
Creates an instance of FFmpegOpusAudio by probing the provided source to determine necessary codec and bitrate information.

### Parameters
- **source** (str) - Required - The input source path or identifier.
- **method** (Union[str, Callable]) - Optional - The probing method. Can be 'native' (ffprobe), 'fallback' (ffmpeg), or a custom callable.
- **kwargs** (dict) - Optional - Additional parameters passed to the FFmpegOpusAudio constructor.

### Returns
- **FFmpegOpusAudio** - An instance of the FFmpegOpusAudio class.

### Raises
- **AttributeError** - If an invalid probe method is provided.
- **TypeError** - If the probe parameter is not a string or callable.
```

--------------------------------

### ShardInfo.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects a specific shard.

```APIDOC
## await ShardInfo.connect()

### Description
Connects a shard. If the shard is already connected this does nothing.
```

--------------------------------

### Define Command Flags with FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Defines a command interface using FlagConverter to allow user-friendly flag syntax in command invocations.

```python
from discord.ext import commands
import discord


class BanFlags(commands.FlagConverter):
    member: discord.Member
    reason: str
    days: int = 1


@commands.command()
async def ban(ctx, *, flags: BanFlags):
    plural = f"{flags.days} days" if flags.days != 1 else f"{flags.days} day"
    await ctx.send(f"Banned {flags.member} for {flags.reason!r} (deleted {plural} worth of messages)")
```

--------------------------------

### application_info

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the bot's application information.

```APIDOC
## await application_info()

### Description
Retrieves the bot's application information as a coroutine.

### Returns
- **AppInfo** - The bot's application information.
```

--------------------------------

### Describe Command Parameters

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Provides descriptions for command parameters using the describe decorator or standard docstrings.

```python
@app_commands.command(description="Bans a member")
@app_commands.describe(member="the member to ban")
async def ban(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"Banned {member}")
```

```python
@app_commands.command()
async def ban(interaction: discord.Interaction, member: discord.Member):
    """Bans a member

    Parameters
    -----------
    member: discord.Member
        the member to ban
    """
    await interaction.response.send_message(f"Banned {member}")
```

--------------------------------

### connect(reconnect=True)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a websocket connection and starts the event loop to listen for messages from Discord.

```APIDOC
## connect(reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord. This is a loop that runs the entire event system and miscellaneous aspects of the library.

### Parameters
- **reconnect** (bool) - Optional - If we should attempt reconnecting, either due to internet failure or a specific failure on Discord’s part.
```

--------------------------------

### append_option

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Appends a pre-existing SelectOption to the select menu.

```APIDOC
## append_option(option)

### Description
Appends an option to the select menu.

### Parameters
- **option** (discord.SelectOption) - Required - The option to append to the select menu.
```

--------------------------------

### Configure User Installation

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Apply user_install to make a command available for installation by users. This decorator does not function on subcommands.

```python
@app_commands.command()
@app_commands.user_install()
async def my_user_install_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in users by default!")
```

--------------------------------

### Create FFmpegOpusAudio from Probe

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use the from_probe factory method to automatically detect audio codec and bitrate information before initializing the audio source.

```python
source = await discord.FFmpegOpusAudio.from_probe("song.webm")
voice_client.play(source)
```

--------------------------------

### discord.utils.snowflake_time

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the creation time of the given snowflake ID.

```APIDOC
## discord.utils.snowflake_time

### Description
Returns the creation time of the given snowflake.

### Parameters
- **id** (int) - Required - The snowflake ID.
```

--------------------------------

### SoundboardSound.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the properties of a soundboard sound, such as name, volume, or emoji.

```APIDOC
## await SoundboardSound.edit(name=..., volume=..., emoji=..., reason=None)

### Description
Edits the soundboard sound. You must have `manage_expressions` to edit the sound. If the sound was created by the client, you must have either `manage_expressions` or `create_expressions`.

### Parameters
- **name** (str) - Optional - The new name of the sound. Must be between 2 and 32 characters.
- **volume** (Optional[float]) - Optional - The new volume of the sound. Must be between 0 and 1.
- **emoji** (Optional[Union[Emoji, PartialEmoji, str]]) - Optional - The new emoji of the sound.
- **reason** (Optional[str]) - Optional - The reason for editing this sound. Shows up on the audit log.

### Returns
- **SoundboardSound** - The newly updated soundboard sound.
```

--------------------------------

### Implement an inline advanced converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a classmethod named convert within the type itself to handle conversion logic, avoiding the need for a separate converter class.

```python
class JoinDistance:
    def __init__(self, joined, created):
        self.joined = joined
        self.created = created

    @classmethod
    async def convert(cls, ctx, argument):
        member = await commands.MemberConverter().convert(ctx, argument)
        return cls(member.joined_at, member.created_at)

    @property
    def delta(self):
        return self.joined - self.created


@bot.command()
async def delta(ctx, *, member: JoinDistance):
    is_new = member.delta.days < 100
    if is_new:
        await ctx.send("Hey you're pretty new!")
    else:
        await ctx.send("Hm you're not so new.")
```

--------------------------------

### get_channel(channel_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a channel with the given ID, excluding threads.

```APIDOC
## get_channel(channel_id)

### Description
Returns a channel with the given ID. This does not search for threads.

### Parameters
- **channel_id** (int) - Required - The ID to search for.

### Returns
- **Optional[abc.GuildChannel]** - The returned channel or `None` if not found.
```

--------------------------------

### get_stage_instance(stage_instance_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific stage instance within the guild by its ID.

```APIDOC
## get_stage_instance(stage_instance_id)

### Description
Returns a stage instance with the given ID.

### Parameters
- **stage_instance_id** (int) - Required - The ID to search for.

### Returns
- **Optional[StageInstance]** - The stage instance or None if not found.
```

--------------------------------

### get_soundboard_sound(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a soundboard sound from the cache by its ID.

```APIDOC
## get_soundboard_sound(id)

### Description
Returns a soundboard sound with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **SoundboardSound** (Optional) - The soundboard sound or None if not found.
```

--------------------------------

### await delete_original_response()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the original interaction response message.

```APIDOC
## await delete_original_response()

### Description
Deletes the original interaction response message. This is a lower-level interface to InteractionMessage.delete() to save an HTTP request.
```

--------------------------------

### SKU.fetch_subscription

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific Subscription by its ID.

```APIDOC
## await SKU.fetch_subscription(subscription_id)

### Description
Retrieves a Subscription with the specified ID.

### Parameters
- **subscription_id** (int) - Required - The subscription’s ID to fetch from.

### Returns
- **Subscription** - The subscription you requested.

### Raises
- **NotFound** - A subscription with this ID does not exist.
- **HTTPException** - Fetching the subscription failed.
```

--------------------------------

### Converter Usage

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows that converters can be used directly as type annotations in command definitions.

```python
@bot.command()
async def slap(ctx, *, reason: Slapper):
    await ctx.send(reason)
```

--------------------------------

### vanity_invite()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the guild’s special vanity invite.

```APIDOC
## vanity_invite()

### Description
Returns the guild’s special vanity invite. The guild must have VANITY_URL in features. You must have manage_guild to do this.

### Raises
- **Forbidden** - You do not have the proper permissions to get this.
- **HTTPException** - Retrieving the vanity invite failed.

### Response
- **Invite** (Optional[Invite]) - The special vanity invite.
```

--------------------------------

### MessageReference

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents a reference to a Message, used for replies or linking to specific messages.

```APIDOC
## class discord.MessageReference

### Description
Represents a reference to a Message. This class can be constructed by users to create references for replies.

### Constructor
`discord.MessageReference(message_id, channel_id, guild_id=None, fail_if_not_exists=True, type=MessageReferenceType.default)`

### Attributes
- **message_id** (Optional[int]) - The id of the message referenced.
- **channel_id** (int) - The channel id of the message referenced.
- **guild_id** (Optional[int]) - The guild id of the message referenced.
- **fail_if_not_exists** (bool) - Whether to raise HTTPException if the message no longer exists.
- **type** (MessageReferenceType) - The type of message reference.
- **resolved** (Optional[Union[Message, DeletedReferencedMessage]]) - The message that this reference resolved to.
- **jump_url** (str) - A URL that allows the client to jump to the referenced message.

### Methods
#### from_message(message, *, fail_if_not_exists=True, type=MessageReferenceType.default)
Creates a MessageReference from an existing Message object.
```

--------------------------------

### delete_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a message owned by the webhook.

```APIDOC
## delete_message(message_id, thread=None)

### Description
Deletes a message owned by this webhook using its ID.

### Parameters
- **message_id** (int) - Required - The message ID to delete.
- **thread** (Snowflake) - Optional - The thread the webhook message belongs to.
```

--------------------------------

### VoiceClient.move_to

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves the voice client to a different voice channel.

```APIDOC
## await VoiceClient.move_to(channel, *, timeout=30.0)

### Description
Moves the voice client to a different voice channel.

### Parameters
#### Arguments
- **channel** (Optional[abc.Snowflake]) - Required - The channel to move to. Must be a voice channel.

#### Keyword Arguments
- **timeout** (Optional[float]) - Optional - How long to wait for the move to complete.

### Errors
- **asyncio.TimeoutError** - The move did not complete in time, but may still be ongoing.
```

--------------------------------

### AudioSource.read()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Reads 20ms worth of audio data from the source. Subclasses must implement this method to return either Opus encoded data or 16-bit 48KHz stereo PCM.

```APIDOC
## read()

### Description
Reads 20ms worth of audio. Subclasses must implement this. If the audio is complete, returning an empty bytes-like object signals completion.

### Returns
- **bytes** - A bytes-like object representing the PCM or Opus data.
```

--------------------------------

### clear_fields()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes all fields from the embed object. Returns the class instance for method chaining.

```APIDOC
## clear_fields()

### Description
Removes all fields from this embed. This function returns the class instance to allow for fluent-style chaining.
```

--------------------------------

### discord.SelectDefaultValue

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a default value for a select menu, which can be constructed from channels, roles, or users.

```APIDOC
## class discord.SelectDefaultValue(id, type)

### Description
Represents a select menu’s default value. These can be created by users.

### Methods
- **from_channel(channel)**: Creates a SelectDefaultValue with the type set to channel.
- **from_role(role)**: Creates a SelectDefaultValue with the type set to role.
- **from_user(user)**: Creates a SelectDefaultValue with the type set to user.
```

--------------------------------

### SoundEffect.to_file()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the sound effect asset into a File object suitable for sending in messages.

```APIDOC
## await SoundEffect.to_file(*, filename=..., description=None, spoiler=False)

### Description
Converts the asset into a File suitable for sending via abc.Messageable.send().

### Parameters
- **filename** (Optional[str]) - Optional - The filename of the file.
- **description** (Optional[str]) - Optional - The description for the file.
- **spoiler** (bool) - Optional - Whether the file is a spoiler.

### Returns
- **File** - The asset as a file suitable for sending.
```

--------------------------------

### AudioSource.is_opus()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the audio source is already encoded in Opus format.

```APIDOC
## is_opus()

### Description
Checks if the audio source is already encoded in Opus.
```

--------------------------------

### Asset.to_file()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the asset into a File object suitable for sending.

```APIDOC
## await to_file(filename=None, description=None, spoiler=False)

### Description
Converts the asset into a File suitable for sending via abc.Messageable.send().

### Parameters
- **filename** (Optional[str]) - Optional - The filename of the file.
- **description** (Optional[str]) - Optional - The description for the file.
- **spoiler** (bool) - Optional - Whether the file is a spoiler.

### Returns
- **File** - The asset as a file suitable for sending.
```

--------------------------------

### ShardInfo.disconnect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects a specific shard.

```APIDOC
## await ShardInfo.disconnect()

### Description
Disconnects a shard. When this is called, the shard connection will no longer be open. If the shard is already disconnected this does nothing.
```

--------------------------------

### discord.utils.escape_mentions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Escapes everyone, here, role, and user mentions in a string.

```APIDOC
## discord.utils.escape_mentions(text)

### Description
A helper function that escapes everyone, here, role, and user mentions.

### Parameters
- **text** (str) - Required - The text to escape mentions from.

### Returns
- **str** - The text with the mentions removed.
```

--------------------------------

### Attachment.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts an attachment into a file object suitable for sending in a message.

```APIDOC
## Attachment.to_file

### Description
Converts the attachment into a `File` object that can be sent in a message.

### Parameters
- **filename** (Optional[str]) - Optional - The filename to use for the file. If not specified, the original filename is used.
- **description** (Optional[str]) - Optional - The description to use for the file. If not specified, the original description is used.
- **use_cached** (bool) - Optional - Whether to use `proxy_url` rather than `url` when downloading. Useful for accessing attachments after the original message is deleted.
- **spoiler** (bool) - Optional - Whether the file should be marked as a spoiler.

### Returns
- **File** - The attachment as a file object.

### Raises
- **HTTPException** - Downloading the attachment failed.
- **Forbidden** - You do not have permissions to access this attachment.
- **NotFound** - The attachment was deleted.
```

--------------------------------

### ShardInfo.reconnect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects and then reconnects a specific shard.

```APIDOC
## await ShardInfo.reconnect()

### Description
Disconnects and then connects the shard again.
```

--------------------------------

### remove_command(name, /)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a command from the internal list of commands.

```APIDOC
## remove_command(name, /)

### Description
Removes a Command from the internal list of commands. Can also be used to remove aliases.

### Parameters
- **name** (str) - Required - The name of the command to remove.
```

--------------------------------

### AppCommand.delete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the application command.

```APIDOC
## await delete()

### Description
Deletes the application command.

### Raises
- **NotFound** - The application command was not found.
- **Forbidden** - You do not have permission to delete this application command.
- **HTTPException** - Deleting the application command failed.
- **MissingApplicationID** - The client does not have an application ID.
```

--------------------------------

### discord.Attachment.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the attachment into a File object for sending.

```APIDOC
## await discord.Attachment.to_file(*, filename=..., description=..., use_cached=False, spoiler=False)

### Description
Converts the attachment into a File suitable for sending via abc.Messageable.send(). This is a coroutine.

### Parameters
- **filename** (str) - Optional - The filename to use for the file.
- **description** (str) - Optional - The description for the file.
- **use_cached** (bool) - Optional - Whether to use proxy_url rather than url.
- **spoiler** (bool) - Optional - Whether the file should be marked as a spoiler.
```

--------------------------------

### StageInstance.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the stage instance. Requires manage_channels permission.

```APIDOC
## await StageInstance.delete(reason=None)

### Description
Deletes the stage instance. You must have `manage_channels` to do this.

### Parameters
- **reason** (str) - Optional - The reason the stage instance was deleted. Shows up on the audit log.

### Raises
- **Forbidden** - You do not have permissions to delete the stage instance.
- **HTTPException** - Deleting the stage instance failed.
```

--------------------------------

### fetch_stage_instance

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a StageInstance for a specific stage channel ID.

```APIDOC
## await fetch_stage_instance(channel_id)

### Description
Gets a StageInstance for a stage channel id.

### Parameters
- **channel_id** (int) - Required - The stage channel ID.

### Returns
- **StageInstance** - The stage instance from the stage channel ID.

### Raises
- **NotFound** - The stage instance or channel could not be found.
- **HTTPException** - Getting the stage instance failed.
```

--------------------------------

### Restrict Commands via add_command

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Register a command to a specific guild using the add_command method. Avoid combining this with the command decorator to prevent duplicates.

```python
@app_commands.command()
async def ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")


tree.add_command(ping, guild=discord.Object(123456789012345678))
```

--------------------------------

### get_partial_message(message_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a PartialMessage from the message ID without performing an API call.

```APIDOC
## get_partial_message(message_id)

### Description
Creates a PartialMessage from the message ID. This is useful if you want to work with a message and only have its ID without doing an unnecessary API call.

### Parameters
- **message_id** (int) - Required - The message ID to create a partial message for.
```

--------------------------------

### Use Range converter in a command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Restricts numeric or string input to a specific range or length.

```python
@bot.command()
async def range(ctx: commands.Context, value: commands.Range[int, 10, 12]):
    await ctx.send(f"Your value is {value}")
```

--------------------------------

### AppInfo

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents the application information for a bot provided by Discord, containing metadata such as name, owner, and installation settings.

```APIDOC
## AppInfo

### Description
Represents the application info for the bot provided by Discord.

### Attributes
- **id** (int) - The application ID.
- **name** (str) - The application name.
- **owner** (User) - The application owner.
- **team** (Optional[Team]) - The application's team.
- **description** (str) - The application description.
- **bot_public** (bool) - Whether the bot can be invited by anyone.
- **bot_require_code_grant** (bool) - Whether the bot requires the full oauth2 code grant flow.
- **verify_key** (str) - The hex encoded key for verification in interactions.
- **approximate_guild_count** (int) - The approximate count of guilds the bot was added to.
- **approximate_user_install_count** (Optional[int]) - The approximate count of user-level installations.
```

--------------------------------

### welcome_screen()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the guild’s welcome screen.

```APIDOC
## welcome_screen()

### Description
Returns the guild’s welcome screen. Requires `COMMUNITY` feature and `manage_guild` permission.

### Returns
- `WelcomeScreen` - The welcome screen.
```

--------------------------------

### discord.utils.oauth_url

Source: https://discordpy.readthedocs.io/en/latest/api.html

Generates an OAuth2 URL for inviting the bot into guilds.

```APIDOC
## discord.utils.oauth_url

### Description
A helper function that returns the OAuth2 URL for inviting the bot into guilds.

### Parameters
- **client_id** (Union[int, str]) - Required - The client ID for your bot.
- **permissions** (Permissions) - Optional - The permissions you’re requesting.
- **guild** (Snowflake) - Optional - The guild to pre-select in the authorization screen.
- **redirect_uri** (str) - Optional - An optional valid redirect URI.
- **scopes** (Iterable[str]) - Optional - An optional valid list of scopes.
- **disable_guild_select** (bool) - Optional - Whether to disallow the user from changing the guild dropdown.
- **state** (str) - Optional - The state to return after the authorization.
```

--------------------------------

### get_parameter(name)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves a command parameter by its Python identifier name.

```APIDOC
## get_parameter(name)

### Description
Retrieves a parameter by its name. The name must be the Python identifier used in the callback function.

### Parameters
- **name** (str) - Required - The parameter name in the callback function.
```

--------------------------------

### set_footer(text=None, icon_url=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the footer for the embed content. Returns the class instance for chaining.

```APIDOC
### Method
`set_footer(text=None, icon_url=None)`

### Description
Sets the footer for the embed content. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **text** (str) - Optional - The footer text. Can only be up to 2048 characters.
- **icon_url** (str) - Optional - The URL of the footer icon. Only HTTP(S) is supported.
```

--------------------------------

### discord.on_invite_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an Invite is deleted. Requires Intents.invites.

```APIDOC
## discord.on_invite_delete(invite)

### Description
Called when an Invite is deleted. You must have manage_channels to receive this. This requires Intents.invites to be enabled.

### Parameters
- **invite** (Invite) - The invite that was deleted.
```

--------------------------------

### create_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an instant invite for the channel.

```APIDOC
## create_invite(reason=None, max_age=0, max_uses=0, temporary=False, unique=True, target_type=None, target_user=None, target_application_id=None, guest=False)

### Description
Creates an instant invite from a text or voice channel.

### Parameters
- **max_age** (int) - Optional - How long the invite lasts in seconds.
- **max_uses** (int) - Optional - Number of uses allowed.
- **temporary** (bool) - Optional - Whether the invite grants temporary membership.
- **unique** (bool) - Optional - Whether a unique invite URL should be created.
- **reason** (Optional[str]) - Optional - Reason for the audit log.
- **target_type** (Optional[InviteTarget]) - Optional - The type of target for the invite.
- **target_user** (Optional[User]) - Optional - The user whose stream to display.
- **target_application_id** (Optional[int]) - Optional - The ID of the embedded application.
- **guest** (bool) - Optional - Whether the invite is a guest invite.

### Returns
- **Invite** - The created invite object.
```

--------------------------------

### Webhook.remove_attachments

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes specified attachments from a webhook message.

```APIDOC
## remove_attachments(*attachments)

### Description
Removes attachments from the message.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove from the message.

### Returns
- **SyncWebhookMessage** - The newly edited message.

### Raises
- **HTTPException** - Editing the message failed.
- **Forbidden** - Tried to edit a message that isn't yours.
```

--------------------------------

### set_field_at(index, name, value, inline=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Modifies an existing field in the embed object.

```APIDOC
## set_field_at(index, name, value, inline=True)

### Description
Modifies a field in the embed object. The index must point to a valid pre-existing field.

### Parameters
- **index** (int) - Required - The index of the field to modify.
- **name** (str) - Required - The name of the field (up to 256 characters).
- **value** (str) - Required - The value of the field (up to 1024 characters).
- **inline** (bool) - Optional - Whether the field should be displayed inline.
```

--------------------------------

### VoiceChannel.send_sound

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a soundboard sound to the voice channel. Requires speak and use_soundboard permissions.

```APIDOC
## await send_sound(sound)

### Description
Sends a soundboard sound for this channel. This is a coroutine.

### Parameters
- **sound** (Union[SoundboardSound, SoundboardDefaultSound]) - Required - The sound to play.
```

--------------------------------

### discord.utils.escape_markdown

Source: https://discordpy.readthedocs.io/en/latest/api.html

Escapes Discord's markdown characters in a string.

```APIDOC
## discord.utils.escape_markdown(text, *, as_needed=False, ignore_links=True)

### Description
A helper function that escapes Discord's markdown.

### Parameters
- **text** (str) - Required - The text to escape markdown from.
- **as_needed** (bool) - Optional - Whether to escape the markdown characters as needed. Defaults to False.
- **ignore_links** (bool) - Optional - Whether to leave links alone when escaping markdown. Defaults to True.

### Returns
- **str** - The text with the markdown special characters escaped with a slash.
```

--------------------------------

### CategoryChannel.create_voice_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shortcut method to create a VoiceChannel in the category.

```APIDOC
## await create_voice_channel(name, **options)

### Description
A shortcut method to Guild.create_voice_channel() to create a VoiceChannel in the category.

### Returns
- **VoiceChannel** - The channel that was just created.
```

--------------------------------

### Asset.is_animated()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a boolean indicating whether the asset is animated.

```APIDOC
## is_animated()

### Description
Returns whether the asset is animated.

### Returns
- **bool** - True if the asset is animated, False otherwise.
```

--------------------------------

### VoiceChannel.clone

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the current channel, creating a new one with the same properties.

```APIDOC
## await clone(*, name=None, category=None, reason=None)

### Description
Clones this channel. This is a coroutine. Requires manage_channels permission.
```

--------------------------------

### get_stage_instance(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a stage instance from the cache by its ID.

```APIDOC
## get_stage_instance(id)

### Description
Returns a stage instance with the given stage channel ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **StageInstance** (Optional) - The stage instance or None if not found.
```

--------------------------------

### Invite.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Revokes the instant invite. Requires the manage_channels permission.

```APIDOC
## await Invite.delete(reason=None)

### Description
Revokes the instant invite. You must have `manage_channels` permission to perform this action.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this invite, which appears in the audit log.
```

--------------------------------

### Customize FlagConverter Attributes

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Configures custom flag names, default values, and positional flags within a FlagConverter class.

```python
from typing import List


class BanFlags(commands.FlagConverter):
    members: List[discord.Member] = commands.flag(name="member", default=lambda ctx: [])
```

```python
class BanFlags(commands.FlagConverter):
    members: List[discord.Member] = commands.flag(name="member", positional=True, default=lambda ctx: [])
    reason: Optional[str] = None
```

--------------------------------

### CategoryChannel.create_stage_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shortcut method to create a StageChannel in the category.

```APIDOC
## await create_stage_channel(name, **options)

### Description
A shortcut method to Guild.create_stage_channel() to create a StageChannel in the category.

### Returns
- **StageChannel** - The channel that was just created.
```

--------------------------------

### add_field(name, value, inline=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a field to the embed object. Can only be up to 25 fields.

```APIDOC
### Method
`add_field(name, value, inline=True)`

### Description
Adds a field to the embed object. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **name** (str) - Required - The name of the field. Can only be up to 256 characters.
- **value** (str) - Required - The value of the field. Can only be up to 1024 characters.
- **inline** (bool) - Optional - Whether the field should be displayed inline.
```

--------------------------------

### User.mention

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a string that allows you to mention the given user.

```APIDOC
## Property: User.mention

### Description
Returns a string that allows you to mention the given user.

### Return Type
`str`
```

--------------------------------

### Boolean Converter Logic

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Internal logic used by the library to evaluate string inputs as boolean values.

```python
if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
    return True
elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
    return False
```

--------------------------------

### welcome_screen.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the server's welcome screen settings, including description, enabled status, and welcome channels.

```APIDOC
## welcome_screen.edit(description=None, welcome_channels=None, enabled=None, reason=None)

### Description
Edits the welcome screen for the guild. This operation requires appropriate permissions.

### Parameters
- **description** (Optional[str]) - Optional - The welcome screen’s description.
- **welcome_channels** (Optional[List[WelcomeChannel]]) - Optional - The welcome channels, in their respective order.
- **enabled** (Optional[bool]) - Optional - Whether the welcome screen should be displayed.
- **reason** (Optional[str]) - Optional - The reason for editing the welcome screen. Shows up on the audit log.

### Raises
- **HTTPException** - Editing the welcome screen failed.
- **Forbidden** - You don’t have permissions to edit the welcome screen.
- **NotFound** - This welcome screen does not exist.
```

--------------------------------

### remove_listener(func, /, *, name=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a listener from the pool of listeners.

```APIDOC
## remove_listener(func, /, *, name=...)

### Description
Removes a listener from the pool of listeners.

### Parameters
- **func** (Callable) - Required - The function that was used as a listener to remove.
- **name** (str) - Optional - The name of the event to remove.
```

--------------------------------

### remove_field(index)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a field at a specified index from the embed object.

```APIDOC
## remove_field(index)

### Description
Removes a field at a specified index. If the index is invalid or out of bounds, the error is silently swallowed.

### Parameters
- **index** (int) - Required - The index of the field to remove.
```

--------------------------------

### delete_invite(invite, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Revokes an Invite, URL, or ID to an invite.

```APIDOC
## delete_invite(invite, reason=None)

### Description
Revokes an Invite, URL, or ID to an invite. You must have manage_channels in the associated guild to do this.

### Parameters
- **invite** (Union[Invite, str]) - Required - The invite to revoke.
- **reason** (Optional[str]) - Optional - The reason for deleting the invite.
```

--------------------------------

### AutoShardedClient.is_ws_ratelimited

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the websocket connection is currently rate limited. This is useful for determining whether to query members via HTTP or the gateway.

```APIDOC
## is_ws_ratelimited()

### Description
Returns a boolean indicating whether the websocket is currently rate limited. This implementation checks if any of the shards are rate limited.

### Returns
- **bool** - True if the websocket is rate limited, False otherwise.
```

--------------------------------

### VoiceClient.disconnect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects the voice client from the current voice channel.

```APIDOC
## await VoiceClient.disconnect(*, force=False)

### Description
Disconnects this voice client from voice.

### Parameters
#### Keyword Arguments
- **force** (bool) - Optional - Whether to force the disconnection.
```

--------------------------------

### set_author(name, url=None, icon_url=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the author for the embed content.

```APIDOC
### Method
`set_author(name, url=None, icon_url=None)`

### Description
Sets the author for the embed content. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **name** (str) - Required - The name of the author. Can only be up to 256 characters.
- **url** (str) - Optional - The URL for the author.
- **icon_url** (str) - Optional - The URL of the author icon.
```

--------------------------------

### Default Opening Note Format

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

The default string returned by get_opening_note, which instructs users on how to get more information about commands or categories.

```text
Use {prefix}{command_name} [command] for more info on a command.
You can also use {prefix}{command_name} [category] for more info on a category.
```
