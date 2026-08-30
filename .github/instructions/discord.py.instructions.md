### start(*args, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Starts the internal task in the event loop.

```APIDOC
## start(*args, **kwargs)

### Description
Starts the internal task in the event loop.

### Parameters
- **args** (tuple) - Optional - The arguments to use.
- **kwargs** (dict) - Optional - The keyword arguments to use.

### Returns
- **asyncio.Task** - The task that has been created.

### Raises
- **RuntimeError** - A task has already been launched and is running.
```

--------------------------------

### Install discord.py on Windows

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Installation command specifically for Windows environments.

```bash
py -3 -m pip install -U discord.py
```

--------------------------------

### Enable user installation with user_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Indicates that a command should be installed for users. This is verified server-side and is ignored for subcommands.

```python
@app_commands.command()
@app_commands.user_install()
async def my_user_install_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in users by default!")
```

--------------------------------

### Update extension setup function

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Convert synchronous setup functions to asynchronous coroutines to support the new extension loading system.

```python
# before
def setup(bot):
    bot.add_cog(MyCog(bot))


# after
async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

--------------------------------

### Install discord.py via pip

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Standard installation command for the library on Unix-like systems.

```bash
python3 -m pip install -U discord.py
```

--------------------------------

### Client.login

Source: https://discordpy.readthedocs.io/en/latest/api.html

Logs the client in with the specified credentials and triggers the setup hook.

```APIDOC
## await Client.login(token)

### Description
Logs in the client with the specified credentials and calls the setup_hook().

### Parameters
- **token** (str) - Required - The authentication token. Do not prefix this token with anything as the library will do it for you.

### Raises
- **LoginFailure** - The wrong credentials are passed.
- **HTTPException** - An unknown HTTP related error occurred.
```

--------------------------------

### Install discord.py with voice support

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Installs the library with additional dependencies required for voice functionality.

```bash
python3 -m pip install -U discord.py[voice]
```

--------------------------------

### Setup logging without Client.run()

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Initializes logging manually using discord.utils.setup_logging().

```python
import discord

discord.utils.setup_logging()

# or, for example
discord.utils.setup_logging(level=logging.INFO, root=False)
```

--------------------------------

### await start(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Starts the scheduled event by setting its status to active.

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

### Install packages in virtual environment

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Standard pip installation command to be used after activating the virtual environment.

```bash
$ pip install -U discord.py
```

--------------------------------

### Configure installation context with allowed_installs

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Specifies whether a command should be installed in guilds or for users. This is verified server-side and is ignored for subcommands.

```python
@app_commands.command()
@app_commands.allowed_installs(guilds=False, users=True)
async def my_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in users by default!")
```

--------------------------------

### Implement setup_hook in Client

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Shows how to use the setup_hook method by subclassing discord.Client to perform asynchronous setup tasks.

```python
class MyClient(discord.Client):
    async def setup_hook(self):
        print("This is asynchronous!")


client = MyClient()
client.run(TOKEN)
```

--------------------------------

### Client.setup_hook

Source: https://discordpy.readthedocs.io/en/latest/api.html

An asynchronous hook for performing setup tasks after login but before connecting to the websocket.

```APIDOC
## await Client.setup_hook()

### Description
A coroutine to be called to setup the bot. To perform asynchronous setup after the bot is logged in but before it has connected to the Websocket, overwrite this coroutine.
```

--------------------------------

### Edit Welcome Screen Example

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to retrieve channels and emojis to prepare for updating a guild's welcome screen configuration.

```python
rules_channel = guild.get_channel(12345678)
announcements_channel = guild.get_channel(87654321)

custom_emoji = utils.get(guild.emojis, name="loudspeaker")
```

--------------------------------

### @discord.app_commands.user_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates this command should be installed for users.

```APIDOC
## @discord.app_commands.user_install()

### Description
Indicates that the command should be available for user installation. This is verified server-side by Discord.
```

--------------------------------

### Configure Basic Intents

Source: https://discordpy.readthedocs.io/en/latest/intents.html

Example of initializing a bot with specific intents for messages and guilds.

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

### Enable guild installation with guild_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Indicates that a command should be installed in guilds. This is verified server-side and is ignored for subcommands.

```python
@app_commands.command()
@app_commands.guild_install()
async def my_guild_install_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am installed in guilds by default!")
```

--------------------------------

### Example command invocations for Greedy and Optional

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates how the combined Greedy and Optional command can be invoked with varying numbers of arguments.

```text
$ban @Member @Member2 spam bot
$ban @Member @Member2 7 spam bot
$ban @Member spam

```

--------------------------------

### @discord.app_commands.guild_install

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates this command should be installed in guilds.

```APIDOC
## @discord.app_commands.guild_install()

### Description
Indicates that the command should be available for guild installation. This is verified server-side by Discord.
```

--------------------------------

### Client.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Establishes a websocket connection to Discord and starts the event loop.

```APIDOC
## await Client.connect(*, reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord. This is a loop that runs the entire event system and miscellaneous aspects of the library. Control is not resumed until the WebSocket connection is terminated.

### Parameters
- **reconnect** (bool) - Optional - Whether to automatically reconnect if the connection is lost.
```

--------------------------------

### Implement setup and teardown

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

The teardown function is an optional entry point called when an extension is unloaded for cleanup tasks.

```python
async def setup(bot):
    print("I am being loaded!")


async def teardown(bot):
    print("I am being unloaded!")
```

--------------------------------

### Implement a basic discord.py client

Source: https://discordpy.readthedocs.io/en/latest/intro.html

A minimal example demonstrating event handling for bot readiness and incoming messages. Requires the 'message_content' intent to be enabled.

```python
# This example requires the 'message_content' intent.

import discord


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")

    async def on_message(self, message):
        print(f"Message from {message.author}: {message.content}")


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run("my token goes here")
```

--------------------------------

### Start a scheduled event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Starts the scheduled event by setting its status to active.

```python
await event.edit(status=EventStatus.active)
```

--------------------------------

### Initialize UI imports

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Basic imports required to start using discord.ui components.

```python
import discord
from discord import ui
```

--------------------------------

### await fetch_template(code)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Gets a Template from a discord.new URL or code.

```APIDOC
## await fetch_template(code)

### Description
Gets a Template from a discord.new URL or code.

### Parameters
- **code** (Union[Template, str]) - Required - The Discord Template Code or URL.

### Raises
- **NotFound** - The template is invalid.
- **HTTPException** - Getting the template failed.

### Returns
- **Template** - The template from the URL/code.
```

--------------------------------

### @discord.app_commands.allowed_installs

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates this command should be installed in specific contexts (guilds and users).

```APIDOC
## @discord.app_commands.allowed_installs(guilds=..., users=...)

### Description
Specifies the installation contexts for the command. Valid contexts are guilds and users.

### Parameters
- **guilds** (bool) - Optional - Whether the command can be installed in guilds.
- **users** (bool) - Optional - Whether the command can be installed by users.
```

--------------------------------

### connect(reconnect=True)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a websocket connection and starts the event loop to listen to Discord messages.

```APIDOC
## await connect(reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord. This is a loop that runs the entire event system and miscellaneous aspects of the library.

### Parameters
- **reconnect** (bool) - Optional - If we should attempt reconnecting, either due to internet failure or a specific failure on Discord’s part.
```

--------------------------------

### Define an extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

An extension requires a setup coroutine that accepts the bot instance to register commands or cogs.

```python
from discord.ext import commands


@commands.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.display_name}.")


async def setup(bot):
    bot.add_command(hello)
```

--------------------------------

### Initialize multiple daily task times

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

This snippet shows the setup for defining multiple daily execution times.

```python
import datetime
from discord.ext import commands, tasks

utc = datetime.timezone.utc
```

--------------------------------

### Define a LayoutView with a Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Example of subclassing LayoutView to include a container with a text display.

```python
class MyView(ui.LayoutView):
    container = ui.Container(ui.TextDisplay("I am a text display on a container!"))
    # or you can use your subclass:
    # container = MyContainer()
```

--------------------------------

### fetch_session_start_limits()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the session start limits for the application.

```APIDOC
## fetch_session_start_limits()

### Description
Get the session start limits. This is typically handled automatically but can be used for manual sharding management.

### Returns
- **SessionStartLimits** - A class containing the session start limits.

### Raises
- **GatewayNotFound** - The gateway was unreachable.
```

--------------------------------

### Define a LayoutView with a File

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Example of adding a file component to a LayoutView using the attachment URI format.

```python
import discord
from discord import ui


class MyView(ui.LayoutView):
    file = ui.File("attachment://file.txt")
    # attachment://file.txt points to an attachment uploaded alongside this view
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

### Translator.load()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

An asynchronous setup function for loading the translation system. This is invoked when CommandTree.set_translator() is called.

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

### Install voice dependencies on Debian

Source: https://discordpy.readthedocs.io/en/latest/intro.html

System-level dependencies required for voice support on Debian-based Linux distributions.

```bash
$ apt install libffi-dev libnacl-dev python3-dev
```

--------------------------------

### Hybrid Command FlagConverter Interaction

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Examples showing how FlagConverter parameters map to hybrid command arguments and descriptions.

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

```python
class BanFlags(commands.FlagConverter):
    member: discord.Member = commands.flag(description="The member to ban")
    reason: str = commands.flag(description="The reason for the ban")
    days: int = commands.flag(default=1, description="The number of days worth of messages to delete")


@commands.hybrid_command()
async def ban(ctx, *, flags: BanFlags): ...
```

--------------------------------

### Advanced rotating file logging setup

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Configures a RotatingFileHandler with custom formatting and specific log levels for different loggers.

```python
import discord
import logging
import logging.handlers

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Assume client refers to a discord.Client subclass...
# Suppress the default configuration since we have our own
client.run(token, log_handler=None)
```

--------------------------------

### discord.utils.setup_logging

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets up logging for the library, similar to logging.basicConfig but with custom defaults.

```APIDOC
## discord.utils.setup_logging(handler=..., formatter=..., level=..., root=True)

### Description
A helper function to setup logging. This is superficially similar to logging.basicConfig() but uses different defaults and a colour formatter if the stream can display colour.

### Parameters
- **handler** (logging.Handler) - Optional - The log handler to use for the library’s logger.
- **formatter** (logging.Formatter) - Optional - The formatter to use with the given log handler.
- **level** (int) - Optional - The default log level for the library’s logger. Defaults to logging.INFO.
- **root** (bool) - Optional - Whether to set up the root logger rather than the library logger. Defaults to True.
```

--------------------------------

### Wait for bot readiness before starting a loop

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Use the before_loop decorator to execute logic, such as waiting for the bot to be ready, before the task begins its first iteration.

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

### await onboarding()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the onboarding configuration for the guild.

```APIDOC
## await onboarding()

### Description
Fetches the onboarding configuration for this guild.

### Returns
- **Onboarding** - The onboarding configuration that was fetched.
```

--------------------------------

### View.find_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Gets an item with a specific ID.

```APIDOC
## find_item(id, /)

### Description
Gets an item with Item.id set as id, or None if not found.

### Parameters
- **id** (int) - Required - The ID of the component.
```

--------------------------------

### @before_loop

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Decorator that registers a coroutine to be called before the loop starts running.

```APIDOC
## @before_loop

### Description
A decorator that registers a coroutine to be called before the loop starts running. This is useful for waiting for bot state, such as wait_until_ready().

### Parameters
- **coro** (coroutine) - Required - The coroutine to register before the loop runs.

### Raises
- **TypeError** - The function was not a coroutine.
```

--------------------------------

### Create a virtual environment

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Commands to navigate to the project directory and initialize a new virtual environment.

```bash
$ cd your-bot-source
$ python3 -m venv bot-env
```

--------------------------------

### discord.on_audit_log_entry_create(entry)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild gets a new audit log entry. Requires Intents.moderation to be enabled.

```APIDOC
## discord.on_audit_log_entry_create(entry)

### Description
Called when a Guild gets a new audit log entry. You must have view_audit_log to receive this. This requires Intents.moderation to be enabled.

### Parameters
- **entry** (AuditLogEntry) - The audit log entry that was created.
```

--------------------------------

### get_shard(shard_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Gets the shard information at a given shard ID.

```APIDOC
## get_shard(shard_id)

### Description
Gets the shard information at a given shard ID or None if not found.

### Parameters
#### Path Parameters
- **shard_id** (int) - Required - The ID of the shard to retrieve.
```

--------------------------------

### Set channel permissions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Examples for modifying channel-specific permission overwrites using keyword arguments, clearing existing overwrites, or applying a PermissionOverwrite object.

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

### Modal.find_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Gets an item with Item.id set as id, or None if not found.

```APIDOC
## find_item(id)

### Description
Gets an item with Item.id set as id, or None if not found.

### Parameters
- **id** (int) - Required - The ID of the component.

### Returns
- **Optional[Item]** - The item found, or None.
```

--------------------------------

### Migrating extension loading

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates for loading extensions using setup_hook or async context managers.

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

### AppInfo

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents the application information for a bot provided by Discord, including metadata like name, owner, and installation settings.

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
- **rpc_origins** (Optional[List[str]]) - A list of RPC origin URLs.
- **verify_key** (str) - The hex encoded key for verification.
- **guild_id** (Optional[int]) - The linked guild ID if the app is a game.
- **primary_sku_id** (Optional[int]) - The ID of the Game SKU if it exists.
- **slug** (Optional[str]) - The URL slug for the store page.
- **terms_of_service_url** (Optional[str]) - The application's terms of service URL.
- **privacy_policy_url** (Optional[str]) - The application's privacy policy URL.
- **tags** (List[str]) - List of tags describing the application.
- **custom_install_url** (List[str]) - The custom authorization URL.
- **install_params** (Optional[AppInstallParams]) - Settings for custom authorization URL.
- **role_connections_verification_url** (Optional[str]) - The connection verification URL.
- **interactions_endpoint_url** (Optional[str]) - The interactions endpoint URL.
- **redirect_uris** (List[str]) - A list of authentication redirect URIs.
- **approximate_guild_count** (int) - Approximate count of guilds the bot was added to.
- **approximate_user_install_count** (Optional[int]) - Approximate count of user-level installations.
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

### Get sent message ID

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Access the ID of a message after sending it.

```python
message = await channel.send("hmm…")
message_id = message.id
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

### Disable default logging configuration

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Pass None to log_handler to completely disable the library's default logging setup.

```python
client.run(token, log_handler=None)
```

--------------------------------

### Retrieve a single message from history

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Fetch a specific message from channel history using the get method.

```python
my_last_message = await channel.history().get(author=client.user)
```

--------------------------------

### await create_forum(name, *, topic=..., position=..., category=None, slowmode_delay=..., nsfw=..., media=..., overwrites=..., reason=None, default_auto_archive_duration=..., default_thread_slowmode_delay=..., default_sort_order=..., default_reaction_emoji=..., default_layout=..., available_tags=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new ForumChannel within the guild. This is a coroutine.

```APIDOC
## await create_forum(name, *, topic=..., position=..., category=None, slowmode_delay=..., nsfw=..., media=..., overwrites=..., reason=None, default_auto_archive_duration=..., default_thread_slowmode_delay=..., default_sort_order=..., default_reaction_emoji=..., default_layout=..., available_tags=...)

### Description
Creates a new ForumChannel in the guild. The overwrites parameter can be used to create a 'secret' channel upon creation.

### Parameters
- **name** (str) - Required - The channel's name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply upon creation.
- **reason** (str) - Optional - The reason for creating this channel, shown in the audit log.
```

--------------------------------

### Run Client with asyncio.run

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Demonstrates using asyncio.run to manage the event loop instead of the traditional Client.run method.

```python
client = discord.Client()


async def main():
    # do other async things
    await my_async_function()

    # start the client
    async with client:
        await client.start(TOKEN)


asyncio.run(main())
```

--------------------------------

### welcome_screen()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the guild’s welcome screen.

```APIDOC
## welcome_screen()

### Description
Returns the guild’s welcome screen. Requires COMMUNITY feature and manage_guild permission.

### Returns
- **WelcomeScreen** - The welcome screen.
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

### Create and use a webhook from a URL

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates initializing a Webhook object from a URL using an aiohttp session and sending a message.

```python
from discord import Webhook
import aiohttp


async def foo():
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url("url-here", session=session)
        await webhook.send("Hello World", username="Foo")
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

### Update Client Execution Pattern

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates the transition from separate login and run calls to a unified, blocking client.run() call.

```python
client.login("token")
client.run()
```

```python
client.run("token")
```

--------------------------------

### await edit_onboarding(*, prompts=..., default_channels=..., enabled=..., mode=..., reason=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the onboarding configuration for the guild. Requires Permissions.manage_guild and Permissions.manage_roles.

```APIDOC
## await edit_onboarding(*, prompts=..., default_channels=..., enabled=..., mode=..., reason=...)

### Description
Edits the onboarding configuration for this guild. You must have `Permissions.manage_guild` and `Permissions.manage_roles` to do this.

### Parameters
- **prompts** (List[OnboardingPrompt]) - Optional - The prompts that will be shown to new members.
- **default_channels** (List[abc.Snowflake]) - Optional - The channels that will be used as the default channels for new members.
- **enabled** (bool) - Optional - Whether the onboarding configuration is enabled.
- **mode** (OnboardingMode) - Optional - The mode that will be used for the onboarding configuration.
- **reason** (str) - Optional - The reason for editing the onboarding configuration.

### Returns
- **Onboarding** - The new onboarding configuration.
```

--------------------------------

### Create a simple background task in a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Use the @tasks.loop decorator to define a recurring task within a Cog, ensuring it is started in the constructor and cancelled during cog_unload.

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

### Use and configure built-in converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows how to use the clean_content converter with default settings or custom configuration.

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

### Get element in iterable with discord.utils.get

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the first element in an iterable matching all provided keyword attributes. Supports nested attribute lookups using double underscores.

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

### discord.FFmpegOpusAudio.from_probe

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an FFmpegOpusAudio instance by probing the input source for bitrate and codec information.

```APIDOC
## discord.FFmpegOpusAudio.from_probe

### Description
Creates an instance of FFmpegOpusAudio by probing the provided source. This method allows specifying a probing method such as 'native' or 'fallback', or a custom callable.

### Parameters
- **source** (str) - Required - The input source to probe.
- **method** (Optional[Union[str, Callable]]) - Optional - The probing method. Valid strings are 'native' or 'fallback'.
- **kwargs** (dict) - Optional - Additional parameters passed to the FFmpegOpusAudio constructor.

### Returns
- **FFmpegOpusAudio** - An instance of the class.
```

--------------------------------

### Transitioning to Coroutines

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates the change from direct function calls to using yield from or await for coroutines.

```python
client.send_message(message.channel, "Hello")
```

```python
yield from client.send_message(message.channel, "Hello")

# or in python 3.5+
await client.send_message(message.channel, "Hello")
```

--------------------------------

### Registering a command manually

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates how to define a command function and add it to the bot instance manually.

```python
@commands.command()
async def test(ctx):
    pass


bot.add_command(test)
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

### WelcomeScreen.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the welcome screen configuration.

```APIDOC
## WelcomeScreen.edit(*, description=..., welcome_channels=..., enabled=..., reason=None)

### Description
Edit the welcome screen. Requires `manage_guild` permission in the guild.

### Parameters
- **description** (str) - Optional - The description shown on the welcome screen.
- **welcome_channels** (List[WelcomeChannel]) - Optional - The channels shown on the welcome screen.
- **enabled** (bool) - Optional - Whether the welcome screen is displayed.
- **reason** (str) - Optional - The reason for the edit.
```

--------------------------------

### Implement a Channel Select Menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates using the @discord.ui.select decorator to create a channel selection menu within a View.

```python
class View(discord.ui.View):
    @discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f"You selected {select.values[0].mention}")
```

--------------------------------

### Using multiple positional arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates accepting multiple positional arguments in a command.

```python
@bot.command()
async def test(ctx, arg1, arg2):
    await ctx.send(f"You passed {arg1} and {arg2}")
```

--------------------------------

### StageChannel.create_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an instant invite from the channel. Requires create_instant_invite permission.

```APIDOC
## await create_invite(reason=None, max_age=0, max_uses=0, temporary=False, unique=True, target_type=None, target_user=None, target_application_id=None, guest=False)

### Description
Creates an instant invite from a text or voice channel.

### Parameters
- **max_age** (int) - Optional - How long the invite should last in seconds.
- **max_uses** (int) - Optional - How many uses the invite could be used for.
- **temporary** (bool) - Optional - Denotes that the invite grants temporary membership.
- **unique** (bool) - Optional - Indicates if a unique invite URL should be created.
- **reason** (Optional[str]) - Optional - The reason for creating this invite.
- **target_type** (Optional[InviteTarget]) - Optional - The type of target for the voice channel invite.
- **target_user** (Optional[User]) - Optional - The user whose stream to display for this invite.
- **target_application_id** (Optional[int]) - Optional - The id of the embedded application for the invite.
- **guest** (bool) - Optional - Whether the invite is a guest invite.

### Returns
- **Invite** - The invite that was created.
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

### Subclassing and Using ActionRow

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates how to subclass ActionRow to add components via decorators or use it directly within a LayoutView.

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

### create_soundboard_sound()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a SoundboardSound for the guild. Requires Permissions.create_expressions.

```APIDOC
## create_soundboard_sound(name, sound, volume=1, emoji=None, reason=None)

### Description
Creates a `SoundboardSound` for the guild. Requires `Permissions.create_expressions`.

### Parameters
- **name** (str) - Required - The name of the sound.
- **sound** (bytes) - Required - The bytes-like object representing the sound data.
- **volume** (float) - Optional - The volume of the sound. Defaults to 1.
- **emoji** (Optional[Union[Emoji, PartialEmoji, str]]) - Optional - The emoji of the sound.
- **reason** (Optional[str]) - Optional - The reason for creating the sound.

### Returns
- **SoundboardSound** - The newly created soundboard sound.
```

--------------------------------

### welcome_screen.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the server's welcome screen settings, including description, enabled status, and welcome channels.

```APIDOC
## Method: welcome_screen.edit

### Description
Edits the welcome screen of a guild. This allows updating the description, the list of welcome channels, and the enabled status.

### Parameters
- **description** (str) - Optional - The welcome screen’s description.
- **welcome_channels** (List[WelcomeChannel]) - Optional - The welcome channels, in their respective order.
- **enabled** (bool) - Optional - Whether the welcome screen should be displayed.
- **reason** (str) - Optional - The reason for editing the welcome screen. Shows up on the audit log.

### Raises
- **HTTPException** - Editing the welcome screen failed.
- **Forbidden** - You don’t have permissions to edit the welcome screen.
- **NotFound** - This welcome screen does not exist.
```

--------------------------------

### Implement a custom HelpCommand within a Cog

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates how to subclass MinimalHelpCommand and bind it to a Cog, ensuring the original help command is restored upon unloading.

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

### Probe audio source with fallback method

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use the fallback method to probe audio using ffmpeg when ffprobe is unavailable on Windows.

```python
source = await discord.FFmpegOpusAudio.from_probe("song.webm", method="fallback")
voice_client.play(source)
```

--------------------------------

### Default Opening Note Format

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

The default string returned by get_opening_note, which provides instructions on how to use the help command.

```text
Use {prefix}{command_name} [command] for more info on a command.
You can also use {prefix}{command_name} [category] for more info on a category.
```

--------------------------------

### Edit a Welcome Screen

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the welcome screen description and channels. Requires appropriate permissions and may raise HTTPException, Forbidden, or NotFound exceptions.

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

### Registering Events with asyncio

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Demonstrates the transition from standard functions to coroutines for event registration.

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

### Define a basic command converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates a simple command using a custom converter class.

```python
@bot.command()
async def slap(ctx, *, reason: Slapper()):
    await ctx.send(reason)
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

### SyncWebhook.partial

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial SyncWebhook object using an ID and token.

```APIDOC
## SyncWebhook.partial

### Description
Creates a partial `SyncWebhook` object. A partial webhook contains only the ID and token, and can be used to perform operations if the token is valid.

### Parameters
- **id** (int) - Required - The ID of the webhook.
- **token** (str) - Required - The authentication token of the webhook.
- **session** (requests.Session) - Optional - The session to use for requests.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.

### Returns
- **SyncWebhook** - A partial `SyncWebhook` instance.
```

--------------------------------

### Migrate channel history iteration

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replace manual iterator loops with the async for syntax.

```python
# before
it = channel.history()
while True:
    try:
        message = await self.next()
    except discord.NoMoreItems:
        break
    print(f"Found message with ID {message.id}")

# after
async for message in channel.history():
    print(f"Found message with ID {message.id}")
```

--------------------------------

### run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A blocking call that abstracts away the event loop initialization and sets up logging.

```APIDOC
## run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

### Description
A blocking call that abstracts away the event loop initialisation. This function must be the last function to call as it is blocking.

### Parameters
- **token** (str) - Required - The authentication token.
- **reconnect** (bool) - Optional - If we should attempt reconnecting.
- **log_handler** (Optional[logging.Handler]) - Optional - The log handler to use.
- **log_formatter** (logging.Formatter) - Optional - The formatter to use with the log handler.
- **log_level** (int) - Optional - The default log level.
- **root_logger** (bool) - Optional - Whether to set up the root logger.
```

--------------------------------

### edit_welcome_screen(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shorthand method to edit the guild's welcome screen.

```APIDOC
## edit_welcome_screen(**kwargs)

### Description
A shorthand method of WelcomeScreen.edit without needing to fetch the welcome screen beforehand.

### Returns
- **WelcomeScreen** - The edited welcome screen.
```

--------------------------------

### create_guild(name, icon=..., code=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a new Guild.

```APIDOC
## await create_guild(name, icon=..., code=...)

### Description
Creates a Guild. Bot accounts in more than 10 guilds are not allowed to create guilds.

### Parameters
- **name** (str) - Required - The name of the guild.
- **icon** (Optional[bytes]) - Optional - The bytes-like object representing the icon.
- **code** (str) - Optional - The code for a template to create the guild with.

### Returns
- **Guild** - The guild created.
```

--------------------------------

### Attach a ChannelSelect menu to a LayoutView

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates using the select decorator to filter for text channels and respond with the selected channel's mention.

```python
class MyView(discord.ui.LayoutView):
    action_row = discord.ui.ActionRow()

    @action_row.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f"You selected {select.values[0].mention}")
```

--------------------------------

### Registering Events via Subclassing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to register event handlers by subclassing discord.Client and defining coroutines for specific events.

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

### Create a minimal discord.py bot

Source: https://discordpy.readthedocs.io/en/latest/quickstart.html

Initializes a discord.py client with message content intents and defines basic event handlers for ready and message events.

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

### Migrate voice connection and playback

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Voice operations now use VoiceChannel.connect and play AudioSource objects directly.

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

### create_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an instant invite for the channel.

```APIDOC
## create_invite(reason=None, max_age=0, max_uses=0, temporary=False, unique=True, target_type=None, target_user=None, target_application_id=None, guest=False)

### Description
Creates an instant invite from a text or voice channel. Requires create_instant_invite permission.

### Parameters
- **max_age** (int) - Optional - Duration in seconds before expiry.
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

### application_info()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the bot’s application information.

```APIDOC
## application_info()

### Description
Retrieves the bot’s application information.

### Returns
- **AppInfo** - The bot’s application information.

### Raises
- **HTTPException** - Retrieving the information failed somehow.
```

--------------------------------

### Implement Custom Member Converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows how to create a custom converter by inheriting from an existing one, in this case to extract a list of member role names.

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

### invites()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all active instant invites from the channel. Requires manage_channels permission.

```APIDOC
## invites()

### Description
Retrieves a list of all active instant invites from the channel. Requires manage_channels permission.

### Returns
- **List[Invite]** - The list of invites that are currently active.
```

--------------------------------

### SyncWebhook.from_url

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial SyncWebhook from a provided webhook URL.

```APIDOC
## SyncWebhook.from_url

### Description
Creates a partial `SyncWebhook` instance by parsing a standard Discord webhook URL.

### Parameters
- **url** (str) - Required - The URL of the webhook.
- **session** (requests.Session) - Optional - The session to use for requests.
- **bot_token** (Optional[str]) - Optional - The bot authentication token.

### Returns
- **SyncWebhook** - A partial `SyncWebhook` instance.

### Errors
- **ValueError** - Raised if the provided URL is invalid.
```

--------------------------------

### Define a basic command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands are defined by decorating a function with @bot.command(). The first parameter must always be the context object.

```python
@bot.command()
async def foo(ctx, arg):
    await ctx.send(arg)
```

--------------------------------

### launch_activity

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by launching the activity associated with the app.

```APIDOC
## await launch_activity()

### Description
Responds to this interaction by launching the activity associated with the app. Only available for apps with activities enabled.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### Configure logging with a FileHandler

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Directs logs to a file instead of stderr by passing a FileHandler to Client.run().

```python
import logging

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# Assume client refers to a discord.Client subclass...
client.run(token, log_handler=handler)
```

--------------------------------

### discord.on_integration_create(integration)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is created. Requires Intents.integrations to be enabled.

```APIDOC
## discord.on_integration_create(integration)

### Description
Called when an integration is created. This requires Intents.integrations to be enabled.

### Parameters
- **integration** (Integration) - The integration that was created.
```

--------------------------------

### await send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination. The content must be convertible to a string, or an embed must be provided.

```APIDOC
## await send(...)

### Description
Sends a message to the destination. If content is None, an embed must be provided. You cannot specify both single and list versions of files or embeds simultaneously.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message.
- **tts** (bool) - Optional - Whether to use text-to-speech.
- **embed** (Embed) - Optional - A single rich embed.
- **embeds** (List[Embed]) - Optional - A list of up to 10 embeds.
- **file** (File) - Optional - A single file to upload.
- **files** (List[File]) - Optional - A list of up to 10 files to upload.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of up to 3 stickers.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **nonce** (int) - Optional - The nonce for the message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls mention processing.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to a message to reply to.
- **mention_author** (Optional[bool]) - Optional - Overrides the replied_user attribute.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds.
- **silent** (bool) - Optional - Whether to suppress notifications.
- **poll** (Poll) - Optional - A poll to send.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### Manual Event Loop Management

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Shows how to manually control the event loop using asyncio instead of the blocking client.run() utility.

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

### Set client activity

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Configure the client's activity status.

```python
activity = discord.Activity(name="my activity", type=discord.ActivityType.watching)
client = discord.Client(activity=activity)
```

--------------------------------

### Initialize AutoShardedClient

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Replaces standard Client with AutoShardedClient for automatic sharding.

```python
client = discord.AutoShardedClient()
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

### Raises
- **LoginFailure** - The wrong credentials are passed.
- **HTTPException** - An unknown HTTP related error occurred.
```

--------------------------------

### Activate a virtual environment

Source: https://discordpy.readthedocs.io/en/latest/intro.html

Commands to activate the virtual environment on Unix and Windows systems.

```bash
$ source bot-env/bin/activate
```

```bash
$ bot-env\Scripts\activate.bat
```

--------------------------------

### Using Client.async_event Decorator

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Simplifies coroutine registration by using the provided utility decorator.

```python
@client.async_event
def on_message(message):
    pass
```

--------------------------------

### Describe Command Parameters

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Provides descriptions for command parameters using decorators or docstrings.

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

### Probe audio source with custom method

Source: https://discordpy.readthedocs.io/en/latest/api.html

Define a custom callable to determine codec and bitrate for an audio source.

```python
def custom_probe(source, executable):
    # some analysis code here
    return codec, bitrate


source = await discord.FFmpegOpusAudio.from_probe("song.webm", method=custom_probe)
voice_client.play(source)
```

--------------------------------

### FFmpegOpusAudio.from_probe

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine factory method that creates an FFmpegOpusAudio instance by probing the input source for codec and bitrate information.

```APIDOC
## FFmpegOpusAudio.from_probe

### Description
A factory method that creates a `FFmpegOpusAudio` after probing the input source for audio codec and bitrate information. This is a coroutine.

### Parameters
- **source** (Union[str, io.BufferedIOBase]) - Required - The input source to probe.
- **method** (Optional[str]) - Optional - The probing method.
- **kwargs** (dict) - Optional - Additional arguments passed to the constructor.

### Example
```python
source = await discord.FFmpegOpusAudio.from_probe("song.webm")
voice_client.play(source)
```
```

--------------------------------

### Integration.sync

Source: https://discordpy.readthedocs.io/en/latest/api.html

Syncs the integration. Requires the manage_guild permission.

```APIDOC
## [COROUTINE] Integration.sync

### Description
Syncs the integration. You must have `manage_guild` to do this.

### Raises
- **Forbidden** - You do not have permission to sync the integration.
- **HTTPException** - Syncing the integration failed.
```

--------------------------------

### create_webhook(name, avatar=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new webhook for the forum channel. Requires manage_webhooks permission.

```APIDOC
## create_webhook(name, avatar=None, reason=None)

### Description
Creates a webhook for this channel. You must have `manage_webhooks` to do this.

### Parameters
- **name** (str) - Required - The webhook’s name.
- **avatar** (Optional[bytes]) - Optional - A bytes-like object representing the webhook’s default avatar.
- **reason** (Optional[str]) - Optional - The reason for creating this webhook. Shows up in the audit logs.

### Returns
- **Webhook** - The created webhook.

### Raises
- **HTTPException** - Creating the webhook failed.
- **Forbidden** - You do not have permissions to create a webhook.
```

--------------------------------

### discord.on_invite_create(invite)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an Invite is created. Requires Intents.invites to be enabled.

```APIDOC
## discord.on_invite_create(invite)

### Description
Called when an Invite is created. You must have manage_channels to receive this. This requires Intents.invites to be enabled.

### Parameters
- **invite** (Invite) - The invite that was created.
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

### clone(*, name=None, category=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a copy of the current forum channel. Requires manage_channels permission.

```APIDOC
### Method
await clone(*, name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. You must have manage_channels to do this.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel.

### Returns
- abc.GuildChannel - The channel that was created.
```

--------------------------------

### User.create_dm()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a DMChannel with the user. This is a coroutine.

```APIDOC
## await User.create_dm()

### Description
Creates a DMChannel with this user. This should be rarely called, as this is done transparently for most people.

### Returns
- **DMChannel** - The channel that was created.
```

--------------------------------

### Client Constructor

Source: https://discordpy.readthedocs.io/en/latest/api.html

The Client class is the main entry point for interacting with the Discord API. It accepts various configuration parameters to manage caching, proxy settings, intents, and connection timeouts.

```APIDOC
## Client Constructor

### Description
Initializes the discord.py Client instance with specific configuration for gateway connections, caching, and event handling.

### Parameters
- **max_messages** (int) - Optional - Maximum number of messages to store in the internal cache. Defaults to 1000.
- **proxy** (str) - Optional - Proxy URL.
- **proxy_auth** (aiohttp.BasicAuth) - Optional - Proxy HTTP Basic Authorization object.
- **shard_id** (int) - Optional - Integer starting at 0 and less than shard_count.
- **shard_count** (int) - Optional - Total number of shards.
- **application_id** (int) - Required - The client’s application ID.
- **intents** (Intents) - Required - The intents to enable for the session.
- **member_cache_flags** (MemberCacheFlags) - Optional - Control over how the library caches members.
- **chunk_guilds_at_startup** (bool) - Optional - Whether to delay on_ready() to chunk guilds at start-up.
- **status** (Status) - Optional - Initial presence status.
- **activity** (BaseActivity) - Optional - Initial presence activity.
- **allowed_mentions** (AllowedMentions) - Optional - Default mention handling settings.
- **heartbeat_timeout** (float) - Required - Seconds before timing out the WebSocket if no HEARTBEAT_ACK is received.
- **guild_ready_timeout** (float) - Required - Seconds to wait for GUILD_CREATE stream before firing READY.
- **assume_unsync_clock** (bool) - Required - Whether to assume the system clock is unsynced for rate limit handling.
- **enable_debug_events** (bool) - Required - Whether to enable raw socket receive/send events.
- **enable_raw_presences** (bool) - Required - Whether to enable on_raw_presence_update event.
- **http_trace** (aiohttp.TraceConfig) - Required - Trace configuration for tracking HTTP requests.
- **max_ratelimit_timeout** (float) - Optional - Maximum seconds to wait for non-global rate limits.
- **connector** (aiohttp.BaseConnector) - Optional - aiohttp connector for underlying network control.
```

--------------------------------

### connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects to the voice channel and returns a VoiceClient.

```APIDOC
## await connect(timeout=30.0, reconnect=True, cls=VoiceClient, self_deaf=False, self_mute=False)

### Description
Connects to voice and creates a VoiceClient to establish your connection to the voice server. This requires voice_states.

### Parameters
- **timeout** (float) - Optional - The timeout in seconds to wait the connection to complete.
- **reconnect** (bool) - Optional - Whether the bot should automatically attempt a reconnect if a part of the handshake fails or the gateway goes down.
- **cls** (Type[VoiceProtocol]) - Optional - A type that subclasses VoiceProtocol to connect with.
- **self_mute** (bool) - Optional - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Optional - Indicates if the client should be self-deafened.

### Returns
- **VoiceProtocol** - A voice client that is fully connected to the voice server.
```

--------------------------------

### Subclassing Context

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Custom context classes can be defined by inheriting from commands.Context.

```python
class MyContext(commands.Context):
    @property
    def secret(self):
        return "my secret here"
```

--------------------------------

### Invoke a command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands are invoked by the user using the configured prefix followed by the command name and arguments.

```text
$foo abc
```

--------------------------------

### fetch_commands(guild=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches all of the application's current commands, either globally or for a specific guild.

```APIDOC
## fetch_commands(guild=None)

### Description
Fetches the application's current commands. This is a coroutine.

### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to fetch the commands from. If not passed, global commands are fetched.

### Returns
- **List[AppCommand]** - The application's commands.

### Raises
- **HTTPException** - Fetching the commands failed.
- **MissingApplicationID** - The application ID could not be found.
```

--------------------------------

### fetch_guild_preview

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a preview of a guild.

```APIDOC
## fetch_guild_preview(guild_id)

### Description
Retrieves a preview of a `Guild` from an ID. If the guild is discoverable, you don’t have to be a member of it.

### Parameters
- **guild_id** (int) - Required - The guild’s ID to fetch from.
```

--------------------------------

### Asset.save(fp, *, seek_begin=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the asset into a file-like object.

```APIDOC
## await Asset.save(fp, *, seek_begin=True)

### Description
Saves this asset into a file-like object.

### Parameters
- **fp** (Union[io.BufferedIOBase, os.PathLike]) - Required - The file-like object to save this asset to or the filename to use.
- **seek_begin** (bool) - Optional - Whether to seek to the beginning of the file after saving is successfully done.

### Returns
- **int** - The number of bytes written.

### Raises
- **DiscordException** - There was no internal connection state.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
```

--------------------------------

### Simplified Parameter Defaults

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses built-in parameter shortcuts like Author to simplify command definitions.

```python
@bot.command()
async def wave(ctx, to: discord.User = commands.Author):
    await ctx.send(f"Hello {to.mention} :wave:")
```

--------------------------------

### create_webhook(name, avatar, reason)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new webhook for the channel.

```APIDOC
## create_webhook(name, avatar, reason)

### Description
Creates a webhook for this channel. Requires manage_webhooks permission.

### Parameters
- **name** (str) - Required - The webhook’s name.
- **avatar** (bytes) - Optional - A bytes-like object representing the webhook’s default avatar.
- **reason** (str) - Optional - The reason for creating this webhook.

### Returns
- Webhook - The created webhook.
```

--------------------------------

### StageChannel.create_webhook

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a webhook for this channel. Requires manage_webhooks permission.

```APIDOC
## await create_webhook(name, avatar=None, reason=None)

### Description
Creates a webhook for this channel.

### Parameters
- **name** (str) - Required - The webhook’s name.
- **avatar** (Optional[bytes]) - Optional - A bytes-like object representing the webhook’s default avatar.
- **reason** (Optional[str]) - Optional - The reason for creating this webhook.

### Returns
- **Webhook** - The created webhook.
```

--------------------------------

### @discord.app_commands.context_menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Creates an application command context menu from a regular function. The function must accept an Interaction as the first parameter and a Member, User, or Message as the second.

```APIDOC
## @discord.app_commands.context_menu(name=..., nsfw=False, auto_locale_strings=True, extras=...)

### Description
Creates an application command context menu from a regular function.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the context menu command.
- **nsfw** (bool) - Optional - Whether the command is NSFW and should only work in NSFW channels. Defaults to False.
- **auto_locale_strings** (bool) - Optional - If True, translatable strings are implicitly wrapped into locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary to store extraneous data.
```

--------------------------------

### @discord.app_commands.describe

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Describes the given parameters by their name using the key of the keyword argument as the name.

```APIDOC
## @discord.app_commands.describe(**parameters)

### Description
Describes the given parameters by their name using the key of the keyword argument as the name.

### Parameters
- **parameters** (Union[str, locale_str]) - Required - The description of the parameters.
```

--------------------------------

### Configure Bot Prefix with when_mentioned_or

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Sets the bot's command prefix to include mentions and a custom string.

```python
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"))
```

--------------------------------

### Set default command permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Sets a hint for default permissions required to execute a command. Administrators can override these settings in the client, and it does not function as a strict check.

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

### add_view(view, *, message_id=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a View for persistent listening.

```APIDOC
## add_view(view, *, message_id=None)

### Description
Registers a View for persistent listening. This method should be used for when a view is comprised of components that last longer than the lifecycle of the program.

### Parameters
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Required - The view to register for dispatching.
- **message_id** (Optional[int]) - Optional - The message ID that the view is attached to.

### Raises
- **TypeError** - A view was not passed.
- **ValueError** - The view is not persistent or is already finished.
```

--------------------------------

### Extend a command check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates how to wrap an existing check to add custom logic, such as allowing the guild owner to bypass permissions.

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

### fetch_soundboard_sounds()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all soundboard sounds for the guild.

```APIDOC
## fetch_soundboard_sounds()

### Description
Retrieves a list of all soundboard sounds for the guild.

### Returns
- **List[SoundboardSound]** - The retrieved soundboard sounds.
```

--------------------------------

### Combining Multiple Checks

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates applying multiple checks to a single command, where all must pass for execution.

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

### SyncWebhook.fetch

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the current state of the webhook from Discord.

```APIDOC
## SyncWebhook.fetch

### Description
Fetches the full webhook data from Discord. Useful for converting a partial webhook into a full one.

### Parameters
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.

### Returns
- **SyncWebhook** - The fully populated webhook object.

### Errors
- **HTTPException** - Could not fetch the webhook.
- **NotFound** - Could not find the webhook by this ID.
- **ValueError** - The webhook does not have a token associated with it.
```

--------------------------------

### Annotating Parameters with Converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates how to use a custom converter with a command parameter, which can cause type checker issues.

```python
class SomeType:
    foo: int


class MyVeryCoolConverter(commands.Converter[SomeType]): ...  # implementation left as an exercise for the reader


@bot.command()
async def bar(ctx, cool_value: MyVeryCoolConverter):
    cool_value.foo  # type checker warns MyVeryCoolConverter has no value foo (uh-oh)
```

--------------------------------

### Webhook.partial

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a partial Webhook object using an ID and token.

```APIDOC
## Webhook.partial(id, token, *, session=..., client=..., bot_token=None)

### Description
Creates a partial Webhook object using the webhook ID and authentication token.

### Parameters
- **id** (int) - Required - The ID of the webhook.
- **token** (str) - Required - The authentication token of the webhook.
- **session** (aiohttp.ClientSession) - Optional - The session to use to send requests with.
- **client** (Client) - Optional - The client to initialise this webhook with.
- **bot_token** (Optional[str]) - Optional - The bot authentication token for authenticated requests.

### Returns
- **Webhook** - A partial webhook object.
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

### Asset.to_file(*, filename=..., description=None, spoiler=False)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the asset into a File object suitable for sending via messages.

```APIDOC
## await Asset.to_file(*, filename=..., description=None, spoiler=False)

### Description
Converts the asset into a `File` suitable for sending via `abc.Messageable.send()`.

### Parameters
- **filename** (Optional[str]) - Optional - The filename of the file.
- **description** (Optional[str]) - Optional - The description for the file.
- **spoiler** (bool) - Optional - Whether the file is a spoiler.

### Returns
- **File** - The asset as a file suitable for sending.

### Raises
- **DiscordException** - The asset does not have an associated state.
- **ValueError** - The asset is a unicode emoji.
- **TypeError** - The asset is a sticker with lottie type.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
```

--------------------------------

### await create_category(name, *, overwrites=..., reason=None, position=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new CategoryChannel within the guild. This is a coroutine.

```APIDOC
## await create_category(name, *, overwrites=..., reason=None, position=...)

### Description
Creates a new CategoryChannel in the guild. Note that the category parameter is not supported as categories cannot contain other categories.

### Parameters
- **name** (str) - Required - The channel's name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite to apply upon creation.
- **reason** (str) - Optional - The reason for creating this channel, shown in the audit log.
- **position** (int) - Optional - The position in the channel list.

### Returns
- **CategoryChannel** - The channel that was just created.

### Raises
- **Forbidden** - Insufficient permissions to create the channel.
- **HTTPException** - Creating the channel failed.
- **TypeError** - Permission overwrite information is not in proper form.
```

--------------------------------

### Set channel permissions with allow and deny

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets channel-specific permissions for a member using keyword arguments for permission attributes.

```python
await message.channel.set_permissions(message.author, read_messages=True, send_messages=False)
```

--------------------------------

### Connectable.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects to voice and creates a VoiceClient to establish a connection to the voice server.

```APIDOC
## await connect(timeout=30.0, reconnect=True, cls=VoiceClient, self_deaf=False, self_mute=False)

### Description
Connects to voice and creates a `VoiceClient` to establish your connection to the voice server. This requires `voice_states`.

### Parameters
- **timeout** (float) - Optional - The timeout in seconds to wait for the connection to complete.
- **reconnect** (bool) - Optional - Whether the bot should automatically attempt a reconnect if a part of the handshake fails.
- **cls** (Type[VoiceProtocol]) - Optional - A type that subclasses `VoiceProtocol` to connect with.
- **self_mute** (bool) - Optional - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Optional - Indicates if the client should be self-deafened.

### Returns
- **VoiceProtocol** - A voice client that is fully connected to the voice server.

### Raises
- **asyncio.TimeoutError** - Could not connect to the voice channel in time.
- **ClientException** - You are already connected to a voice channel.
- **OpusNotLoaded** - The opus library has not been loaded.
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

### Errors
- **Forbidden**: You do not have permission to create the integration.
- **HTTPException**: The account could not be found.
```

--------------------------------

### PCMAudio

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents a raw 16-bit 48KHz stereo PCM audio source.

```APIDOC
## class discord.PCMAudio(stream)

### Description
Represents raw 16-bit 48KHz stereo PCM audio source.

### Attributes
- **stream** (file object) - A file-like object that reads byte data representing raw PCM.
```

--------------------------------

### Creating a Custom Command Check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Demonstrates defining a predicate function to restrict command access and applying it as a decorator.

```python
def check_if_it_is_me(interaction: discord.Interaction) -> bool:
    return interaction.user.id == 85309593344815104


@tree.command()
@app_commands.check(check_if_it_is_me)
async def only_for_me(interaction: discord.Interaction):
    await interaction.response.send_message("I know you!", ephemeral=True)
```

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

### discord.app_commands.Choice

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents an application command argument choice.

```APIDOC
## class discord.app_commands.Choice(name, value)

### Description
Represents an application command argument choice.

### Parameters
- **name** (Union[str, locale_str]) - Required - The name of the choice for display purposes (up to 100 characters).
- **name_localizations** (Dict[Locale, str]) - Optional - The localised names of the choice.
- **value** (Union[int, str, float]) - Required - The value of the choice (string values up to 100 characters).
```

--------------------------------

### Send Typing Indicator in a Channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates using the typing context manager for long-running tasks and the awaitable typing method for a fixed duration.

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

### typing()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination.

```APIDOC
## typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is called using await.
```

--------------------------------

### Create a text channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel in the guild. Requires the manage_channels permission.

```python
channel = await guild.create_text_channel("cool-channel")
```

```python
overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True)}

channel = await guild.create_text_channel("secret", overwrites=overwrites)
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
- **Template** - The created template object.
```

--------------------------------

### connect(reconnect=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a websocket connection to Discord.

```APIDOC
## connect(reconnect=True)

### Description
Creates a websocket connection and lets the websocket listen to messages from Discord.

### Parameters
- **reconnect** (bool) - Optional - If the client should attempt reconnecting on failure.

### Raises
- **GatewayNotFound** - If the gateway to connect to Discord is not found.
- **ConnectionClosed** - The websocket connection has been terminated.
```

--------------------------------

### Template.create_guild

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new Guild using the template.

```APIDOC
## Template.create_guild(name, icon=...)

### Description
Creates a `Guild` using the template. Note that bot accounts in more than 10 guilds are not allowed to create guilds.

### Parameters
- **name** (str) - Required - The name of the guild.
- **icon** (bytes) - Optional - The bytes-like object representing the icon.

### Returns
- **Guild** - The guild created.
```

--------------------------------

### @discord.app_commands.choices

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Instructs the given parameters by their name to use the provided choices.

```APIDOC
## @discord.app_commands.choices(**parameters)

### Description
Instructs the given parameters by their name to use the given choices for their choices.

### Parameters
- **parameters** (Any) - Required - The choices of the parameters.
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

### Run the bot script

Source: https://discordpy.readthedocs.io/en/latest/quickstart.html

Commands to execute the bot script from the terminal on different operating systems.

```bash
$ py -3 example_bot.py
```

```bash
$ python3 example_bot.py
```

--------------------------------

### await publish()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Publishes the message to the channel's followers.

```APIDOC
## await publish()

### Description
Publishes this message to the channel's followers. Must be in a news channel and requires `send_messages` permission (and `manage_messages` if not your own).
```

--------------------------------

### Migrate AsyncIterator.get()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use discord.utils.get to retrieve items from an iterator.

```python
# before
msg = await channel.history().get(author__name="Dave")

# after
msg = await discord.utils.get(channel.history(), author__name="Dave")
```

--------------------------------

### fetch(prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches the current webhook. This is a coroutine used to retrieve a full webhook object from a partial one.

```APIDOC
## fetch(prefer_auth=True)

### Description
Fetches the current webhook. This could be used to get a full webhook from a partial webhook.

### Parameters
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### Subclassing ui.Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Define a custom container by subclassing ui.Container and adding components via decorators.

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

### discord.opus.is_loaded()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the opus library has been successfully loaded.

```APIDOC
## discord.opus.is_loaded()

### Description
Function to check if opus lib is successfully loaded. This must return True for voice to work.

### Returns
- **bool** - Indicates if the opus library has been loaded.
```

--------------------------------

### channel.typing()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is awaited.

```APIDOC
## async with channel.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is awaited.

### Usage
```python
# Indefinite typing indicator
async with channel.typing():
    await asyncio.sleep(20)

# 10-second typing indicator
await channel.typing()
```
```

--------------------------------

### Upload multiple files

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Shows how to send multiple file attachments using a list of discord.File objects.

```python
my_files = [
    discord.File('cool.png', 'testing.png'),
    discord.File(some_fp, 'cool_filename.png'),
]

await channel.send('Your images:', files=my_files)
```

--------------------------------

### Wait for reaction event

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates capturing multiple return arguments from a wait_for event.

```python
reaction, user = await client.wait_for("reaction_add", check=lambda r, u: u.id == 176995180300206080)

# use user and reaction
```

--------------------------------

### create_sticker

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a sticker for the guild.

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

### Errors
- **Forbidden**: You are not allowed to create stickers.
- **HTTPException**: An error occurred creating a sticker.

### Response
- **Returns**: GuildSticker
```

--------------------------------

### discord.ui.Select

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of custom options.

```APIDOC
## class discord.ui.Select

### Description
Represents a UI select menu with a list of custom options. This is represented to the user as a dropdown menu.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu that gets received during an interaction.
- **placeholder** (Optional[str]) - Optional - The placeholder text that is shown if nothing is selected.
- **min_values** (int) - Optional - The minimum number of items that must be chosen (0-25, default 1).
- **max_values** (int) - Optional - The maximum number of items that must be chosen (1-25, default 1).
- **options** (List[discord.SelectOption]) - Optional - A list of options that can be selected.
- **disabled** (bool) - Optional - Whether the select is disabled or not.
- **required** (bool) - Optional - Whether the select is required (only applicable within modals).
- **row** (Optional[int]) - Optional - The relative row this select menu belongs to (0-4).
- **id** (Optional[int]) - Optional - The ID of the component.
```

--------------------------------

### discord.PCMVolumeTransformer

Source: https://discordpy.readthedocs.io/en/latest/api.html

Transforms an existing AudioSource to provide volume control capabilities.

```APIDOC
## discord.PCMVolumeTransformer

### Description
Wraps an existing AudioSource to add volume control. Note that this does not work on audio sources where is_opus() returns True.

### Parameters
- **original** (AudioSource) - Required - The original audio source to transform.
- **volume** (float) - Optional - The initial volume level (e.g., 1.0 for 100%).

### Attributes
- **volume** (float) - Retrieves or sets the volume as a floating point percentage.
```

--------------------------------

### fetch_command(command_id, guild=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches a specific application command from the application, either globally or from a specific guild.

```APIDOC
## fetch_command(command_id, guild=None)

### Description
Fetches an application command from the application. This is a coroutine.

### Parameters
- **command_id** (int) - Required - The ID of the command to fetch.
- **guild** (Optional[Snowflake]) - Optional - The guild to fetch the command from. If not passed, the global command is fetched.

### Returns
- **AppCommand** - The application command.

### Raises
- **HTTPException** - Fetching the command failed.
- **MissingApplicationID** - The application ID could not be found.
- **NotFound** - The application command was not found.
```

--------------------------------

### Migrate AsyncIterator.find()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use discord.utils.find to locate items matching a predicate.

```python
def predicate(event):
    return event.reason is not None


# before
event = await guild.audit_logs().find(predicate)

# after
event = await discord.utils.find(predicate, guild.audit_logs())
```

--------------------------------

### CommandTree.sync

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Syncs the application commands to Discord. This must be called for the application commands to show up.

```APIDOC
## await CommandTree.sync(guild=None)

### Description
Syncs the application commands to Discord. This also runs the translator to get the translated strings necessary for feeding back into Discord.

### Parameters
- **guild** (Optional[Snowflake]) - Optional - The guild to sync the commands to. If None then it syncs all global commands instead.

### Returns
- **List[AppCommand]** - The application’s commands that got synced.
```

--------------------------------

### send(content=..., username=..., avatar_url=..., tts=False, ephemeral=False, file=..., files=..., embed=..., embeds=..., allowed_mentions=..., view=..., thread=..., thread_name=..., wait=False, suppress_embeds=False, silent=False, applied_tags=..., poll=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message using the webhook. This is a coroutine.

```APIDOC
## send(...)

### Description
Sends a message using the webhook. The content must be a type that can convert to a string through str(content).
```

--------------------------------

### fetch_widget

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the widget information for a guild.

```APIDOC
## fetch_widget(guild_id)

### Description
Gets a Widget from a guild ID. The guild must have the widget enabled. This function is a coroutine.

### Parameters
- **guild_id** (int) - Required - The ID of the guild.

### Returns
- **Widget** - The guild's widget.
```

--------------------------------

### set_footer(text=None, icon_url=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the footer for the embed content. Returns the class instance for chaining.

```APIDOC
### set_footer(text=None, icon_url=None)

#### Parameters
- **text** (str) - Optional - The footer text (max 2048 characters).
- **icon_url** (str) - Optional - The URL of the footer icon.
```

--------------------------------

### Using variable arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Allows a command to accept an arbitrary number of arguments using Python's *args syntax.

```python
@bot.command()
async def test(ctx, *args):
    arguments = ", ".join(args)
    await ctx.send(f"{len(args)} arguments: {arguments}")
```

--------------------------------

### @command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that creates an application command from a regular function under a Group.

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

### Combine Greedy and Optional converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Allows for flexible command signatures where multiple arguments can be provided optionally. Note that this can introduce parsing ambiguities.

```python
import typing


@bot.command()
async def ban(ctx, members: commands.Greedy[discord.Member], delete_days: typing.Optional[int] = 0, *, reason: str):
    """Mass bans members with an optional delete_days parameter"""
    delete_seconds = delete_days * 86400  # one day
    for member in members:
        await member.ban(delete_message_seconds=delete_seconds, reason=reason)
```

--------------------------------

### Bot.run

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A blocking call that abstracts away the event loop initialization and sets up logging.

```APIDOC
## Bot.run(token, *, reconnect=True, log_handler=..., log_formatter=..., log_level=..., root_logger=False)

### Description
A blocking call that abstracts away the event loop initialisation from you. This function also sets up the logging library.

### Parameters
- **token** (str) - Required - The authentication token.
- **reconnect** (bool) - Optional - If we should attempt reconnecting.
- **log_handler** (Optional[logging.Handler]) - Optional - The log handler to use.
- **log_formatter** (logging.Formatter) - Optional - The formatter to use with the log handler.
- **log_level** (int) - Optional - The default log level.
- **root_logger** (bool) - Optional - Whether to set up the root logger.
```

--------------------------------

### Update Command Syntax

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Commands now receive a context object by default, replacing the old bot.say method with ctx.send.

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

### @context_menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator used to create an application command context menu from a function.

```APIDOC
## @context_menu(*, name=..., nsfw=False, guild=..., guilds=..., auto_locale_strings=True, extras=...)

### Description
A decorator that creates an application command context menu from a regular function. The function must accept an Interaction as its first parameter and a Member, User, or Message as its second.

### Parameters
- **name** (Union[str, locale_str]) - Optional - The name of the context menu.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **guild** (Optional[Snowflake]) - Optional - The guild to add the command to.
- **guilds** (List[Snowflake]) - Optional - The list of guilds to add the command to.
- **auto_locale_strings** (bool) - Optional - Whether to implicitly wrap strings in locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary for storing extraneous data.
```

--------------------------------

### clone(name=None, category=None, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the current channel, creating a new channel with the same properties.

```APIDOC
## clone(name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. Requires `manage_channels` permission.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel. Defaults to the current channel name.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel, shown in the audit log.

### Returns
- **abc.GuildChannel** - The channel that was created.

### Raises
- **Forbidden** - Missing permissions to create the channel.
- **HTTPException** - Creating the channel failed.
```

--------------------------------

### Cog.get_app_commands

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a list of app commands and groups defined within the cog.

```APIDOC
## get_app_commands()

### Description
Returns the app commands that are defined inside this cog.

### Returns
- **List[Union[discord.app_commands.Command, discord.app_commands.Group]]** - A list of app commands and groups defined in this cog.
```

--------------------------------

### AppCommand.fetch_permissions()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves the command's permissions in a specific guild.

```APIDOC
## await AppCommand.fetch_permissions(guild)

### Description
Retrieves this command's permission in the guild.

### Parameters
- **guild** (Snowflake) - Required - The guild to retrieve the permissions from.

### Returns
- **GuildAppCommandPermissions** - An object representing the application command's permissions in the guild.

### Raises
- **Forbidden** - You do not have permission to fetch the application command's permissions.
- **HTTPException** - Fetching the application command's permissions failed.
- **MissingApplicationID** - The client does not have an application ID.
- **NotFound** - The application command's permissions could not be found.
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

### Raises
- **ExtensionNotFound** - The extension could not be imported.
- **ExtensionAlreadyLoaded** - The extension is already loaded.
- **NoEntryPointError** - The extension does not have a setup function.
- **ExtensionFailed** - The extension or its setup function had an execution error.
```

--------------------------------

### fetch

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Fetches the full message object.

```APIDOC
## fetch()

### Description
Fetches the partial message to a full `Message` object.

### Returns
- **Message** - The full message.
```

--------------------------------

### Registering per-command invocation hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Attach hooks directly to specific command instances to handle command-specific logic.

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

### discord.on_connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when the client has successfully connected to Discord.

```APIDOC
## discord.on_connect()

### Description
Called when the client has successfully connected to Discord. This is not the same as the client being fully prepared.
```

--------------------------------

### StageChannel.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects to voice and creates a VoiceClient to establish a connection to the voice server.

```APIDOC
## await connect(timeout=30.0, reconnect=True, cls=VoiceClient, self_deaf=False, self_mute=False)

### Description
Connects to voice and creates a VoiceClient to establish your connection to the voice server.

### Parameters
- **timeout** (float) - Optional - The timeout in seconds to wait for the connection to complete.
- **reconnect** (bool) - Optional - Whether the bot should automatically attempt a reconnect.
- **cls** (Type[VoiceProtocol]) - Optional - A type that subclasses VoiceProtocol to connect with.
- **self_mute** (bool) - Optional - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Optional - Indicates if the client should be self-deafened.

### Returns
- **VoiceProtocol** - A voice client that is fully connected to the voice server.
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

### follow(destination, reason)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Follows a news channel using a webhook.

```APIDOC
## follow(destination, reason)

### Description
Follows a channel using a webhook. Only news channels can be followed.

### Parameters
- **destination** (TextChannel) - Required - The channel you would like to follow from.
- **reason** (str) - Optional - The reason for following the channel.

### Returns
- Webhook - The created webhook.
```

--------------------------------

### PartialEmoji.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the asset into a File object suitable for sending.

```APIDOC
## await PartialEmoji.to_file(*, filename=None, description=None, spoiler=False)

### Description
Converts the asset into a File suitable for sending via abc.Messageable.send(). This is a coroutine.

### Parameters
- **filename** (Optional[str]) - Optional - The filename of the file.
- **description** (Optional[str]) - Optional - The description for the file.
- **spoiler** (bool) - Optional - Whether the file is a spoiler.

### Returns
- **File** - The asset as a file suitable for sending.
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
- **Webhook** - A partial webhook object.
```

--------------------------------

### ShardInfo.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Connects a shard.

```APIDOC
## await ShardInfo.connect()

### Description
Connects a shard. If the shard is already connected this does nothing.
```

--------------------------------

### Converter Usage

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows the standard syntax for applying a custom converter class to a command argument.

```python
@bot.command()
async def slap(ctx, *, reason: Slapper):
    await ctx.send(reason)
```

--------------------------------

### await leave()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the guild. This is a coroutine.

```APIDOC
## await leave()

### Description
Leaves the guild.

### Raises
- **HTTPException** - Leaving the guild failed.
```

--------------------------------

### await add_tags(*tags, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds the given forum tags to a thread. The parent channel must be a ForumChannel.

```APIDOC
## await add_tags(*tags, reason=None)

### Description
Adds the given forum tags to a thread. You must have manage_threads to use this or the thread must be owned by you.

### Parameters
- **tags** (abc.Snowflake) - Required - An argument list of abc.Snowflake representing a ForumTag to add to the thread.
- **reason** (Optional[str]) - Optional - The reason for adding these tags.
```

--------------------------------

### Create command groups

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the group decorator to create nested subcommands.

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

### Perform HTTP requests with ClientSession

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Replaces removed helper functions with a persistent ClientSession.

```python
async with aiohttp.ClientSession() as sess:
    async with sess.get('url') as resp:
        # work with resp
```

--------------------------------

### create_forum

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a ForumChannel within the category.

```APIDOC
## await create_forum(name, **options)

### Description
A shortcut method to create a ForumChannel in the category.

### Returns
- **ForumChannel** - The channel that was just created.
```

--------------------------------

### Migrate Asynchronous Webhooks

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates the asynchronous webhook initialization by removing the explicit adapter and passing the session directly.

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

### create_guild

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new guild. Note that bot accounts in more than 10 guilds are not allowed to create guilds.

```APIDOC
## create_guild(name, icon=..., code=...)

### Description
Creates a new Guild. This function is a coroutine.

### Parameters
- **name** (str) - Required - The name of the guild.
- **icon** (Optional[bytes]) - Optional - The bytes-like object representing the icon.
- **code** (str) - Optional - The code for a template to create the guild with.

### Returns
- **Guild** - The guild created.
```

--------------------------------

### await fetch_guild(guild_id, /, *, with_counts=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a Guild from an ID.

```APIDOC
## await fetch_guild(guild_id, /, *, with_counts=True)

### Description
Retrieves a Guild from an ID.

### Parameters
- **guild_id** (int) - Required - The guild's ID to fetch from.
- **with_counts** (bool) - Optional - Whether to include count information in the guild. Defaults to True.

### Raises
- **NotFound** - The guild doesn't exist or you got no access to it.
- **HTTPException** - Getting the guild failed.

### Returns
- **Guild** - The guild from the ID.
```

--------------------------------

### @discord.app_commands.command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Decorator to create an application command from a regular function.

```APIDOC
## @discord.app_commands.command(name=..., description=..., nsfw=False, auto_locale_strings=True, extras=...)

### Description
Creates an application command from a regular function.

### Parameters
- **name** (str) - Optional - The name of the application command.
- **description** (str) - Optional - The description of the application command.
- **nsfw** (bool) - Optional - Whether the command is NSFW.
- **auto_locale_strings** (bool) - Optional - Whether to implicitly wrap strings in locale_str.
- **extras** (dict) - Optional - A dictionary for storing extraneous data.
```

--------------------------------

### integrations

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a list of all integrations attached to the guild.

```APIDOC
## await integrations()

### Description
Returns a list of all integrations attached to the guild. You must have `manage_guild` to do this.

### Errors
- **Forbidden**: You do not have permission to create the integration.
- **HTTPException**: Fetching the integrations failed.

### Response
- **Returns**: List[Integration]
```

--------------------------------

### Configure custom sharding

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Manually specify shard counts and IDs for the AutoShardedClient.

```python
# launch 10 shards regardless
client = discord.AutoShardedClient(shard_count=10)

# launch specific shard IDs in this process
client = discord.AutoShardedClient(shard_count=10, shard_ids=(1, 2, 5, 6))
```

--------------------------------

### Collect reaction users into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Collect all users who reacted into a list for random selection. This approach loads all users into memory.

```python
users = [user async for user in reaction.users()]
# users is now a list of User...
winner = random.choice(users)
await channel.send(f"{winner} has won the raffle.")
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

### discord.on_guild_channel_create(channel)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event handler called when a guild channel is created.

```APIDOC
## discord.on_guild_channel_create(channel)

### Description
Called whenever a guild channel is created. Requires Intents.guilds.

### Parameters
- **channel** (abc.GuildChannel) - Required - The guild channel that got created.
```

--------------------------------

### discord.SelectOption

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents an option within a select menu. Users can construct this class to define menu choices.

```APIDOC
## class discord.SelectOption(label, value=..., description=None, emoji=None, default=False)

### Description
Represents a select menu's option. These can be created by users.

### Parameters
- **label** (str) - Required - The label of the option (up to 100 characters).
- **value** (str) - Optional - The value of the option (up to 100 characters). Defaults to label if not provided.
- **description** (Optional[str]) - Optional - An additional description of the option (up to 100 characters).
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the option.
- **default** (bool) - Optional - Whether this option is selected by default.
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

### Registering global invocation hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use these decorators to execute code before or after any command is invoked.

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

### Wait for message event

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates the legacy method for waiting for a message event prior to v1.0.

```python
# before
msg = await client.wait_for_message(author=message.author, channel=message.channel)
```

--------------------------------

### Send local file in embed

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Upload a file and reference it in the embed using the attachment:// prefix.

```python
file = discord.File("path/to/my/image.png", filename="image.png")
embed = discord.Embed()
embed.set_image(url="attachment://image.png")
await channel.send(file=file, embed=embed)
```

--------------------------------

### Imports for Attachment and Optional

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Required imports when combining file attachments with optional parameters.

```python
import typing
import discord
```

--------------------------------

### Checking Channel Types

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use isinstance() with specific channel types or abstract base classes to verify channel categories.

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

### AudioSource.read

Source: https://discordpy.readthedocs.io/en/latest/api.html

Reads 20ms worth of audio data from the source.

```APIDOC
## read()

### Description
Reads 20ms worth of audio. If the audio is complete, returns an empty bytes-like object.

### Returns
- **bytes** - A bytes like object that represents the PCM or Opus data.
```

--------------------------------

### @discord.ext.commands.before_invoke(coro)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a coroutine as a pre-invoke hook for a command.

```APIDOC
## @discord.ext.commands.before_invoke(coro)

### Description
Registers a coroutine to be executed before the command is invoked. Useful for logging or setup tasks.
```

--------------------------------

### Migrate Synchronous Webhooks

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Updates synchronous webhook usage by switching from the generic Webhook class with an adapter to the dedicated SyncWebhook class.

```python
# before
webhook = discord.Webhook.partial(123456, "token-here", adapter=discord.RequestsWebhookAdapter())
webhook.send("Hello World", username="Foo")

# after
webhook = discord.SyncWebhook.partial(123456, "token-here")
webhook.send("Hello World", username="Foo")
```

--------------------------------

### Migrate manual iterator advancement

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use anext() or __anext__() to retrieve the next item from an iterator without a loop.

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

### fetch_soundboard_sound()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a SoundboardSound with the specified ID.

```APIDOC
## fetch_soundboard_sound(sound_id)

### Description
Retrieves a `SoundboardSound` with the specified ID.

### Returns
- **SoundboardSound** - The retrieved sound.
```

--------------------------------

### Widget.fetch_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an Invite from the widget’s invite URL.

```APIDOC
## async Widget.fetch_invite(with_counts=True)

### Description
Retrieves an Invite from the widget’s invite URL. This is a coroutine.

### Parameters
- **with_counts** (bool) - Optional - Whether to include count information in the invite.

### Returns
- **Optional[Invite]** - The invite from the widget’s invite URL, if available.
```

--------------------------------

### Create a UI Modal

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Inherit from discord.ui.Modal to define a custom modal popup with input fields and a submission handler.

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

### create_application_emoji(name, image)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates an emoji for the current application.

```APIDOC
## await create_application_emoji(name, image)

### Description
Create an emoji for the current application.

### Parameters
- **name** (str) - Required - The emoji name. Must be between 2 and 32 characters long.
- **image** (bytes) - Required - The bytes-like object representing the image data to use. Only JPG, PNG and GIF images are supported.

### Returns
- **Emoji** - The emoji that was created.
```

--------------------------------

### Using positional arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Defines a command that accepts a single positional argument.

```python
@bot.command()
async def test(ctx, arg):
    await ctx.send(arg)
```

--------------------------------

### Member.create_dm()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a DMChannel with the member.

```APIDOC
## await Member.create_dm()

### Description
Creates a DMChannel with this user. This should be rarely called, as this is done transparently for most people.

### Returns
- **DMChannel** - The channel that was created.
```

--------------------------------

### Register a Global Command Check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a check that runs before any command checks for every command in the bot.

```python
@bot.check
def check_commands(ctx):
    return ctx.command.qualified_name in allowed_commands
```

--------------------------------

### wait_until_ready()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that blocks until the client's internal cache is fully populated and ready.

```APIDOC
## wait_until_ready()

### Description
Waits until the client's internal cache is all ready. 

### Warning
Calling this inside `setup_hook()` can lead to a deadlock.
```

--------------------------------

### Define an Application Command Group

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Inherit from app_commands.Group to create a command group. Decorators applied to the class will affect all commands within the group.

```python
from discord import app_commands


@app_commands.guild_only()
class MyGroup(app_commands.Group):
    pass
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
- **Optional[Union[Command, ContextMenu, Group]]** - The application command that was found. If nothing was found then None is returned.
```

--------------------------------

### Template.sync

Source: https://discordpy.readthedocs.io/en/latest/api.html

Syncs the template to the guild's current state.

```APIDOC
## Template.sync()

### Description
Sync the template to the guild’s current state. Requires `manage_guild` permission in the source guild.

### Returns
- **Template** - The newly edited template.
```

--------------------------------

### reply(content=None, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that acts as a shortcut to send() to reply to the message referenced by this context.

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

### Set channel permissions using PermissionOverwrite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Configures permissions by explicitly creating and assigning a PermissionOverwrite object.

```python
overwrite = discord.PermissionOverwrite()
overwrite.send_messages = False
overwrite.read_messages = True
await channel.set_permissions(member, overwrite=overwrite)
```

--------------------------------

### Register a command with intents

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Commands require the message_content intent to be enabled in both the developer portal and the bot instance.

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

### Apply logging configuration to the root logger

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Uses root_logger=True to apply the library's logging configuration to all loggers.

```python
client.run(token, log_handler=handler, root_logger=True)
```

--------------------------------

### Migrate AsyncIterator.flatten()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use a list comprehension with async for to collect items.

```python
# before
users = await reaction.users().flatten()

# after
users = [user async for user in reaction.users()]
```

--------------------------------

### discord.ext.commands.when_mentioned_or

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A callable that implements when mentioned or other prefixes provided, intended for use with the Bot.command_prefix attribute.

```APIDOC
## discord.ext.commands.when_mentioned_or(*prefixes)

### Description
A callable that implements when mentioned or other prefixes provided. These are meant to be passed into the `Bot.command_prefix` attribute.
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

### Raises
- **DiscordException** - The asset does not have an associated state.
- **ValueError** - The asset is a unicode emoji.
- **TypeError** - The asset is a sticker with lottie type.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
```

--------------------------------

### discord.on_app_command_completion(interaction, command)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event handler called when an application command has successfully completed.

```APIDOC
## discord.on_app_command_completion(interaction, command)

### Description
Called when a app_commands.Command or app_commands.ContextMenu has successfully completed without error.

### Parameters
- **interaction** (Interaction) - Required - The interaction of the command.
- **command** (Union[app_commands.Command, app_commands.ContextMenu]) - Required - The command that completed successfully.
```

--------------------------------

### Enable Member Intents

Source: https://discordpy.readthedocs.io/en/latest/intents.html

Configures the bot to request member data by enabling the privileged members intent.

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

### AutoShardedClient.connect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Initiates the connection request for the client. This is a coroutine that handles the initial connection flow.

```APIDOC
## await connect(timeout, reconnect, self_deaf=False, self_mute=False)

### Description
An abstract method called when the client initiates the connection request. It is recommended to use Guild.change_voice_state() within this method to start the voice connection flow.

### Parameters
- **timeout** (float) - Required - The timeout for the connection.
- **reconnect** (bool) - Required - Whether reconnection is expected.
- **self_mute** (bool) - Optional - Indicates if the client should be self-muted (New in version 2.0).
- **self_deaf** (bool) - Optional - Indicates if the client should be self-deafened (New in version 2.0).
```

--------------------------------

### publish()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Publishes the message to the channel's followers.

```APIDOC
## await publish()

### Description
Publishes this message to the channel’s followers. The message must have been sent in a news channel. This is a coroutine.
```

--------------------------------

### Schedule a background task with specific times

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Demonstrates using the @tasks.loop decorator with a list of datetime.time objects to execute a task at specific times of the day.

```python
# If no tzinfo is given then UTC is assumed.
times = [datetime.time(hour=8, tzinfo=utc), datetime.time(hour=12, minute=30, tzinfo=utc), datetime.time(hour=16, minute=40, second=30, tzinfo=utc)]


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.my_task.start()

    def cog_unload(self):
        self.my_task.cancel()

    @tasks.loop(time=times)
    async def my_task(self):
        print("My task is running!")
```

--------------------------------

### Register a pre-invoke hook with before_invoke

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

### StickerItem.fetch

Source: https://discordpy.readthedocs.io/en/latest/api.html

Attempts to retrieve the full sticker data of the sticker item.

```APIDOC
## async StickerItem.fetch()

### Description
Attempts to retrieve the full sticker data of the sticker item. This is a coroutine.

### Raises
- **HTTPException** - Retrieving the sticker failed.

### Returns
- **Union[StandardSticker, GuildSticker]** - The retrieved sticker.
```

--------------------------------

### invoke(command, *args, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Calls a command with the arguments given, bypassing converters, checks, and hooks.

```APIDOC
## invoke(command, *args, **kwargs)

### Description
Calls a command with the arguments given. This is useful if you want to call the callback that a Command holds internally. This does not handle converters, checks, cooldowns, pre-invoke, or after-invoke hooks.

### Parameters
- **command** (Command) - Required - The command that is going to be called.
- ***args** - Optional - The arguments to use.
- ****kwargs** - Optional - The keyword arguments to use.
```

--------------------------------

### Define a command with a Timestamp parameter

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use app_commands.Timestamp to automatically convert Discord timestamp inputs into datetime objects.

```python
@app_commands.command()
async def datetime(interaction: discord.Interaction, value: app_commands.Timestamp):
    await interaction.response.send_message(value.isoformat())
```

--------------------------------

### GroupMixin Methods

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Methods available for managing commands within a GroupMixin instance.

```APIDOC
## add_command(command)

### Description
Adds a Command into the internal list of commands. This is usually not called directly, as the @command or @group decorators are preferred.

### Parameters
- **command** (Command) - Required - The command to add.

### Raises
- **CommandRegistrationError** - If the command or its alias is already registered.
- **TypeError** - If the command passed is not a subclass of Command.

## remove_command(name)

### Description
Removes a Command from the internal list of commands by its name.

### Parameters
- **name** (str) - Required - The name of the command to remove.

### Returns
- **Command** (Optional) - The command that was removed, or None if not found.

## get_command(name)

### Description
Retrieves a Command from the internal list of commands. Supports fully qualified names for subcommands (e.g., 'foo bar').

### Parameters
- **name** (str) - Required - The name of the command to get.

### Returns
- **Command** (Optional) - The requested command, or None if not found.

## walk_commands()

### Description
An iterator that recursively walks through all commands and subcommands.

### Yields
- **Union[Command, Group]** - A command or group from the internal list.
```

--------------------------------

### set_image(url)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the image for the embed content. Returns the class instance for chaining.

```APIDOC
### set_image(url)

#### Parameters
- **url** (str) - Optional - The source URL for the image.
```

--------------------------------

### Late Binding with parameter()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses parameter() to define a default value dynamically based on the command context.

```python
@bot.command()
async def wave(ctx, to: discord.User = commands.parameter(default=lambda ctx: ctx.author)):
    await ctx.send(f"Hello {to.mention} :wave:")
```

--------------------------------

### kick(user, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Kicks a user from the guild. Requires the 'kick_members' permission.

```APIDOC
## kick(user, *, reason=None)

### Description
Kicks a user from the guild. The user must meet the abc.Snowflake abc. You must have 'kick_members' to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to kick from the guild.
- **reason** (Optional[str]) - Optional - The reason the user got kicked.

### Raises
- **Forbidden** - You do not have the proper permissions to kick.
- **HTTPException** - Kicking failed.
```

--------------------------------

### create_dm(user)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a DMChannel with the specified user.

```APIDOC
## await create_dm(user)

### Description
Creates a DMChannel with this user.

### Parameters
- **user** (Snowflake) - Required - The user to create a DM with.

### Returns
- **DMChannel** - The channel that was created.
```

--------------------------------

### Using parameter() for Type Hinting

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the parameter() function to provide type information to checkers while still using a custom converter.

```python
@bot.command()
async def bar(ctx, cool_value: SomeType = commands.parameter(converter=MyVeryCoolConverter)):
    cool_value.foo  # no error (hurray)
```

--------------------------------

### discord.on_member_join(member)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Member joins a Guild. Requires Intents.members to be enabled.

```APIDOC
## discord.on_member_join(member)

### Description
Called when a Member joins a Guild. This requires Intents.members to be enabled.

### Parameters
- **member** (Member) - The member who joined.
```

--------------------------------

### Using Custom Context

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Inject a custom context class into the bot using get_context within on_message.

```python
class MyBot(commands.Bot):
    async def on_message(self, message):
        ctx = await self.get_context(message, cls=MyContext)
        await self.invoke(ctx)
```

--------------------------------

### from_interaction(interaction)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a context from a discord.Interaction. This only works on application command-based interactions.

```APIDOC
## from_interaction(interaction)

### Description
Creates a context from a discord.Interaction. This only works on application command-based interactions, such as slash commands or context menus.

### Parameters
- **interaction** (discord.Interaction) - Required - The interaction to create a context with.
```

--------------------------------

### Member.move_to

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves a member to a new voice channel.

```APIDOC
## Member.move_to(channel, *, reason=None)

### Description
Moves a member to a new voice channel. The member must be connected to a voice channel first.

### Parameters
- **channel** (Optional[Union[VoiceChannel, StageChannel]]) - Required - The new voice channel to move the member to.
- **reason** (Optional[str]) - Optional - The reason for the audit log.
```

--------------------------------

### Define Context Menus with @context_menu

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the @context_menu decorator to create context menu commands. The callback must accept an Interaction as the first argument and a target object (Member, User, or Message) as the second.

```python
@app_commands.context_menu()
async def react(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message("Very cool message!", ephemeral=True)


@app_commands.context_menu()
async def ban(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message(f"Should I actually ban {user}...", ephemeral=True)
```

--------------------------------

### Updating Converter classes

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Converters now require an asynchronous convert method accepting ctx and argument parameters.

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

### Customizing command names

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Shows how to override the default command name using the name parameter in the decorator.

```python
@bot.command(name="list")
async def _list(ctx, arg):
    pass
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

### Retrieve guild and channel by name

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use discord.utils.get to find objects by attributes. Always check for None to avoid errors if the object is not found.

```python
guild = discord.utils.get(client.guilds, name="My Server")

# make sure to check if it's found
if guild is not None:
    # find a channel by name
    channel = discord.utils.get(guild.text_channels, name="cool-channel")
```

--------------------------------

### add_user

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a user to the thread.

```APIDOC
## add_user(user)

### Description
Adds a user to this thread. Requires send_messages_in_threads permission.

### Parameters
- **user** (abc.Snowflake) - Required - The user to add to the thread.
```

--------------------------------

### create_text_channel(name, ...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel within the guild.

```APIDOC
## create_text_channel(name, reason=None, category=None, news=False, ...)

### Description
Creates a TextChannel for the guild. Requires manage_channels permission.

### Parameters
- **name** (str) - Required - The name of the channel.
- **reason** (str) - Optional - The reason for creating the channel.
- **category** (CategoryChannel) - Optional - The category to place the channel in.
- **overwrites** (dict) - Optional - Permission overwrites for the channel.
```

--------------------------------

### discord.opus.load_opus(name)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Loads the libopus shared library for use with voice. This function is required for PCM-based AudioSources if the library is not automatically found.

```APIDOC
## discord.opus.load_opus(name)

### Description
Loads the libopus shared library for use with voice. If this function is not called, the library attempts to use ctypes.util.find_library().

### Parameters
- **name** (str) - Required - The filename of the shared library.
```

--------------------------------

### Execute coroutines in music player after callback

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Uses asyncio.run_coroutine_threadsafe to safely trigger a coroutine from the music player's non-async thread.

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

### create_text_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel in the guild. This is a coroutine.

```APIDOC
## await create_text_channel(name, *, overwrites=None, category=None, position=0, topic=None, slowmode_delay=0, nsfw=False, news=False, default_auto_archive_duration=None, default_thread_slowmode_delay=0, reason=None)

### Description
Creates a new text channel in the guild. Returns the created TextChannel object.

### Parameters
- **name** (str) - Required - The channel's name.
- **overwrites** (Dict[Union[Role, Member], PermissionOverwrite]) - Optional - A dict of target to PermissionOverwrite.
- **category** (Optional[CategoryChannel]) - Optional - The category to place the channel under.
- **position** (int) - Optional - The position in the channel list.
- **topic** (str) - Optional - The new channel's topic.
- **slowmode_delay** (int) - Optional - The slowmode rate limit in seconds.
- **nsfw** (bool) - Optional - Whether the channel is NSFW.
- **news** (bool) - Optional - Whether to create as a news channel.
- **default_auto_archive_duration** (int) - Optional - Default auto archive duration for threads.
- **default_thread_slowmode_delay** (int) - Optional - Default slowmode delay for threads.
- **reason** (Optional[str]) - Optional - The reason for creating the channel.

### Returns
- **TextChannel** - The channel that was just created.
```

--------------------------------

### VoiceClient.move_to(channel, *, timeout=30.0)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves the voice client to a different voice channel.

```APIDOC
## await VoiceClient.move_to(channel, *, timeout=30.0)

### Description
Moves you to a different voice channel. This is a coroutine.

### Parameters
- **channel** (Optional[abc.Snowflake]) - Required - The channel to move to. Must be a voice channel.
- **timeout** (Optional[float]) - Optional - How long to wait for the move to complete.

### Raises
- **asyncio.TimeoutError** - The move did not complete in time, but may still be ongoing.
```

--------------------------------

### permissions_for(obj, /)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a User in a DM channel context.

```APIDOC
## permissions_for(obj, /)

### Description
Handles permission resolution for a User. This function is provided for compatibility with other channel types, as direct messages do not have standard permission concepts.

### Parameters
- **obj** (User) - Required - The user to check permissions for. This parameter is ignored.

### Returns
- **Permissions** - The resolved permissions object.
```

--------------------------------

### Walking Cog Subcommands

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Use walk_commands to retrieve all commands and subcommands associated with a Cog.

```python
>>> print([c.qualified_name for c in cog.walk_commands()])
```

--------------------------------

### add_listener(func, /, name=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

The non-decorator alternative to the listen() decorator for registering event listeners.

```APIDOC
## add_listener(func, /, name=...)

### Description
The non-decorator alternative to listen().

### Parameters
- **func** (coroutine) - Required - The function to call.
- **name** (str) - Optional - The name of the event to listen for. Defaults to func.__name__.

### Example
```python
async def on_ready(): pass
async def my_message(message): pass

bot.add_listener(on_ready)
bot.add_listener(my_message, 'on_message')
```
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

### create_voice_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new voice channel in the guild. This is a coroutine.

```APIDOC
## await create_voice_channel(name, *, reason=None, category=None, position=..., bitrate=..., user_limit=..., rtc_region=..., video_quality_mode=..., overwrites=..., nsfw=...)

### Description
Creates a new voice channel in the guild. Returns the created VoiceChannel object.

### Parameters
- **name** (str) - Required - The channel's name.
- **reason** (Optional[str]) - Optional - The reason for creating the channel.
- **category** (Optional[CategoryChannel]) - Optional - The category to place the channel under.
- **position** (int) - Optional - The position in the channel list.
- **bitrate** (int) - Optional - The preferred audio bitrate.
- **user_limit** (int) - Optional - The limit for number of members.
- **rtc_region** (Optional[str]) - Optional - The region for voice communication.
- **video_quality_mode** (VideoQualityMode) - Optional - The camera video quality.
- **nsfw** (bool) - Optional - Whether the channel is NSFW.

### Returns
- **VoiceChannel** - The channel that was just created.
```

--------------------------------

### get_prefix(message)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the prefix the bot is listening to. This is a coroutine.

```APIDOC
## get_prefix(message)

### Description
Retrieves the prefix the bot is listening to with the message as a context.

### Parameters
- **message** (discord.Message) - Required - The message context to get the prefix of.

### Returns
- **Union[List[str], str]** - A list of prefixes or a single prefix.
```

--------------------------------

### Migrate AsyncIterator.chunk()

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use discord.utils.as_chunks to process items in groups.

```python
# before
async for leader, *users in reaction.users().chunk(3):
    ...

# after
async for leader, *users in discord.utils.as_chunks(reaction.users(), 3):
    ...
```

--------------------------------

### StageChannel.send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the StageChannel. This is a coroutine that returns the sent Message object.

```APIDOC
## StageChannel.send

### Description
Sends a message to the destination with the content given. If content is None, an embed must be provided.

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
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions processed in this message.
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
- **NotFound** - Message with the same nonce was deleted.
- **ValueError** - Invalid files or embeds list size.
- **TypeError** - Invalid parameter combinations or reference object type.
```

--------------------------------

### create_entitlement(sku, owner, owner_type)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Creates a test Entitlement for the application.

```APIDOC
## await create_entitlement(sku, owner, owner_type)

### Description
Creates a test Entitlement for the application.

### Parameters
- **sku** (Snowflake) - Required - The SKU to create the entitlement for.
- **owner** (Snowflake) - Required - The ID of the owner.
- **owner_type** (EntitlementOwnerType) - Required - The type of the owner.
```

--------------------------------

### Loop.restart

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

A convenience method to restart the internal task.

```APIDOC
## Loop.restart(*args, **kwargs)

### Description
A convenience method to restart the internal task. Note that the task is not returned.
```

--------------------------------

### await reply(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine that sends a reply to the message. This is a shortcut for abc.Messageable.send().

```APIDOC
## await reply(**kwargs)

### Description
A shortcut method to send a reply to the message.

### Returns
- **Message** - The message that was sent.

### Raises
- **HTTPException** - Sending the message failed.
- **Forbidden** - You do not have the proper permissions to send the message.
- **ValueError** - The files list is not of the appropriate size.
- **TypeError** - You specified both file and files.
```

--------------------------------

### Range converter usage

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates restricting a numeric input to a specific range using commands.Range.

```python
@bot.command()
async def range(ctx: commands.Context, value: commands.Range[int, 10, 12]):
    await ctx.send(f"Your value is {value}")
```

--------------------------------

### await change_presence(activity=None, status=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Changes the client's presence status and activity.

```APIDOC
## await change_presence(activity=None, status=None)

### Description
Changes the client's presence status and activity.

### Parameters
- **activity** (Optional[BaseActivity]) - Optional - The activity being done.
- **status** (Optional[Status]) - Optional - Indicates what status to change to.

### Raises
- **TypeError** - If the activity parameter is not the proper type.
```

--------------------------------

### await _create_custom_emoji(name, image, roles=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new custom emoji for the guild.

```APIDOC
## await _create_custom_emoji(name, image, roles=..., reason=None)

### Description
Creates a custom `Emoji` for the guild. Requires `manage_emojis` permission.

### Parameters
- **name** (str) - Required - The emoji name (at least 2 characters).
- **image** (bytes) - Required - The bytes-like object representing the image data (JPG, PNG, or GIF).
- **roles** (List[Role]) - Optional - A list of roles that can use this emoji.
- **reason** (Optional[str]) - Optional - The reason for creating this emoji for the audit log.

### Returns
- **Emoji** - The created emoji.

### Raises
- **Forbidden** - You are not allowed to create emojis.
- **HTTPException** - An error occurred creating an emoji.
```

--------------------------------

### fetch_channels()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all channels that the guild has.

```APIDOC
## await fetch_channels()

### Description
Retrieves all `abc.GuildChannel` that the guild has.

### Returns
- **Sequence[abc.GuildChannel]** - All channels in the guild.
```

--------------------------------

### AutoShardedClient.play

Source: https://discordpy.readthedocs.io/en/latest/api.html

Plays an AudioSource. The finalizer 'after' is called after the source has been exhausted or an error occurred.

```APIDOC
## play(source, *, after=None, application='audio', bitrate=128, fec=True, expected_packet_loss=0.15, bandwidth='full', signal_type='auto')

### Description
Plays an AudioSource. If an error happens while the audio player is running, the exception is caught and the audio player is then stopped.

### Parameters
- **source** (AudioSource) - Required - The audio source we’re reading from.
- **after** (Callable[[Optional[Exception]], Any]) - Optional - The finalizer that is called after the stream is exhausted.
- **application** (str) - Optional - Configures the encoder’s intended application. Can be 'audio', 'voip', or 'lowdelay'. Defaults to 'audio'.
- **bitrate** (int) - Optional - Configures the bitrate in the encoder (16-512). Defaults to 128.
- **fec** (bool) - Optional - Configures the encoder’s use of inband forward error correction. Defaults to True.
- **expected_packet_loss** (float) - Optional - Configures the encoder’s expected packet loss percentage. Defaults to 0.15.
- **bandwidth** (str) - Optional - Configures the encoder’s bandpass. Can be 'narrow', 'medium', 'wide', 'superwide', or 'full'. Defaults to 'full'.
- **signal_type** (str) - Optional - Configures the type of signal being encoded. Can be 'auto', 'voice', or 'music'. Defaults to 'auto'.
```

--------------------------------

### Iterate over pinned messages

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to asynchronously iterate through pinned messages in a channel with a specified limit.

```python
counter = 0
async for message in channel.pins(limit=250):
    counter += 1
```

--------------------------------

### Send Typing Indicator for Fixed Duration

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a typing indicator for 10 seconds by awaiting the context manager.

```python
await channel.typing()
# Do some computational magic for about 10 seconds
await channel.send("Done!")
```

--------------------------------

### typing(ephemeral=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination. In interaction-based contexts, this acts as a defer() call.

```APIDOC
## typing(ephemeral=False)

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is awaited. In an interaction-based context, this is equivalent to a defer() call.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral. Only valid for interaction-based contexts.
```

--------------------------------

### await chunk(cache)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Requests all members belonging to the guild. Requires Intents.members to be enabled.

```APIDOC
## await chunk(cache=True)

### Description
Requests all members that belong to this guild. This is a websocket operation and requires Intents.members to be enabled.

### Parameters
- **cache** (bool) - Whether to cache the members as well.

### Returns
- **List[Member]** - The list of members in the guild.

### Raises
- **ClientException** - The members intent is not enabled.
```

--------------------------------

### discord.ui.Container

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI container component for layout management.

```APIDOC
## class discord.ui.Container

### Description
Represents a UI container. This is a top-level layout component that can be used on LayoutView and can contain various UI elements.

### Constructor Parameters
- **children** - The child components to include.
- **accent_colour** (Optional) - Accent colour for the container.
- **accent_color** (Optional) - Alias for accent_colour.
- **spoiler** (bool) - Whether the container is a spoiler.
- **id** (Optional[int]) - Unique ID for the container.
```

--------------------------------

### webhooks()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the list of webhooks for the channel.

```APIDOC
## webhooks()

### Description
Gets the list of webhooks from this channel. Requires manage_webhooks permission.

### Returns
- List[Webhook] - The webhooks for this channel.
```

--------------------------------

### Basic Integer Converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses function annotations to automatically cast command arguments to integers.

```python
@bot.command()
async def add(ctx, a: int, b: int):
    await ctx.send(a + b)
```

--------------------------------

### Copy global commands to a guild

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use this method to copy all global commands to a specific guild, typically for development purposes.

```python
tree.copy_global_to(guild=discord.Object(123456789012345678))
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
- **min_values** (int) - Optional - Minimum number of items to choose. Defaults to 1 (0-25).
- **max_values** (int) - Optional - Maximum number of items to choose. Defaults to 1 (1-25).
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required (only for modals).
- **default_values** (Sequence[Snowflake]) - Optional - Channels selected by default.
- **row** (Optional[int]) - Optional - The relative row (0-4) for the component.
- **id** (Optional[int]) - Optional - Unique ID of the component.

### Methods
- **callback(interaction)**: Coroutine to be overridden for handling the interaction.
- **interaction_check(interaction)**: Coroutine to check if the callback should be processed.
```

--------------------------------

### create_thread

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a public thread in the forum channel with an initial message.

```APIDOC
## await create_thread(name, auto_archive_duration=..., slowmode_delay=None, content=None, tts=False, embed=..., embeds=..., file=..., files=..., stickers=..., allowed_mentions=..., mention_author=..., applied_tags=..., view=..., suppress_embeds=False, silent=False, reason=None)

### Description
Creates a thread in this forum. This thread is a public thread with the initial message given. Currently in order to start a thread in this forum, the user needs `send_messages`.

### Parameters
- **name** (str) - Required - The name of the thread.
- **auto_archive_duration** (int) - Optional - The duration in minutes before a thread is automatically hidden.
- **slowmode_delay** (Optional[int]) - Optional - Specifies the slowmode rate limit for user in this channel, in seconds.
- **content** (Optional[str]) - Optional - The content of the message to send with the thread.
- **applied_tags** (List[discord.ForumTag]) - Optional - A list of tags to apply to the thread.

### Returns
- **Tuple[Thread, Message]** - The created thread with the created message.
```

--------------------------------

### fetch_stickers

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a list of all stickers for the guild.

```APIDOC
## await fetch_stickers()

### Description
Retrieves a list of all `Sticker`s for the guild.

### Errors
- **HTTPException**: An error occurred fetching the stickers.

### Response
- **Returns**: List[GuildSticker]
```

--------------------------------

### discord.on_automod_rule_create(rule)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event handler called when an AutoModRule is created.

```APIDOC
## discord.on_automod_rule_create(rule)

### Description
Called when an AutoModRule is created. Requires manage_guild permission and Intents.auto_moderation_configuration.

### Parameters
- **rule** (AutoModRule) - Required - The rule that was created.
```

--------------------------------

### StageChannel.clone

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the current channel, creating a new one with the same properties. Requires manage_channels permission.

```APIDOC
## await clone(name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel.

### Parameters
- **name** (Optional[str]) - Optional - The name of the new channel.
- **category** (Optional[CategoryChannel]) - Optional - The category the new channel belongs to.
- **reason** (Optional[str]) - Optional - The reason for cloning this channel.

### Returns
- **abc.GuildChannel** - The channel that was created.
```

--------------------------------

### forward(destination, *, fail_if_not_exists=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Forwards the message to a specified channel.

```APIDOC
## await forward(destination, *, fail_if_not_exists=True)

### Description
Forwards this message to a target channel.

### Parameters
- **destination** (Messageable) - Required - The channel to forward the message to.
- **fail_if_not_exists** (bool) - Optional - Whether to raise an exception if the message no longer exists.
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

### await query_members(query, limit, user_ids, presences, cache)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Requests members of the guild matching a specific query or list of IDs.

```APIDOC
## await query_members(query=None, limit=5, user_ids=None, presences=False, cache=True)

### Description
Request members of this guild whose username or nickname starts with the given query. This is a websocket operation.

### Parameters
- **query** (Optional[str]) - The string that the username or nickname should start with.
- **limit** (int) - The maximum number of members to return (5-100).
- **presences** (bool) - Whether to request presences.
- **cache** (bool) - Whether to cache the members internally.
- **user_ids** (Optional[List[int]]) - List of user IDs to search for.

### Returns
- **List[Member]** - The list of members that matched the query.

### Raises
- **asyncio.TimeoutError** - The query timed out.
- **ValueError** - Invalid parameters passed.
- **ClientException** - The presences intent is not enabled.
```

--------------------------------

### discord.on_guild_role_create(role)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a guild creates a new role. Requires Intents.guilds to be enabled.

```APIDOC
## discord.on_guild_role_create(role)

### Description
Called when a Guild creates a new Role.

### Parameters
- **role** (Role) - The role that was created.
```

--------------------------------

### move(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A rich interface to help move a channel relative to other channels.

```APIDOC
## move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. Requires `manage_channels` permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning of the list.
- **end** (bool) - Optional - Move to the end of the list.
- **before** (Snowflake) - Optional - Move before the given channel.
- **after** (Snowflake) - Optional - Move after the given channel.
- **offset** (int) - Optional - Number of channels to offset the move by.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the category.
- **reason** (str) - Optional - The reason for the move.

### Raises
- **ValueError** - An invalid position was given.
- **TypeError** - A bad mix of arguments were passed.
- **Forbidden** - Missing permissions to move the channel.
- **HTTPException** - Moving the channel failed.
```

--------------------------------

### Set bot activity status

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Initialize the client with an activity object to set the bot's status.

```python
client = discord.Client(activity=discord.Game(name="my game"))
```

--------------------------------

### Implement a dynamic command cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses a factory function to conditionally apply cooldowns, bypassing them for specific users like the owner.

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

### discord.PermissionOverwrite.from_pair

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an overwrite instance from an allow/deny pair of Permissions.

```APIDOC
## from_pair(allow, deny)

### Description
Creates an overwrite from an allow/deny pair of Permissions.

### Parameters
- **allow** (Permissions) - The permissions to allow.
- **deny** (Permissions) - The permissions to deny.
```

--------------------------------

### LayoutView.add_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the view.

```APIDOC
## LayoutView.add_item(item)

### Description
Adds an item to the view. Returns the class instance for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to add to the view.

### Raises
- **TypeError** - If an Item was not passed.
- **ValueError** - If the maximum number of children is exceeded or the item is not allowed.
```

--------------------------------

### await edit_widget(enabled, channel, reason)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the widget settings for the guild. Requires manage_guild permission.

```APIDOC
## await edit_widget(enabled, channel, reason)

### Description
Edits the widget of the guild. Requires the manage_guild permission.

### Parameters
- **enabled** (bool) - Whether to enable the widget for the guild.
- **channel** (Optional[Snowflake]) - The new widget channel. None removes the widget channel.
- **reason** (Optional[str]) - The reason for editing this widget, which appears in the audit log.

### Raises
- **Forbidden** - You do not have permission to edit the widget.
- **HTTPException** - Editing the widget failed.
```

--------------------------------

### send()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination channel.

```APIDOC
## send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

### Description
Sends a message to the destination with the content given. This function is a coroutine.

### Parameters
#### Parameters
- **content** (str) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload (max 10).
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload (max 10).
- **stickers** (Sequence) - Optional - A list of stickers to upload (max 3).
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions processed in this message.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the message to which you are replying.
- **mention_author** (bool) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Optional - The poll to send with this message.
```

--------------------------------

### VoiceChannel.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager to send a typing indicator to the destination.

```APIDOC
## typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination. If used with `async with`, it lasts for the duration of the block. If `await` is used, it lasts for 10 seconds.
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

### Messageable.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager to send a typing indicator to the destination.

```APIDOC
## async Messageable.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination. If used as an async context manager, it lasts for the duration of the block. If awaited, it lasts for 10 seconds.
```

--------------------------------

### Use typing.Union for Multiple Converters

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Allows a command parameter to accept multiple types by attempting conversion from left to right.

```python
import typing


@bot.command()
async def union(ctx, what: typing.Union[discord.TextChannel, discord.Member]):
    await ctx.send(what)
```

--------------------------------

### Upload files with send

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Updates file upload syntax to use the discord.File pseudo-namedtuple.

```python
# before
await client.send_file(channel, "cool.png", filename="testing.png", content="Hello")

# after
await channel.send("Hello", file=discord.File("cool.png", "testing.png"))
```

--------------------------------

### Send message to channel

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Fetch a channel by ID and send a message to it.

```python
channel = client.get_channel(12324234183172)
await channel.send("hello")
```

--------------------------------

### Using keyword-only arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Captures the remainder of the input as a single argument, useful for multi-word strings without requiring quotes.

```python
@bot.command()
async def test(ctx, *, arg):
    await ctx.send(arg)
```

--------------------------------

### join

Source: https://discordpy.readthedocs.io/en/latest/api.html

Joins the current thread. Requires send_messages_in_threads permission.

```APIDOC
## join()

### Description
Joins this thread. If the thread is private, manage_threads permission is also required.
```

--------------------------------

### discord.on_guild_stickers_update(guild, before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild updates its stickers. Requires Intents.emojis_and_stickers to be enabled.

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

### VoiceChannel.clone

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clones the channel, creating a new one with the same properties.

```APIDOC
## await clone(*, name=None, category=None, reason=None)

### Description
Clones this channel. This creates a channel with the same properties as this channel. This is a coroutine.

### Parameters
- **name** (str) - Optional - The name of the new channel.
- **category** (CategoryChannel) - Optional - The category for the new channel.
- **reason** (str) - Optional - The reason for cloning this channel.
```

--------------------------------

### discord.ext.commands.when_mentioned

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A callable that implements a command prefix equivalent to being mentioned, intended for use with the Bot.command_prefix attribute.

```APIDOC
## discord.ext.commands.when_mentioned(bot, msg, /)

### Description
A callable that implements a command prefix equivalent to being mentioned. These are meant to be passed into the `Bot.command_prefix` attribute.
```

--------------------------------

### Perform asynchronous HTTP requests

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use aiohttp instead of the requests library to avoid blocking the event loop during network operations.

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

### Configure log level with a FileHandler

Source: https://discordpy.readthedocs.io/en/latest/logging.html

Sets the logging level to DEBUG while using a custom file handler.

```python
import logging

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# Assume client refers to a discord.Client subclass...
client.run(token, log_handler=handler, log_level=logging.DEBUG)
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
- **fail_if_not_exists** (`bool`) - Optional - Whether to raise an exception if the message no longer exists.

### Returns
- `Message` - The message sent to the channel.
```

--------------------------------

### DMChannel.typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous context manager that allows you to send a typing indicator to the destination.

```APIDOC
## async with DMChannel.typing()

### Description
Returns an asynchronous context manager that allows you to send a typing indicator to the destination for an indefinite period of time, or 10 seconds if the context manager is called using await.
```

--------------------------------

### pin(*, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Pins the message to the channel.

```APIDOC
## await pin(*, reason=None)

### Description
Pins the message. Requires pin_messages permission.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message, shown in the audit log.
```

--------------------------------

### Collect subscriptions into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use a list comprehension with an asynchronous iterator to store subscriptions in a list.

```python
subscriptions = [subscription async for subscription in sku.subscriptions(limit=100, user=user)]
# subscriptions is now a list of Subscription...
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
- **roles** (abc.Snowflake) - Required - An argument list of abc.Snowflake representing a Role to give to the member.
- **reason** (str) - Optional - The reason for adding these roles. Shows up on the audit log.
- **atomic** (bool) - Optional - Whether to atomically add roles.
```

--------------------------------

### create_thread

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new thread within the text channel.

```APIDOC
## create_thread(name, message=None, auto_archive_duration=None, type=None, reason=None, invitable=True, slowmode_delay=None)

### Description
Creates a new thread in the text channel. Requires appropriate permissions.

### Parameters
- **name** (str) - Required - The name of the thread.
- **message** (Optional[abc.Snowflake]) - Optional - The message to create the thread with.
- **auto_archive_duration** (int) - Optional - Duration in minutes before the thread is archived (60, 1440, 4320, 10080).
- **type** (Optional[ChannelType]) - Optional - The type of thread to create.
- **reason** (str) - Optional - Reason for the audit log.
- **invitable** (bool) - Optional - Whether non-moderators can add users to the thread.
- **slowmode_delay** (Optional[int]) - Optional - Slowmode rate limit in seconds.

### Returns
- **Thread** - The created thread object.
```

--------------------------------

### Sync guild-specific commands

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Synchronize the command tree for a specific guild after registering guild-restricted commands.

```python
await tree.sync(guild=discord.Object(123456789012345678))
```

--------------------------------

### Migrate to UTC-Aware Datetime

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Update datetime calculations to use UTC-aware objects instead of naive ones to avoid local time errors.

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

### Custom Callable Converter

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

### Receive Discord Member via Converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Demonstrates using a discord.Member type hint to automatically convert a string argument into a Member object.

```python
@bot.command()
async def joined(ctx, *, member: discord.Member):
    await ctx.send(f"{member} joined on {member.joined_at}")
```

--------------------------------

### @discord.ext.commands.after_invoke(coro)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers a coroutine as a post-invoke hook for a command.

```APIDOC
## @discord.ext.commands.after_invoke(coro)

### Description
Registers a coroutine to be executed after the command is invoked.
```

--------------------------------

### discord.on_typing

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when someone begins typing a message.

```APIDOC
## discord.on_typing(channel, user, when)

### Description
Called when someone begins typing a message. This requires Intents.typing to be enabled.

### Parameters
- **channel** (abc.Messageable) - Required - The location where the typing originated from.
- **user** (Union[User, Member]) - Required - The user that started typing.
- **when** (datetime.datetime) - Required - When the typing started as an aware datetime in UTC.
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

### Raises
- **DiscordException** - There was no internal connection state.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
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

### reload_extension(name, *, package=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Atomically reloads an extension, replacing it with a refreshed version.

```APIDOC
## reload_extension(name, *, package=None)

### Description
Atomically reloads an extension. If the operation fails, the bot rolls back to the prior working state.

### Parameters
- **name** (str) - Required - The extension name to reload (dot-separated).
- **package** (Optional[str]) - Optional - The package name to resolve relative imports with.
```

--------------------------------

### Update VoiceClient source volume

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use PCMVolumeTransformer to modify the volume of the current audio source at runtime.

```python
vc.source = discord.PCMVolumeTransformer(vc.source)
vc.source.volume = 0.6
```

--------------------------------

### @discord.app_commands.default_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that sets the default permissions required to execute a command.

```APIDOC
## @discord.app_commands.default_permissions(perms_obj=None, **perms)

### Description
Sets the default permissions needed to execute a command. This serves as a hint to the Discord client; administrators can override these settings.

### Parameters
- **perms_obj** (Permissions) - Optional - A permissions object as a positional argument.
- **perms** (bool) - Optional - Keyword arguments denoting specific permissions to set as default.
```

--------------------------------

### forward(destination, fail_if_not_exists=True)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Forwards the message to a specified channel.

```APIDOC
## await forward(destination, fail_if_not_exists=True)

### Description
Forwards this message to a channel. This is a coroutine.

### Parameters
- **destination** (Messageable) - Required - The channel to forward this message to.
- **fail_if_not_exists** (bool) - Optional - Whether replying using the message reference should raise HTTPException if the message no longer exists.

### Returns
- **Message** - The message sent to the channel.
```

--------------------------------

### fetch_stage_instance

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a StageInstance for a specific stage channel ID.

```APIDOC
## fetch_stage_instance(channel_id)

### Description
Gets a StageInstance for a stage channel id. This function is a coroutine.

### Parameters
- **channel_id** (int) - Required - The stage channel ID.

### Returns
- **StageInstance** - The stage instance from the stage channel ID.
```

--------------------------------

### Inspecting Cog Commands

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Retrieve a list of commands registered to a specific Cog instance using get_commands.

```python
>>> cog = bot.get_cog('Greetings')
>>> commands = cog.get_commands()
>>> print([c.name for c in commands])
```

--------------------------------

### autocomplete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by providing autocomplete choices.

```APIDOC
## await autocomplete(choices)

### Description
Responds to this interaction by giving the user the choices they can use.

### Parameters
- **choices** (List[Choice]) - Required - The list of new choices as the user is typing.
```

--------------------------------

### set_thumbnail(url)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the thumbnail for the embed content. Returns the class instance for chaining.

```APIDOC
### set_thumbnail(url)

#### Parameters
- **url** (str) - Optional - The source URL for the thumbnail.
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

### discord.ui.Section

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI section component that can contain text displays and an accessory.

```APIDOC
## class discord.ui.Section(children, accessory, id=None)

### Description
Represents a UI section. This is a top-level layout component that can only be used on LayoutView.

### Methods
- **add_item(item)**: Adds an item to this section. Returns the class instance for chaining.
- **remove_item(item)**: Removes an item from this section. Returns the class instance for chaining.
- **find_item(id)**: Gets an item with the specified ID, or None if not found.
- **clear_items()**: Removes all items from the section. Returns the class instance for chaining.
- **interaction_check(interaction)**: A coroutine callback to check if an interaction should be processed. Returns bool.
- **walk_children()**: An iterator that recursively walks through all children and the accessory.
```

--------------------------------

### LayoutView.from_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Converts a message's components into a View or LayoutView instance.

```APIDOC
## LayoutView.from_message(message, /, *, timeout=180.0)

### Description
Converts a message's components into a View or LayoutView. This is necessary to modify and edit message components.

### Parameters
- **message** (discord.Message) - Required - The message with components to convert.
- **timeout** (Optional[float]) - Optional - The timeout of the converted view.

### Returns
- **Union[View, LayoutView]** - The converted view instance.
```

--------------------------------

### clear()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Clears the internal state of the bot.

```APIDOC
## clear()

### Description
Clears the internal state of the bot. After this, the bot can be considered “re-opened”.
```

--------------------------------

### Define Windows-style flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a forward-slash prefix and no delimiter for command flags.

```python
class WindowsLikeFlags(commands.FlagConverter, prefix="/", delimiter=""):
    make: str
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
- **name** (Union[str, locale_str]) - Optional - The name of the application command.
- **description** (Union[str, locale_str]) - Optional - The description of the application command shown in the UI.
- **nsfw** (bool) - Optional - Whether the command is NSFW. Defaults to False.
- **guild** (Optional[Snowflake]) - Optional - The guild to add the command to.
- **guilds** (List[Snowflake]) - Optional - The list of guilds to add the command to.
- **auto_locale_strings** (bool) - Optional - Whether to implicitly wrap strings in locale_str. Defaults to True.
- **extras** (dict) - Optional - A dictionary for storing extraneous data.
```

--------------------------------

### discord.on_integration_update(integration)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is updated. Requires Intents.integrations to be enabled.

```APIDOC
## discord.on_integration_update(integration)

### Description
Called when an integration is updated. This requires Intents.integrations to be enabled.

### Parameters
- **integration** (Integration) - The integration that was updated.
```

--------------------------------

### discord.utils.oauth_url

Source: https://discordpy.readthedocs.io/en/latest/api.html

Generates an OAuth2 URL for inviting the bot into guilds.

```APIDOC
## discord.utils.oauth_url(client_id, *, permissions=..., guild=..., redirect_uri=..., scopes=..., disable_guild_select=False, state=...)

### Description
A helper function that returns the OAuth2 URL for inviting the bot into guilds.

### Parameters
- **client_id** (int|str) - Required - The client ID for your bot.
- **permissions** (Permissions) - Optional - The permissions you’re requesting.
- **guild** (Snowflake) - Optional - The guild to pre-select in the authorization screen.
- **redirect_uri** (str) - Optional - An optional valid redirect URI.
- **scopes** (Iterable[str]) - Optional - An optional valid list of scopes.
- **disable_guild_select** (bool) - Optional - Whether to disallow the user from changing the guild dropdown.
- **state** (str) - Optional - The state to return after the authorization.

### Response
- **url** (str) - The OAuth2 URL for inviting the bot into guilds.
```

--------------------------------

### Upload files

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Upload images or files using the File object.

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

### Define a Hybrid Command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the hybrid_command decorator to create a command that can be invoked via text or slash. Remember to manually sync the CommandTree for slash command visibility.

```python
@bot.hybrid_command()
async def test(ctx):
    await ctx.send("This is a hybrid command!")
```

--------------------------------

### Greedy converter usage

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Demonstrates using Greedy to consume multiple arguments of the same type until a different type is encountered.

```python
@commands.command()
async def test(ctx, numbers: Greedy[int], reason: str):
    await ctx.send("numbers: {}, reason: {}".format(numbers, reason))
```

--------------------------------

### discord.ext.commands.Paginator

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A class that aids in paginating code blocks for Discord messages.

```APIDOC
## class discord.ext.commands.Paginator(prefix='```', suffix='```', max_size=2000, linesep='\n')

### Description
A class that aids in paginating code blocks for Discord messages.

### Methods
- **add_line(line='', *, empty=False)**: Adds a line to the current page. Raises RuntimeError if the line exceeds max_size.
- **clear()**: Clears the paginator to have no pages.
- **close_page()**: Prematurely terminate a page.

### Attributes
- **pages**: Returns the rendered list of pages (List[str]).
- **prefix**: The prefix inserted to every page (Optional[str]).
- **suffix**: The suffix appended at the end of every page (Optional[str]).
- **max_size**: The maximum amount of codepoints allowed in a page (int).
- **linesep**: The character string inserted between lines (str).
```

--------------------------------

### @discord.ext.tasks.loop

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

A decorator that schedules a task in the background with optional reconnect logic.

```APIDOC
## @discord.ext.tasks.loop

### Description
A decorator that schedules a task in the background for you with optional reconnect logic. The decorator returns a Loop object.

### Parameters
- **seconds** (float) - Optional - The number of seconds between every iteration.
- **minutes** (float) - Optional - The number of minutes between every iteration.
- **hours** (float) - Optional - The number of hours between every iteration.
- **time** (Union[datetime.time, Sequence[datetime.time]]) - Optional - The exact times to run this loop at.
- **count** (Optional[int]) - Optional - The number of loops to do, None if it should be an infinite loop.
- **reconnect** (bool) - Optional - Whether to handle errors and restart the task.
- **name** (Optional[str]) - Optional - The name to assign to the internal task.
```

--------------------------------

### InteractionResponse.pong

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Pongs the ping interaction.

```APIDOC
## await InteractionResponse.pong()

### Description
Pongs the ping interaction. This should rarely be used.
```

--------------------------------

### Register an autocomplete callback for a command parameter

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use the @autocomplete decorator to provide dynamic suggestions for a command parameter. The callback must return a list of up to 25 Choice objects.

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

### copy_global_to(guild)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Copies all global commands to a specified guild, useful for development and testing.

```APIDOC
## copy_global_to(guild)

### Description
Copies all global commands to the specified guild. This method will override pre-existing guild commands that conflict.

### Parameters
- **guild** (Snowflake) - Required - The guild to copy the commands to.

### Raises
- **CommandLimitReached** - The maximum number of commands was reached for that guild.
```

--------------------------------

### Integration.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the integration settings. Requires the manage_guild permission.

```APIDOC
## [COROUTINE] Integration.edit

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

### Iterate over reaction users

Source: https://discordpy.readthedocs.io/en/latest/api.html

Asynchronously iterate through users who reacted to a message. Note that this can be memory-intensive for large reaction counts.

```python
async for user in reaction.users():
    await channel.send(f"{user} has reacted with {reaction.emoji}!")
```

--------------------------------

### @discord.app_commands.allowed_contexts

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that indicates this command can only be used in certain contexts such as guilds, DMs, and private channels. This is verified server-side by Discord.

```APIDOC
## @discord.app_commands.allowed_contexts(guilds=..., dms=..., private_channels=...)

### Description
Indicates the specific contexts where a command is allowed to be used. This is verified by Discord server-side and does not function as a standard check.

### Parameters
- **guilds** (bool) - Optional - Whether the command is allowed in guilds.
- **dms** (bool) - Optional - Whether the command is allowed in DMs.
- **private_channels** (bool) - Optional - Whether the command is allowed in private channels.
```

--------------------------------

### create_thread()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a public thread from the message. Requires create_public_threads permission.

```APIDOC
## await create_thread(name, auto_archive_duration=..., slowmode_delay=None, reason=None)

### Description
Creates a public thread from this message. The channel must be a TextChannel and the user must have `create_public_threads` permission.

### Parameters
- **name** (`str`) - Required - The name of the thread.
- **auto_archive_duration** (`int`) - Optional - Duration in minutes (60, 1440, 4320, or 10080).
- **slowmode_delay** (`int`) - Optional - Slowmode rate limit in seconds (max 21600).
- **reason** (`str`) - Optional - Reason for creating the thread for the audit log.

### Returns
- `Thread` - The created thread.
```

--------------------------------

### Consume remaining arguments in commands

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the * operator in the command signature to capture all remaining arguments as a single string.

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

### await change_voice_state(channel, self_mute, self_deaf)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Changes the client's voice state within the guild.

```APIDOC
## await change_voice_state(channel, self_mute=False, self_deaf=False)

### Description
Changes the client's voice state in the guild.

### Parameters
- **channel** (Optional[abc.Snowflake]) - Channel the client wants to join. Use None to disconnect.
- **self_mute** (bool) - Indicates if the client should be self-muted.
- **self_deaf** (bool) - Indicates if the client should be self-deafened.
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
- **label** (str) - Required - The label of the option.
- **value** (str) - Optional - The value of the option.
- **description** (Optional[str]) - Optional - An additional description of the option.
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the option.
- **default** (bool) - Optional - Whether this option is selected by default.
```

--------------------------------

### edit(**options)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the channel settings. Requires the manage_channels permission.

```APIDOC
## edit(**options)

### Description
Edits the channel. You must have `manage_channels` permission to perform this action. Returns the newly edited channel object.
```

--------------------------------

### Multiple Attachment Command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Handles a required first attachment and an optional second attachment.

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

await channel.typing()
```
```

--------------------------------

### get_user(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a user with the given ID.

```APIDOC
## get_user(id)

### Description
Returns a user with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[User]** - The user or None if not found.
```

--------------------------------

### await edit(**fields)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the guild. You must have manage_guild permissions.

```APIDOC
## await edit(**fields)

### Description
Edits the guild. You must have manage_guild to edit the guild.

### Parameters
- **name** (str) - The new name of the guild.
- **description** (Optional[str]) - The new description of the guild.
- **icon** (bytes) - A bytes-like object representing the icon.
- **banner** (bytes) - A bytes-like object representing the banner.
- **splash** (bytes) - A bytes-like object representing the invite splash.
- **discovery_splash** (bytes) - A bytes-like object representing the discovery splash.
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
- **callback(interaction)**: Coroutine called when the UI item is interacted with.
- **interaction_check(interaction)**: Coroutine to check if the callback should be processed.
```

--------------------------------

### Configure Default Intents

Source: https://discordpy.readthedocs.io/en/latest/intents.html

Disables specific event types like typing and presences to reduce bot resource usage.

```python
import discord
 intents = discord.Intents.default()
 intents.typing = False
 intents.presences = False

 # Somewhere else:
 # client = discord.Client(intents=intents)
```

--------------------------------

### Register external event listeners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use @bot.listen() to register multiple functions as listeners for the same event.

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

### Update on_voice_state_update signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now accepts a member object and two voice state objects.

```python
async def on_voice_state_update(before, after)
```

```python
async def on_voice_state_update(member, before, after)
```

--------------------------------

### Update on_member_ban signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now receives the guild as the first parameter to handle both User and Member types.

```python
async def on_member_ban(member)
```

```python
async def on_member_ban(guild, user)
```

--------------------------------

### get_soundboard_sound(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a soundboard sound with the given ID.

```APIDOC
## get_soundboard_sound(id)

### Description
Returns a soundboard sound with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[SoundboardSound]** - The soundboard sound or None if not found.
```

--------------------------------

### Iterate over poll voters

Source: https://discordpy.readthedocs.io/en/latest/api.html

Demonstrates how to asynchronously iterate through users who voted for a specific poll answer.

```python
async for voter in poll_answer.voters():
    print(f"{voter} has voted for {poll_answer}!")
```

```python
voters = [voter async for voter in poll_answer.voters()]
# voters is now a list of User
```

--------------------------------

### Compare Enumeration Usage

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Replaces string-based comparisons with discord.py enumeration types to improve API type safety.

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

### create_role(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new role for the guild.

```APIDOC
## create_role(**kwargs)

### Description
Creates a Role for the guild. Requires manage_roles permission.

### Parameters
- **name** (str) - Optional - The role name.
- **permissions** (Permissions) - Optional - The permissions to have.
- **colour** (Union[Colour, int]) - Optional - The colour for the role.
- **hoist** (bool) - Optional - Indicates if the role should be shown separately.
- **display_icon** (Union[bytes, str]) - Optional - Icon for the role.
- **mentionable** (bool) - Optional - Indicates if the role should be mentionable.
- **reason** (Optional[str]) - Optional - The reason for creating this role.

### Returns
- **Role** - The newly created role.
```

--------------------------------

### @discord.ext.commands.max_concurrency(number, per=BucketType.default, *, wait=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Limits the number of concurrent invocations of a command.

```APIDOC
## @discord.ext.commands.max_concurrency(number, per=BucketType.default, *, wait=False)

### Description
Adds a maximum concurrency limit to a command. This prevents a command from being run more than a specified number of times simultaneously.

### Parameters
- **number** (int) - Required - Maximum number of concurrent invocations.
- **per** (BucketType) - Optional - The bucket scope for the concurrency limit.
- **wait** (bool) - Optional - Whether to wait for the queue to clear or raise MaxConcurrencyReached.
```

--------------------------------

### select(cls, options, channel_types, placeholder, custom_id, min_values, max_values, disabled, default_values, id)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a select menu to the action row. The decorated function receives the ActionRow instance, the Interaction, and the select class instance.

```APIDOC
## Method: select

### Description
A decorator that attaches a select menu to the action row. The function being decorated should have three parameters: `self` (the `discord.ui.ActionRow`), the `discord.Interaction`, and the chosen select class.

### Parameters
- **cls** (Union[Type[discord.ui.Select], ...]) - Optional - The class to use for the select menu. Defaults to `discord.ui.Select`.
- **placeholder** (Optional[str]) - Optional - The placeholder text shown if nothing is selected (max 150 chars).
- **custom_id** (str) - Optional - The ID of the select menu received during interaction (max 100 chars).
- **min_values** (int) - Optional - Minimum number of items to be chosen (0-25). Defaults to 1.
- **max_values** (int) - Optional - Maximum number of items to be chosen (1-25). Defaults to 1.
- **options** (List[discord.SelectOption]) - Optional - List of options for standard `Select` instances (max 25 items).
- **channel_types** (List[ChannelType]) - Optional - Types of channels to show for `ChannelSelect` instances.
- **disabled** (bool) - Optional - Whether the select is disabled. Defaults to `False`.
- **default_values** (Sequence[Snowflake]) - Optional - Default values for the select menu.
- **id** (Optional[int]) - Optional - Unique ID of the component.

### Example
```python
class MyView(discord.ui.LayoutView):
    action_row = discord.ui.ActionRow()

    @action_row.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
        return await interaction.response.send_message(f'You selected {select.values[0].mention}')
```
```

--------------------------------

### Attach a view to an interaction response

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use this pattern to associate a view with an interaction response message by retrieving the resource from the callback.

```python
@tree.command()
async def more_timeout_example(interaction):
    """Another example to showcase disabling buttons on timing out"""
    view = MyView()
    callback = await interaction.response.send_message('Press me!', view=view)

    # Step 1
    resource = callback.resource
    # making sure it's an interaction response message
    if isinstance(resource, discord.InteractionMessage):
        view.message = resource
```

--------------------------------

### audit_logs(*, limit=100, before=..., after=..., oldest_first=..., user=..., action=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator that enables receiving the guild's audit logs. Requires 'view_audit_log' permission.

```APIDOC
## audit_logs(*, limit=100, before=..., after=..., oldest_first=..., user=..., action=...)

### Description
Returns an asynchronous iterator that enables receiving the guild's audit logs. You must have 'view_audit_log' to do this.
```

--------------------------------

### walk_commands()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

An iterator that recursively traverses all registered commands and subcommands.

```APIDOC
## walk_commands()

### Description
An iterator that recursively walks through all commands and subcommands.

### Yields
- **Union[Command, Group]** - A command or group from the internal list of commands.
```

--------------------------------

### Autocomplete Callback Implementation

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Associates a parameter with an autocomplete function. Autocomplete is limited to str, int, or float types.

```python
async def fruit_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    fruits = ["Banana", "Pineapple", "Apple", "Watermelon", "Melon", "Cherry"]
    return [app_commands.Choice(name=fruit, value=fruit) for fruit in fruits if current.lower() in fruit.lower()]


@app_commands.command()
@app_commands.autocomplete(fruit=fruit_autocomplete)
async def fruits(interaction: discord.Interaction, fruit: str):
    await interaction.response.send_message(f"Your favourite fruit seems to be {fruit}")
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

### Create an Abstract Cog Mixin

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Combine CogMeta with other metaclasses like abc.ABCMeta to create abstract mixin classes for cogs.

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

### Register a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Add an instance of a cog to the bot using the add_cog method.

```python
await bot.add_cog(Greetings(bot))
```

--------------------------------

### invoke(ctx)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Invokes the command given under the invocation context. This is a coroutine.

```APIDOC
## invoke(ctx)

### Description
Invokes the command given under the invocation context and handles all internal event dispatch mechanisms.

### Parameters
- **ctx** (Context) - Required - The invocation context to invoke.

### Returns
- **None**
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

### discord.on_raw_app_command_permissions_update(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Event handler called when application command permissions are updated.

```APIDOC
## discord.on_raw_app_command_permissions_update(payload)

### Description
Called when application command permissions are updated.

### Parameters
- **payload** (RawAppCommandPermissionsUpdateEvent) - Required - The raw event payload data.
```

--------------------------------

### VoiceChannel.send_sound

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a soundboard sound for this channel. Requires speak and use_soundboard permissions.

```APIDOC
## await send_sound(sound)

### Description
Sends a soundboard sound for this channel. This is a coroutine.

### Parameters
- **sound** (Union[SoundboardSound, SoundboardDefaultSound]) - Required - The sound to send for this channel.
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

### edit(*, reason=None, **options)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Updates the settings and properties of the forum channel. Requires manage_channels permission.

```APIDOC
### Method
await edit(*, reason=None, **options)

### Description
Edits the forum. You must have manage_channels to do this.

### Parameters
- **name** (str) - Optional - The new forum name.
- **topic** (str) - Optional - The new forum’s topic.
- **position** (int) - Optional - The new forum’s position.
- **nsfw** (bool) - Optional - To mark the forum as NSFW or not.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the forum’s new or pre-existing category.
- **category** (Optional[CategoryChannel]) - Optional - The new category for this forum.
- **slowmode_delay** (int) - Optional - Specifies the slowmode rate limit for user in this forum.
- **type** (ChannelType) - Optional - Change the type of this text forum.
- **reason** (Optional[str]) - Optional - The reason for editing this forum.
- **overwrites** (Mapping) - Optional - A Mapping of target to PermissionOverwrite.
- **default_auto_archive_duration** (int) - Optional - The new default auto archive duration in minutes.
- **available_tags** (Sequence[ForumTag]) - Optional - The new available tags for this forum.
- **default_thread_slowmode_delay** (int) - Optional - The new default slowmode delay for threads.
- **default_reaction_emoji** (Optional[Union[Emoji, PartialEmoji, str]]) - Optional - The new default reaction emoji.
- **default_layout** (ForumLayoutType) - Optional - The new default layout for posts.
- **default_sort_order** (Optional[ForumOrderType]) - Optional - The new default sort order for posts.
- **require_tag** (bool) - Optional - Whether to require a tag for threads.
```

--------------------------------

### @discord.ui.select

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a select menu to a component within a discord.ui.View. The decorated function receives the interaction and the select instance as arguments.

```APIDOC
## @discord.ui.select

### Description
A decorator that attaches a select menu to a component. The function being decorated should have three parameters: self (the View), the Interaction, and the chosen select class.

### Parameters
- **cls** (discord.ui.select.Select) - Optional - The class to use for the select menu.
- **options** (List) - Optional - The options available in the select menu.
- **channel_types** (List) - Optional - The types of channels allowed for ChannelSelect.
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

### edit(reason=None, **options)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the channel properties. Requires the 'manage_channels' permission.

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
- **sync_permissions** (`bool`) - Optional - Whether to sync permissions with the channel’s new or pre-existing category.
- **category** (`Optional[CategoryChannel]`) - Optional - The new category for this channel.
- **slowmode_delay** (`int`) - Optional - Specifies the slowmode rate limit for user in this channel, in seconds.
- **reason** (`Optional[str]`) - Optional - The reason for editing this channel.
- **overwrites** (`Mapping`) - Optional - A `Mapping` of target to `PermissionOverwrite`.
- **rtc_region** (`Optional[str]`) - Optional - The new region for the stage channel’s voice communication.
- **video_quality_mode** (`VideoQualityMode`) - Optional - The camera video quality for the stage channel’s participants.

### Returns
- `Optional[StageChannel]` - The newly edited stage channel.
```

--------------------------------

### Optional Attachment Command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Handles a single optional attachment in a command.

```python
@bot.command()
async def upload(ctx, attachment: typing.Optional[discord.Attachment]):
    if attachment is None:
        await ctx.send("You did not upload anything!")
    else:
        await ctx.send(f"You have uploaded <{attachment.url}>")
```

--------------------------------

### await unpin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unpins the message in the channel.

```APIDOC
## await unpin(reason=None)

### Description
Unpins the message. Requires `pin_messages` permission.

### Parameters
- **reason** (str) - Optional - Reason for the audit log.
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

### Restricting Commands by Permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses has_permissions to verify the invoker has specific Discord permissions before executing the command.

```python
@tree.command()
@app_commands.checks.has_permissions(manage_messages=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("You can manage messages.")
```

--------------------------------

### change_presence(*, activity=None, status=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Changes the client’s presence.

```APIDOC
## change_presence(*, activity=None, status=None)

### Description
Changes the client’s presence.

### Parameters
- **activity** (Optional[BaseActivity]) - Optional - The activity being done.
- **status** (Optional[Status]) - Optional - Indicates what status to change to.

### Raises
- **TypeError** - If the activity parameter is not the proper type.
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

### ActionRow.button

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Decorator to attach a button to the action row.

```APIDOC
## button(label=None, custom_id=None, disabled=False, style=ButtonStyle.secondary, emoji=None, id=None)

### Description
A decorator that attaches a button to the action row. The function being decorated should have three parameters: self, interaction, and button.

### Parameters
- **label** (Optional[str]) - Optional - The label of the button.
- **custom_id** (Optional[str]) - Optional - The ID of the button received during interaction.
- **style** (ButtonStyle) - Optional - The style of the button.
- **disabled** (bool) - Optional - Whether the button is disabled.
- **emoji** (Optional[Union[str, Emoji, PartialEmoji]]) - Optional - The emoji of the button.
- **id** (Optional[int]) - Optional - The ID of the component.
```

--------------------------------

### leave

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the current thread.

```APIDOC
## leave()

### Description
Leaves this thread.
```

--------------------------------

### history(*, limit=100, before=None, after=None, around=None, oldest_first=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator for the channel's message history.

```APIDOC
## history(*, limit=100, before=None, after=None, around=None, oldest_first=None)

### Description
Returns an asynchronous iterator to receive the channel's message history. Requires read_message_history permission.

### Parameters
- **limit** (Optional[int]) - Optional - Number of messages to retrieve.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this date or message.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this date or message.
- **around** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this date or message.
- **oldest_first** (Optional[bool]) - Optional - If True, returns messages in oldest to newest order.

### Yields
- **Message** - The parsed message data.
```

--------------------------------

### Define a GroupCog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Create a cog that functions as an application command group by inheriting from commands.GroupCog.

```python
from discord import app_commands
from discord.ext import commands


@app_commands.guild_only()
class MyCog(commands.GroupCog, group_name="my-cog"):
    pass
```

--------------------------------

### @discord.app_commands.autocomplete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Associates specific parameters of a command with an autocomplete callback function. This is supported for parameters with str, int, or float types.

```APIDOC
## @discord.app_commands.autocomplete(**parameters)

### Description
Associates the given parameters with the given autocomplete callback. Autocomplete is only supported on types that have str, int, or float values.

### Parameters
- **parameters** (dict) - The parameters to mark as autocomplete.

### Raises
- **TypeError** - The parameter name is not found or the parameter type was incorrect.
```

--------------------------------

### reply(content=None, **kwargs)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Sends a reply to the message.

```APIDOC
## await reply(content=None, **kwargs)

### Description
A shortcut method to abc.Messageable.send() to reply to the Message. This is a coroutine.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### Listen for messages without blocking commands

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use the @bot.listen decorator to handle events without needing to manually process commands.

```python
@bot.listen('on_message')
async def whatever_you_want_to_call_it(message):
    # do stuff here
    # do not process commands here
```

--------------------------------

### User.history()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator for receiving the destination's message history.

```APIDOC
## async for ... in User.history()

### Description
Returns an asynchronous iterator that enables receiving the destination’s message history. You must have read_message_history to do this.

### Parameters
- **limit** (int) - Optional - The number of messages to retrieve (default 100).
- **before** (datetime) - Optional - Retrieve messages before this date.
- **after** (datetime) - Optional - Retrieve messages after this date.
- **around** (datetime) - Optional - Retrieve messages around this date.
- **oldest_first** (bool) - Optional - Whether to return messages in oldest to newest order.
```

--------------------------------

### Define a Cog Class

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Create a class inheriting from commands.Cog to encapsulate commands and listeners. Ensure all commands include a self parameter.

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

### discord.ui.View

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI view that must be inherited to create a UI within Discord. It manages a collection of UI items and their interactions.

```APIDOC
## class discord.ui.View(timeout=180.0)

### Description
Represents a UI view. This object must be inherited to create a UI within Discord.

### Parameters
- **timeout** (Optional[float]) - Optional - Timeout in seconds from last interaction with the UI before no longer accepting input. If None then there is no timeout.
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

### Retrieve all accessible channels

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Iterates through all guilds and their channels to yield every channel the client can access.

```python
for guild in client.guilds:
    for channel in guild.channels:
        yield channel
```

--------------------------------

### unpin

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Unpins the message. This is a coroutine.

```APIDOC
## await unpin(reason=None)

### Description
Unpins the message. Requires pin_messages permission in a non-private channel context.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for unpinning the message, which shows up on the audit log.

### Raises
- **Forbidden** - You do not have permissions to unpin the message.
- **NotFound** - The message or channel was not found or deleted.
- **HTTPException** - Unpinning the message failed.
```

--------------------------------

### await _fetch_roles()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all roles associated with the guild.

```APIDOC
## await _fetch_roles()

### Description
Retrieves all `Role`s that the guild has. For general usage, consider `roles` instead.

### Returns
- **List[Role]** - All roles in the guild.

### Raises
- **HTTPException** - Retrieving the roles failed.
```

--------------------------------

### move(**kwargs)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine to move a channel relative to other channels. Requires manage_channels permission.

```APIDOC
## move(**kwargs)

### Description
A coroutine to move a channel relative to other channels. Requires manage_channels permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning of the list.
- **end** (bool) - Optional - Move to the end of the list.
- **before** (Snowflake) - Optional - Move before the given channel.
- **after** (Snowflake) - Optional - Move after the given channel.
- **offset** (int) - Optional - Number of channels to offset the move by.
- **category** (Optional[Snowflake]) - Optional - The category to move this channel under.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the category.
- **reason** (str) - Optional - The reason for the move.
```

--------------------------------

### SKU.subscriptions(limit=50, before=None, after=None, user=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of subscriptions associated with the SKU.

```APIDOC
## async for ... in SKU.subscriptions(limit=50, before=None, after=None, user=None)

### Description
Retrieves an asynchronous iterator of the `Subscription` that the SKU has.

### Parameters
- **limit** (`Optional[int]`) - Optional - The number of subscriptions to retrieve. Defaults to 100.
- **before** (`Optional[Union[Snowflake, datetime.datetime]]`) - Optional - Retrieve subscriptions before this date or entitlement.
- **after** (`Optional[Union[Snowflake, datetime.datetime]]`) - Optional - Retrieve subscriptions after this date or entitlement.
- **user** (`Snowflake`) - Optional - The user to filter by.

### Yields
- `Subscription` - The subscription with the SKU.

### Raises
- **HTTPException** - Fetching the subscriptions failed.
- **TypeError** - Both `after` and `before` were provided.
```

--------------------------------

### Use typing.Optional for Default Values

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Enables back-referencing behavior where a failed conversion results in the parameter receiving a default value.

```python
import typing


@bot.command()
async def bottles(ctx, amount: typing.Optional[int] = 99, *, liquid="beer"):
    await ctx.send(f"{amount} bottles of {liquid} on the wall!")
```

--------------------------------

### fetch_members(limit=1000, after=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator that enables receiving the guild’s members.

```APIDOC
## async for ... in fetch_members()

### Description
Retrieves an asynchronous iterator that enables receiving the guild’s members. Requires `Intents.members()` to be enabled.

### Parameters
- **limit** (Optional[int]) - Optional - The number of members to retrieve. Defaults to 1000.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve members after this date or object.

### Yields
- **Member** - The member with the member data parsed.
```

--------------------------------

### pin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Pins the message to the channel.

```APIDOC
## await pin(reason=None)

### Description
Pins the message. Requires pin_messages permission in non-private channel context. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message, which shows up on the audit log.
```

--------------------------------

### translate()

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

### fetch_ban(user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the BanEntry for a user.

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

### @autocomplete(name)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that registers a coroutine as an autocomplete prompt for a specific command parameter.

```APIDOC
## @autocomplete(name)

### Description
Registers a coroutine to provide autocomplete suggestions for a command parameter. The callback must accept an `Interaction` and the current user input string, returning a list of `Choice` objects.

### Parameters
- **name** (str) - Required - The parameter name to register as autocomplete.
```

--------------------------------

### fetch_voice()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the current voice state from the member.

```APIDOC
## fetch_voice()

### Description
Retrieves the current voice state from this member.

### Returns
- **VoiceState** - The current voice state of the member.
```

--------------------------------

### Register a global check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the @bot.check decorator to apply a check to every command registered with the bot.

```python
@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None
```

--------------------------------

### Register a Call-Once Global Check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a global check that executes only once per invoke call, bypassing repeated checks during command execution.

```python
@bot.check_once
def whitelist(ctx):
    return ctx.message.author.id in my_whitelist
```

--------------------------------

### vanity_invite()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the guild's special vanity invite. Requires 'manage_guild' permission.

```APIDOC
## vanity_invite()

### Description
Returns the guild's special vanity invite. The guild must have 'VANITY_URL' in features. You must have 'manage_guild' to do this.

### Raises
- **Forbidden** - You do not have the proper permissions to get this.
- **HTTPException** - Retrieving the vanity invite failed.

### Returns
- **Optional[Invite]** - The special vanity invite. If None then the guild does not have a vanity invite set.
```

--------------------------------

### create_automod_rule()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates an automod rule for the guild. Requires Permissions.manage_guild.

```APIDOC
## create_automod_rule(name, event_type, trigger, actions, enabled=False, exempt_roles=..., exempt_channels=..., reason=...)

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

### Returns
- **AutoModRule** - The automod rule that was created.
```

--------------------------------

### fetch_application_emojis

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves all emojis for the current application.

```APIDOC
## fetch_application_emojis()

### Description
Retrieves all emojis for the current application.

### Returns
- **List[Emoji]** - The list of emojis for the current application.
```

--------------------------------

### Asset.read()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the asset as a bytes object.

```APIDOC
## await Asset.read()

### Description
Retrieves the content of this asset as a `bytes` object.

### Returns
- **bytes** - The content of the asset.

### Raises
- **DiscordException** - There was no internal connection state.
- **HTTPException** - Downloading the asset failed.
- **NotFound** - The asset was deleted.
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

### send(content=..., ...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the channel. This method supports various parameters including embeds, files, stickers, and polls.

```APIDOC
## send(content, ...)

### Description
Sends a message to the channel. Returns the sent Message object.

### Parameters
- **content** (str) - Optional - The content of the message to send.
- **tts** (bool) - Required - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Required - The rich embed for the content.
- **embeds** (List[Embed]) - Required - A list of embeds to upload (max 10).
- **file** (File) - Required - The file to upload.
- **files** (List[File]) - Required - A list of files to upload (max 10).
- **nonce** (int) - Required - The nonce to use for sending this message.
- **delete_after** (float) - Required - Seconds to wait before deleting the message.
- **allowed_mentions** (AllowedMentions) - Required - Controls mentions processed in the message.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Required - A reference to the message to which you are replying.
- **mention_author** (bool) - Optional - Overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Required - A Discord UI View to add to the message.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Required - A list of stickers to upload (max 3).
- **suppress_embeds** (bool) - Required - Whether to suppress embeds for the message.
- **silent** (bool) - Required - Whether to suppress push and desktop notifications.
- **poll** (Poll) - Required - The poll to send with this message.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### create_thread

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Creates a public thread from the interaction message.

```APIDOC
## create_thread(name, auto_archive_duration=..., slowmode_delay=None, reason=None)

### Description
Creates a public thread from this message. Requires `create_public_threads` permission and must be in a `TextChannel`.

### Parameters
- **name** (str) - Required - The name of the thread.
- **auto_archive_duration** (int) - Optional - Duration in minutes (60, 1440, 4320, or 10080).
- **slowmode_delay** (Optional[int]) - Optional - Slowmode rate limit in seconds (max 21600).
- **reason** (Optional[str]) - Optional - Reason for the audit log.

### Returns
- **Thread** - The created thread.
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

### SyncWebhookMessage.add_files

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds new files to the end of the message attachments.

```APIDOC
## add_files(*files)

### Description
Adds new files to the end of the message attachments and returns the updated message.

### Parameters
- **files** (File) - Required - New files to add to the message.
```

--------------------------------

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a User. Since partial messageables cannot reasonably have the concept of permissions, this will always return Permissions.none().

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for a `User`. This function is there for compatibility with other channel types.

### Parameters
- **obj** (`User`) - Required - The user to check permissions for. This parameter is ignored but kept for compatibility.

### Returns
- `Permissions` - The resolved permissions.
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

### fetch_guild

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a guild by its ID.

```APIDOC
## fetch_guild(guild_id, with_counts=True)

### Description
Retrieves a `Guild` from an ID.

### Parameters
- **guild_id** (int) - Required - The guild’s ID to fetch from.
- **with_counts** (bool) - Optional - Whether to include count information in the guild. Defaults to `True`.

### Returns
- **Guild** - The guild from the ID.
```

--------------------------------

### stop()

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Gracefully stops the task from running, allowing the current iteration to finish.

```APIDOC
## stop()

### Description
Gracefully stops the task from running. Unlike cancel(), this allows the task to finish its current iteration before gracefully exiting.
```

--------------------------------

### delete(reason=None, prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the webhook. This is a coroutine.

```APIDOC
## delete(reason=None, prefer_auth=True)

### Description
Deletes this Webhook.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this webhook. Shows up on the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### Retrieve all visible members

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Iterates through all guilds and their members to yield every member the client can see.

```python
for guild in client.guilds:
    for member in guild.members:
        yield member
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

### ForumChannel.move

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves the channel relative to other channels. Requires manage_channels permission.

```APIDOC
## move(beginning=False, end=False, before=None, after=None, offset=0, category=None, sync_permissions=False, reason=None)

### Description
A coroutine to move a channel relative to other channels. If exact position movement is required, use edit instead.

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

### discord.PermissionOverwrite.update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bulk updates the permission overwrite object using keyword arguments.

```APIDOC
## update(**kwargs)

### Description
Bulk updates this permission overwrite object. Allows you to set multiple attributes by using keyword arguments.

### Parameters
- **kwargs** (dict) - A list of key/value pairs to bulk update with.
```

--------------------------------

### edit(reason=None, name=..., avatar=..., channel=None, prefer_auth=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the webhook. This is a coroutine.

```APIDOC
## edit(reason=None, name=..., avatar=..., channel=None, prefer_auth=True)

### Description
Edits this Webhook.

### Parameters
- **name** (Optional[str]) - Optional - The webhook’s new default name.
- **avatar** (Optional[bytes]) - Optional - A bytes-like object representing the webhook’s new default avatar.
- **channel** (Optional[abc.Snowflake]) - Optional - The webhook’s new channel. This requires an authenticated webhook.
- **reason** (Optional[str]) - Optional - The reason for editing this webhook. Shows up on the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token if available. Defaults to True.
```

--------------------------------

### Define case-insensitive settings flags

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Configures a flag converter to be case-insensitive with multiple optional fields.

```python
class Settings(commands.FlagConverter, case_insensitive=True):
    topic: Optional[str]
    nsfw: Optional[bool]
    slowmode: Optional[int]
```

--------------------------------

### Implement an inline advanced converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a classmethod named convert within the target type to handle conversion logic directly.

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

### discord.ext.commands.check_any

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A check that passes if any of the provided checks pass (logical OR).

```APIDOC
## @discord.ext.commands.check_any(*checks)

### Description
A check that passes if any of the checks passed will pass, i.e. using logical OR. If all checks fail, CheckAnyFailure is raised.

### Parameters
- ***checks** (Callable[[Context], bool]) - Required - An argument list of checks that have been decorated with the check() decorator.
```

--------------------------------

### reply

Source: https://discordpy.readthedocs.io/en/latest/api.html

A shortcut method to abc.Messageable.send() to reply to the Message.

```APIDOC
## await reply(content=None, **kwargs)

### Description
A shortcut method to `abc.Messageable.send()` to reply to the `Message`.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### leave()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Leaves the group. If the user is the only one in the group, this deletes it as well.

```APIDOC
## await leave()

### Description
Leave the group. If you are the only one in the group, this deletes it as well.

### Raises
- **HTTPException** - Leaving the group failed.
```

--------------------------------

### View.from_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Converts a message’s components into a View or LayoutView.

```APIDOC
## classmethod from_message(message, /, *, timeout=180.0)

### Description
Converts a message’s components into a View or LayoutView. This is required to modify and edit message components.

### Parameters
- **message** (discord.Message) - Required - The message with components to convert into a view.
- **timeout** (Optional[float]) - Optional - The timeout of the converted view.
```

--------------------------------

### @client.event

Source: https://discordpy.readthedocs.io/en/latest/api.html

A decorator used to register a coroutine as an event listener for the client.

```APIDOC
## @client.event

### Description
Registers a coroutine to listen for specific Discord gateway events. The decorated function must be a coroutine.

### Example
```python
@client.event
async def on_ready():
    print('Ready!')
```

### Raises
- **TypeError** - Raised if the decorated function is not a coroutine.
```

--------------------------------

### Replace time.sleep with asyncio.sleep

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use asyncio.sleep instead of time.sleep to prevent blocking the event loop and freezing the bot.

```python
import asyncio

async def my_task():
    await asyncio.sleep(5)  # Non-blocking sleep
```

--------------------------------

### Modal.on_submit

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine called when the modal is submitted.

```APIDOC
## await on_submit(interaction)

### Description
Called when the modal is submitted.

### Parameters
- **interaction** (Interaction) - Required - The interaction that submitted this modal.
```

--------------------------------

### AppCommand.edit()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the application command with the provided parameters.

```APIDOC
## await AppCommand.edit(*, name=..., description=..., default_member_permissions=..., dm_permission=..., options=...)

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

### Raises
- **NotFound** - The application command was not found.
- **Forbidden** - You do not have permission to edit this application command.
- **HTTPException** - Editing the application command failed.
- **MissingApplicationID** - The client does not have an application ID.
```

--------------------------------

### change_presence(activity=None, status=None, shard_id=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Changes the client's presence status and activity.

```APIDOC
## change_presence(activity=None, status=None, shard_id=None)

### Description
Changes the client's presence.

### Parameters
- **activity** (Activity) - Optional - The activity to set.
- **status** (Status) - Optional - The status to set.
- **shard_id** (int) - Optional - The specific shard ID to update.
```

--------------------------------

### discord.PermissionOverwrite.pair

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the (allow, deny) pair from the permission overwrite object.

```APIDOC
## pair()

### Description
Returns the (allow, deny) pair from this overwrite.

### Returns
- **Tuple[Permissions, Permissions]** - The allow and deny permission sets.
```

--------------------------------

### Basic FlagConverter Implementation

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Defines a FlagConverter class to parse user-friendly flags in commands.

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

### MemberCacheFlags.all()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance with all flags enabled.

```APIDOC
## MemberCacheFlags.all()

### Description
A factory method that creates a MemberCacheFlags with everything enabled.

### Returns
- **MemberCacheFlags** - The resulting member cache flags.
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

### send_modal

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by sending a modal.

```APIDOC
## await send_modal(modal)

### Description
Responds to this interaction by sending a modal.

### Parameters
- **modal** (Modal) - Required - The modal to send.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### Retrieve pinned messages as a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Shows how to collect pinned messages into a list using a list comprehension with an asynchronous iterator.

```python
messages = [message async for message in channel.pins(limit=50)]
# messages is now a list of Message...
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

### ShardInfo.reconnect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects and then connects the shard again.

```APIDOC
## await ShardInfo.reconnect()

### Description
Disconnects and then connects the shard again.
```

--------------------------------

### Updating Converter metaclasses

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Adjustments required for custom metaclasses when inheriting from Converter due to the transition to typing.Protocol.

```python
# before
class SomeConverterMeta(type): ...


class SomeConverter(commands.Converter, metaclass=SomeConverterMeta): ...


# after
class SomeConverterMeta(type(commands.Converter)): ...


class SomeConverter(commands.Converter, metaclass=SomeConverterMeta): ...
```

--------------------------------

### VoiceChannel.webhooks

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the list of webhooks for the channel.

```APIDOC
## webhooks()

### Description
Gets the list of webhooks from this channel. Requires `manage_webhooks` permission.

### Returns
- **List[Webhook]** - The webhooks for this channel.

### Raises
- **Forbidden** - Missing permissions.
```

--------------------------------

### close()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Closes the connection to Discord.

```APIDOC
## close()

### Description
Closes the connection to Discord.
```

--------------------------------

### app_commands.Group

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A class that implements an application command group. These are usually inherited to define command structures.

```APIDOC
## class app_commands.Group

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

### discord.utils.get(iterable, **attrs)

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

### Implement a local command error handler

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the .error decorator to handle specific command failures, such as CheckFailure, locally for a single command.

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

### discord.app_commands.ContextMenu.add_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds a check to the command to determine if the callback should be executed.

```APIDOC
## add_check(func)

### Description
Adds a check to the command. This is the non-decorator interface to check().

### Parameters
- **func** (callable) - Required - The function that will be used as a check.
```

--------------------------------

### fetch_sticker

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a custom sticker from the guild by ID.

```APIDOC
## await fetch_sticker(sticker_id)

### Description
Retrieves a custom `Sticker` from the guild.

### Parameters
- **sticker_id** (int) - Required - The sticker’s ID.

### Errors
- **NotFound**: The sticker requested could not be found.
- **HTTPException**: An error occurred fetching the sticker.

### Response
- **Returns**: GuildSticker
```

--------------------------------

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a User. This function is for compatibility with other channel types and returns all text-related permissions set to True, with specific exceptions for DMs.

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for a User. This function is there for compatibility with other channel types. Actual direct messages do not really have the concept of permissions.

### Parameters
- **obj** (Snowflake) - Required - The user to check permissions for.

### Returns
- **Permissions** - The resolved permissions for the user.
```

--------------------------------

### Define a Custom Transformer

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Implement a custom transformer by inheriting from app_commands.Transformer and overriding the transform method to convert raw input into a specific type.

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

### Define a basic FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Basic structure for a FlagConverter class with positional and keyword flags.

```python
class Greeting(commands.FlagConverter):
    text: str = commands.flag(positional=True)
    bold: bool = False
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

### SoundboardSound.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the soundboard sound. Requires manage_expressions permission or specific ownership permissions.

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

### discord.ui.Separator

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI separator component used for layout spacing and visibility.

```APIDOC
## class discord.ui.Separator(*, visible=True, spacing=SeparatorSpacing.small, id=None)

### Description
Represents a UI separator. This is a top-level layout component that can only be used on LayoutView.

### Properties
- **id** (Optional[int]): The ID of this separator.
- **visible** (bool): Whether this separator is visible.
- **spacing** (SeparatorSpacing): The spacing of this separator.
```

--------------------------------

### discord.utils.find(predicate, iterable)

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

### add_dynamic_items(*items)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers DynamicItem classes for persistent listening.

```APIDOC
## add_dynamic_items(*items)

### Description
Registers DynamicItem classes for persistent listening. This method accepts class types rather than instances.

### Parameters
- **items** (Type[DynamicItem]) - Required - The classes of dynamic items to add.

### Raises
- **TypeError** - A class is not a subclass of DynamicItem.
```

--------------------------------

### Register an event listener

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use the @client.event decorator to register a coroutine as an event listener.

```python
@client.event
async def on_ready():
    print("Ready!")
```

--------------------------------

### Reaction.users(limit=None, after=None, type=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator of users who have reacted with this emoji.

```APIDOC
## async for user in Reaction.users(*, limit=None, after=None, type=None)

### Description
Returns an asynchronous iterator representing the users that have reacted to the message.

### Parameters
- **limit** (int) - Optional - The maximum number of users to retrieve.
- **after** (abc.Snowflake) - Optional - Retrieve users after this specific user.
- **type** (ReactionType) - Optional - The type of reaction to filter by.
```

--------------------------------

### Modal.add_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the view. This function returns the class instance to allow for fluent-style chaining.

```APIDOC
## add_item(item)

### Description
Adds an item to the view. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to add to the view.

### Raises
- **TypeError** - An Item was not passed.
- **ValueError** - Maximum number of children has been exceeded, the row the item is trying to be added to is full or the item you tried to add is not allowed in this View.
```

--------------------------------

### Send messages with embeds

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Demonstrates sending a message containing an embed using the updated send method.

```python
e = discord.Embed(title="foo")
await channel.send("Hello", embed=e)
```

--------------------------------

### send(content=None, *, ...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that sends a message to the destination with the provided content.

```APIDOC
## await send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, ephemeral=False, silent=False, poll=None)

### Description
Sends a message to the destination with the content given. For interaction based contexts, this uses send_message() if no response has been given, or a followup message if a response has been given.
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

### Update Command Event Signatures

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Event signatures for command lifecycle events have been updated to prioritize the context object.

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

### PartialEmoji.read

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the emoji asset as a bytes object.

```APIDOC
## await PartialEmoji.read()

### Description
Retrieves the content of this asset as a bytes object. This is a coroutine.

### Returns
- **bytes** - The content of the asset.
```

--------------------------------

### fetch_channel

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a channel by its ID.

```APIDOC
## fetch_channel(channel_id)

### Description
Retrieves a `abc.GuildChannel`, `abc.PrivateChannel`, or `Thread` with the specified ID.

### Parameters
- **channel_id** (int) - Required - The ID of the channel to fetch.

### Returns
- **Union[abc.GuildChannel, abc.PrivateChannel, Thread]** - The channel from the ID.
```

--------------------------------

### Retrieve Guild Audit Logs

Source: https://discordpy.readthedocs.io/en/latest/api.html

Asynchronous iteration over guild audit logs with support for filtering by limit, action, or user.

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

### purge(*, limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Purges a list of messages that meet the criteria given by the predicate check. Requires manage_messages and read_message_history permissions.

```APIDOC
## purge(*, limit=100, check=..., before=None, after=None, around=None, oldest_first=None, bulk=True, reason=None)

### Description
Purges a list of messages that meet the criteria given by the predicate check. If a check is not provided then all messages are deleted without discrimination.

### Parameters
- **limit** (int) - Optional - The maximum number of messages to search through.
- **check** (callable) - Optional - A predicate to check if a message should be deleted.
- **reason** (Optional[str]) - Optional - The reason for deleting the messages.
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
- **fp** (Union[io.BufferedIOBase, os.PathLike]) - Required - The file-like object to save this asset to or the filename to use.
- **seek_begin** (bool) - Optional - Whether to seek to the beginning of the file after saving is successfully done.

### Returns
- **int** - The number of bytes written.
```

--------------------------------

### discord.Client

Source: https://discordpy.readthedocs.io/en/latest/api.html

The Client class represents a connection to Discord, providing methods to interact with the Discord WebSocket and API.

```APIDOC
## class discord.Client(intents, **options)

### Description
Represents a client connection that connects to Discord. This class is used to interact with the Discord WebSocket and API.

### Usage
```python
async with discord.Client(intents=intents) as client:
    await client.start('token')
```

### Attributes
- **activity**: The current activity of the client.
- **intents**: The intents used for the connection.
- **user**: The user object representing the client.
- **guilds**: A list of guilds the client is connected to.

### Methods
- **async start(token)**: Starts the client connection.
- **async close()**: Closes the client connection.
- **async change_presence(activity, status)**: Changes the client's presence.
```

--------------------------------

### Define Parameter Choices

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Restricts parameter input to a set of predefined choices using decorators, Literal types, or Enums.

```python
@app_commands.command()
@app_commands.describe(fruits='fruits to choose from')
@app_commands.choices(fruits=[
    Choice(name='apple', value=1),
    Choice(name='banana', value=2),
    Choice(name='cherry', value=3),
])
async def fruit(interaction: discord.Interaction, fruits: Choice[int]):
    await interaction.response.send_message(f'Your favourite fruit is {fruits.name}.')
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

### permissions_for(obj, /)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Handles permission resolution for a specific member or role, considering guild owner status, roles, and channel overrides.

```APIDOC
## permissions_for(obj, /)

### Description
Handles permission resolution for the Member or Role, taking into account guild owner status, roles, channel overrides, and member timeouts.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for.

### Returns
- **Permissions** - The resolved permissions for the member or role.
```

--------------------------------

### Restricting Commands by Role

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses has_any_role to ensure the invoker possesses at least one of the specified roles or IDs.

```python
@tree.command()
@app_commands.checks.has_any_role("Library Devs", "Moderators", 492212595072434186)
async def cool(interaction: discord.Interaction):
    await interaction.response.send_message("You are cool indeed")
```

--------------------------------

### Retrieve Guild Bans

Source: https://discordpy.readthedocs.io/en/latest/api.html

Iterate over ban entries or collect them into a list using an asynchronous generator.

```python
async for entry in guild.bans(limit=150):
    print(entry.user, entry.reason)
```

```python
bans = [entry async for entry in guild.bans(limit=2000)]
```

--------------------------------

### Group.get_command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves a command or group from its name.

```APIDOC
## get_command(name)

### Description
Retrieves a command or group from its name.

### Parameters
- **name** (str) - Required - The name of the command or group to retrieve.

### Returns
- **Optional[Union[Command, Group]]** - The command or group that was retrieved, or None if nothing was found.
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
- **label** (Optional[str]) - The label to display above the text input (Deprecated since 2.6).
- **custom_id** (str) - The ID of the text input received during an interaction.
- **style** (discord.TextStyle) - The style of the text input.
- **placeholder** (Optional[str]) - Placeholder text when empty.
- **default** (Optional[str]) - Default value of the text input.
- **required** (bool) - Whether the input is required.
- **min_length** (Optional[int]) - Minimum length (0-4000).
- **max_length** (Optional[int]) - Maximum length (1-4000).
- **row** (Optional[int]) - Relative row index (0-4).
- **id** (Optional[int]) - Unique component ID (New in 2.6).
```

--------------------------------

### delete(*, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the channel. Requires manage_channels permission.

```APIDOC
## delete(*, reason=None)

### Description
Deletes the channel. You must have manage_channels permission to perform this action.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this channel, which appears in the audit log.

### Raises
- **Forbidden** - Insufficient permissions.
- **NotFound** - Channel not found or already deleted.
- **HTTPException** - Deletion failed.
```

--------------------------------

### discord.on_raw_integration_delete(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an integration is deleted. Requires Intents.integrations to be enabled.

```APIDOC
## discord.on_raw_integration_delete(payload)

### Description
Called when an integration is deleted. This requires Intents.integrations to be enabled.

### Parameters
- **payload** (RawIntegrationDeleteEvent) - The raw event payload data.
```

--------------------------------

### Wait for a reaction event

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses wait_for with a timeout to capture a specific reaction from the message author.

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

### await _fetch_emojis()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all custom emojis from the guild.

```APIDOC
## await _fetch_emojis()

### Description
Retrieves all custom `Emoji`s from the guild. This is an API call; for general usage, consider `emojis` instead.

### Returns
- **List[Emoji]** - The retrieved emojis.

### Raises
- **HTTPException** - An error occurred fetching the emojis.
```

--------------------------------

### Registering a Command Check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the check decorator to restrict command execution based on a predicate function.

```python
async def is_owner(ctx):
    return ctx.author.id == 316026178463072268


@bot.command(name="eval")
@commands.check(is_owner)
async def _eval(ctx, *, code):
    """A bad example of an eval command"""
    await ctx.send(eval(code))
```

--------------------------------

### discord.PermissionOverwrite.is_empty

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the permission overwrite has no permissions explicitly set to True or False.

```APIDOC
## is_empty()

### Description
Checks if the permission overwrite is currently empty.

### Returns
- **bool** - True if the overwrite has no permissions set, False otherwise.
```

--------------------------------

### AppCommand.delete()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the application command.

```APIDOC
## await AppCommand.delete()

### Description
Deletes the application command.

### Raises
- **NotFound** - The application command was not found.
- **Forbidden** - You do not have permission to delete this application command.
- **HTTPException** - Deleting the application command failed.
- **MissingApplicationID** - The client does not have an application ID.
```

--------------------------------

### Restrict command to owners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses check_any to allow execution if the user is the bot owner or a guild owner.

```python
@bot.command()
@commands.check_any(commands.is_owner(), is_guild_owner())
async def only_for_owners(ctx):
    await ctx.send("Hello mister owner!")
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
- **after** (Union[abc.Snowflake, datetime.datetime]) - Optional - Retrieve guilds after this date or object.
- **with_counts** (bool) - Optional - Whether to include count information in the guilds. Defaults to True.

### Returns
- **Guild** - The guild with the guild data parsed.
```

--------------------------------

### Use typing.Annotated for custom type conversion

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Allows the library to use a specific converter while the type checker sees a different type. Useful for complex transformations like string manipulation.

```python
from typing import Annotated


@bot.command()
async def fun(ctx, arg: Annotated[str, lambda s: s.upper()]):
    await ctx.send(arg)
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

### fetch_member(member_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a Member from a guild ID and a member ID.

```APIDOC
## await fetch_member(member_id)

### Description
Retrieves a `Member` from a guild ID, and a member ID.

### Parameters
- **member_id** (int) - Required - The member’s ID to fetch from.

### Returns
- **Member** - The member from the member ID.
```

--------------------------------

### add_files

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds new files to the end of the message attachments. This is a coroutine.

```APIDOC
## await add_files(*files)

### Description
Adds new files to the end of the message attachments.

### Parameters
- **files** (File) - Required - New files to add to the message.

### Returns
- **InteractionMessage** - The newly edited message.

### Raises
- **HTTPException** - Editing the message failed.
- **Forbidden** - Tried to edit a message that isn’t yours.
```

--------------------------------

### Define a command with a Range constraint

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use app_commands.Range to restrict numeric or string input values within specific bounds.

```python
@app_commands.command()
async def range(interaction: discord.Interaction, value: app_commands.Range[int, 10, 12]):
    await interaction.response.send_message(f"Your value is {value}", ephemeral=True)
```

--------------------------------

### entitlements()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of entitlements.

```APIDOC
## entitlements()

### Description
Retrieves an asynchronous iterator of the `Entitlement` that the application has.

### Parameters
- **limit** (Optional[int]) - Optional - The number of entitlements to retrieve. Defaults to 100.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve entitlements before this date or entitlement.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve entitlements after this date or entitlement.
- **skus** (Optional[Sequence[Snowflake]]) - Optional - A list of SKUs to filter by.
- **user** (Optional[Snowflake]) - Optional - The user to filter by.
- **guild** (Optional[Snowflake]) - Optional - The guild to filter by.
- **exclude_ended** (bool) - Optional - Whether to exclude ended entitlements. Defaults to False.
- **exclude_deleted** (bool) - Optional - Whether to exclude deleted entitlements. Defaults to True.
```

--------------------------------

### Guild-Specific Command Registration

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Restricts a command to specific guilds instead of making it global. Must be placed below the command decorator.

```python
MY_GUILD_ID = discord.Object(...)  # Guild ID here


@app_commands.command()
@app_commands.guilds(MY_GUILD_ID)
async def bonk(interaction: discord.Interaction):
    await interaction.response.send_message("Bonk", ephemeral=True)
```

--------------------------------

### Access original message in command

Source: https://discordpy.readthedocs.io/en/latest/faq.html

The context object provides access to the original message via the message attribute.

```python
@bot.command()
async def length(ctx):
    await ctx.send(f"Your message is {len(ctx.message.content)} characters long.")
```

--------------------------------

### Iterate over channel history with AsyncIterator

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use asynchronous iteration to process messages from a channel's history.

```python
async for message in channel.history():
    print(message)
```

--------------------------------

### set_permissions(target, *, overwrite=..., reason=None, **permissions)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the channel-specific permission overwrites for a target member or role.

```APIDOC
## set_permissions(target, *, overwrite=..., reason=None, **permissions)

### Description
Sets the channel-specific permission overwrites for a target. This method replaces existing overwrites.

### Parameters
- **target** (Union[Member, Role]) - Required - The member or role to set permissions for.
- **overwrite** (Optional[PermissionOverwrite]) - Optional - The permission overwrite object. If None, overwrites are deleted.
- **reason** (Optional[str]) - Optional - The reason for the change.
- **permissions** (dict) - Optional - Keyword arguments denoting Permission attributes.
```

--------------------------------

### Handle commands with on_message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

When overriding on_message, call bot.process_commands to ensure commands still function.

```python
@bot.event
async def on_message(message):
    # do some extra stuff here

    await bot.process_commands(message)
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

### Cog.get_commands

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a list of commands defined within the cog, excluding app commands.

```APIDOC
## get_commands()

### Description
Returns the commands that are defined inside this cog. This does not include discord.app_commands.Command or discord.app_commands.Group instances.

### Returns
- **List[Command]** - A list of Commands that are defined inside this cog, not including subcommands.
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

### Customizing Cog Name via Meta Options

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Pass keyword arguments to the class definition to customize Cog behavior, such as setting a custom name.

```python
class MyCog(commands.Cog, name="My Cog"):
    pass
```

--------------------------------

### unpin(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unpins the message from the channel.

```APIDOC
## unpin(reason=None)

### Description
Unpins the message. You must have pin_messages permission to do this in a non-private channel context.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for unpinning the message.

### Raises
- **Forbidden** - You do not have permissions to unpin the message.
- **NotFound** - The message or channel was not found or deleted.
- **HTTPException** - Unpinning the message failed.
```

--------------------------------

### Member.timeout

Source: https://discordpy.readthedocs.io/en/latest/api.html

Applies a timeout to a member.

```APIDOC
## Member.timeout(until, /, *, reason=None)

### Description
Applies a time out to a member until the specified date time or for the given datetime.timedelta.

### Parameters
- **until** (datetime) - Required - The date the timeout should expire.
- **reason** (Optional[str]) - Optional - The reason for the audit log.
```

--------------------------------

### Implementing a Local Error Handler

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the error decorator to handle specific exceptions locally within a command.

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

### SKU.fetch_subscription(subscription_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific Subscription by its ID.

```APIDOC
## async SKU.fetch_subscription(subscription_id)

### Description
Retrieves a `Subscription` with the specified ID.

### Parameters
- **subscription_id** (`int`) - Required - The subscription’s ID to fetch from.

### Returns
- `Subscription` - The subscription you requested.

### Raises
- **NotFound** - A subscription with this ID does not exist.
- **HTTPException** - Fetching the subscription failed.
```

--------------------------------

### Integration.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a guild integration. Requires manage_guild permissions.

```APIDOC
## await Integration.delete(reason=None)

### Description
Deletes the integration. You must have `manage_guild` to do this.

### Parameters
- **reason** (str) - Optional - The reason the integration was deleted. Shows up on the audit log.

### Raises
- **Forbidden** - You do not have permission to delete the integration.
- **HTTPException** - Deleting the integration failed.
```

--------------------------------

### Client.before_identify_hook

Source: https://discordpy.readthedocs.io/en/latest/api.html

A hook called before identifying a session with Discord.

```APIDOC
## await Client.before_identify_hook(shard_id, *, initial=False)

### Description
A hook that is called before IDENTIFYing a session. This is useful if you wish to have more control over the synchronization of multiple IDENTIFYing clients.

### Parameters
- **shard_id** (int) - Required - The shard ID that requested being IDENTIFY’d
- **initial** (bool) - Optional - Whether this IDENTIFY is the first initial IDENTIFY.
```

--------------------------------

### get_context(origin, *, cls=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves the invocation context from a message or interaction. This is a coroutine.

```APIDOC
## get_context(origin, *, cls=...)

### Description
Retrieves the invocation context from the message or interaction. This is a low-level counterpart for process_commands() to allow for fine-grained control.

### Parameters
- **origin** (Union[discord.Message, discord.Interaction]) - Required - The message or interaction to get the invocation context from.
- **cls** (Any) - Optional - The factory class used to create the context. Defaults to Context.

### Returns
- **Context** - The invocation context.
```

--------------------------------

### unban(user, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Unbans a user from the guild. Requires the 'ban_members' permission.

```APIDOC
## unban(user, *, reason=None)

### Description
Unbans a user from the guild. The user must meet the abc.Snowflake abc. You must have 'ban_members' to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to unban.
- **reason** (Optional[str]) - Optional - The reason for doing this action.

### Raises
- **NotFound** - The requested unban was not found.
- **Forbidden** - You do not have the proper permissions to unban.
- **HTTPException** - Unbanning failed.
```

--------------------------------

### Accessing Custom Context Properties

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Custom properties defined in a subclass are accessible directly from the context object in commands.

```python
@bot.command()
async def secret(ctx):
    await ctx.send(ctx.secret)
```

--------------------------------

### history(limit=None, before=None, after=None, around=None, oldest_first=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the message history of a channel. This is an asynchronous operation that yields Message objects.

```APIDOC
## history(limit=None, before=None, after=None, around=None, oldest_first=None)

### Description
Retrieves the message history of a channel. This is an asynchronous operation that yields Message objects.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to retrieve.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this date or message.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this date or message.
- **around** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this date or message.
- **oldest_first** (Optional[bool]) - Optional - If set to True, return messages in oldest->newest order.

### Returns
- **Yields** (Message) - The message with the message data parsed.
```

--------------------------------

### MemberCacheFlags.from_intents(intents)

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance based on the provided Intents.

```APIDOC
## MemberCacheFlags.from_intents(intents)

### Description
A factory method that creates a MemberCacheFlags based on the currently selected Intents.

### Parameters
- **intents** (Intents) - Required - The intents to select from.

### Returns
- **MemberCacheFlags** - The resulting member cache flags.
```

--------------------------------

### discord.on_guild_integrations_update(guild)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever an integration is created, modified, or removed from a guild. Requires Intents.integrations to be enabled.

```APIDOC
## discord.on_guild_integrations_update(guild)

### Description
Called whenever an integration is created, modified, or removed from a guild. This requires Intents.integrations to be enabled.

### Parameters
- **guild** (Guild) - The guild that had its integrations updated.
```

--------------------------------

### await end(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends the scheduled event by setting its status to completed.

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

### Add reactions to messages

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Demonstrates adding emojis to messages using IDs, lookups, or raw strings.

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

### Invite.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Revokes an existing instant invite. Requires the manage_channels permission.

```APIDOC
## async delete(reason=None)

### Description
Revokes the instant invite. This is a coroutine.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this invite, which will appear in the audit log.
```

--------------------------------

### insert_field_at(index, name, value, inline=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Inserts a field before a specified index to the embed. Returns the class instance for chaining.

```APIDOC
### insert_field_at(index, name, value, inline=True)

#### Parameters
- **index** (int) - Required - The index of where to insert the field.
- **name** (str) - Required - The name of the field (max 256 characters).
- **value** (str) - Required - The value of the field (max 1024 characters).
- **inline** (bool) - Optional - Whether the field should be displayed inline.
```

--------------------------------

### Use List in FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Using typing.List allows a flag to be passed multiple times.

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

### Update Intents iteration logic

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

### Reload an extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html

Use reload_extension to apply changes to an extension without restarting the bot.

```python
>>> await bot.reload_extension('hello')
```

--------------------------------

### bans(limit=1000, before=..., after=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of the users that are banned from the guild.

```APIDOC
## async for ... in bans()

### Description
Retrieves an asynchronous iterator of the users that are banned from the guild as a `BanEntry`. Requires `ban_members` permission.

### Parameters
- **limit** (Optional[int]) - Optional - The number of bans to retrieve.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve bans before this date or object.
- **after** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve bans after this date or object.

### Yields
- **BanEntry** - The ban entry for the user.
```

--------------------------------

### Update message sending syntax

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Replaces the deprecated client.send_message method with the channel.send method.

```python
# before
await client.send_message(channel, "Hello")

# after
await channel.send("Hello")
```

--------------------------------

### discord.utils.resolve_invite

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves an invite from an Invite object, URL, or code.

```APIDOC
## discord.utils.resolve_invite(invite)

### Description
Resolves an invite from a Invite, URL or code.

### Parameters
- **invite** (Union[Invite, str]) - Required - The invite.

### Returns
- **ResolvedInvite** - A data class containing the invite code and the event ID.
```

--------------------------------

### @discord.ext.commands.dm_only()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Restricts a command to be used only within a DM context.

```APIDOC
## @discord.ext.commands.dm_only()

### Description
A check that ensures the command is only executed in a DM. Raises PrivateMessageOnly if used in a guild.
```

--------------------------------

### Create a custom exception for command checks

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Derive from commands.CheckFailure to raise custom exceptions within a check predicate for more robust error handling.

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

### Iterate over Entitlements

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves an asynchronous iterator of entitlements for the application.

```python
async for entitlement in client.entitlements(limit=100):
    print(entitlement.user_id, entitlement.ends_at)
```

```python
entitlements = [entitlement async for entitlement in client.entitlements(limit=100)]
# entitlements is now a list of Entitlement...
```

--------------------------------

### add_files(*files)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds new files to the end of the message attachments.

```APIDOC
## add_files(*files)

### Description
Adds new files to the end of the message attachments.

### Parameters
- **files** (File) - Required - New files to add to the message.

### Returns
- **WebhookMessage** - The newly edited message.
```

--------------------------------

### CategoryChannel.create_text_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new text channel within this category.

```APIDOC
## await create_text_channel(name, **options)

### Description
Shortcut method to create a TextChannel in the category.

### Returns
- **TextChannel** - The created channel.
```

--------------------------------

### CategoryChannel.create_voice_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new voice channel within this category.

```APIDOC
## await create_voice_channel(name, **options)

### Description
Shortcut method to create a VoiceChannel in the category.

### Returns
- **VoiceChannel** - The created channel.
```

--------------------------------

### Define a Hybrid Command Group

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Use the hybrid_group decorator to create command groups. The fallback parameter is required to handle the Discord limitation where slash command groups cannot be invoked directly.

```python
@bot.hybrid_group(fallback="get")
async def tag(ctx, name):
    await ctx.send(f"Showing tag: {name}")


@tag.command()
async def create(ctx, name):
    await ctx.send(f"Created tag: {name}")
```

--------------------------------

### entitlements(limit=100, ...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves an asynchronous iterator of the Entitlement that the application has.

```APIDOC
## async for ... in entitlements(limit=100, before=None, after=None, skus=None, user=None, guild=None, exclude_ended=False, exclude_deleted=True)

### Description
Retrieves an asynchronous iterator of the Entitlement that applications has.
```

--------------------------------

### Implement a custom Cog

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Defines a Cog with a custom name and implements all available special methods for lifecycle management, checks, error handling, and hooks.

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

### CategoryChannel.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the category channel settings. Requires manage_channels permission.

```APIDOC
## await edit(**options)

### Description
Edits the category channel. Requires the manage_channels permission.

### Parameters
- **name** (str) - Optional - The new category name.
- **position** (int) - Optional - The new category position.
- **nsfw** (bool) - Optional - Mark the category as NSFW.
- **reason** (Optional[str]) - Optional - Reason for the audit log.
- **overwrites** (Mapping) - Optional - Mapping of target to PermissionOverwrite.

### Returns
- **Optional[CategoryChannel]** - The newly edited category channel, or None if only positional changes occurred.
```

--------------------------------

### await edit(name=..., archived=..., locked=..., invitable=..., pinned=..., slowmode_delay=..., auto_archive_duration=..., applied_tags=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the thread properties. Requires appropriate permissions depending on the fields being modified.

```APIDOC
## await edit(name=..., archived=..., locked=..., invitable=..., pinned=..., slowmode_delay=..., auto_archive_duration=..., applied_tags=..., reason=None)

### Description
Edits the thread. The thread must be unarchived to be edited.

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
- Thread - The newly edited thread.
```

--------------------------------

### pin

Source: https://discordpy.readthedocs.io/en/latest/api.html

Pins the message. Requires pin_messages permission.

```APIDOC
## await pin(reason=None)

### Description
Pins the message. You must have `pin_messages` to do this in a non-private channel context.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for pinning the message. Shows up on the audit log.
```

--------------------------------

### get_sticker(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a guild sticker with the given ID.

```APIDOC
## get_sticker(id)

### Description
Returns a guild sticker with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[GuildSticker]** - The sticker or None if not found.
```

--------------------------------

### Schedule a task at a specific time daily

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Pass a datetime.time object to the time parameter of the loop decorator to trigger the task at a specific time each day.

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

### Send direct message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Send a DM to a user or member.

```python
user = client.get_user(381870129706958858)
await user.send("👀")
```

```python
await message.author.send("👋")
```

--------------------------------

### reaction.users()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of users who have reacted to a specific message.

```APIDOC
## reaction.users(limit=None, after=None, type=None)

### Description
Returns an asynchronous iterator of users or members who have reacted to the message. This can be used to process reactions individually or flattened into a list.

### Parameters
- **limit** (int) - Optional - The maximum number of results to return. If not provided, returns all users.
- **after** (abc.Snowflake) - Optional - For pagination, reactions are sorted by member.
- **type** (ReactionType) - Optional - The type of reaction to return users from. Defaults to 'normal'.

### Yields
- **Union[User, Member]** - The member or user that has reacted to the message.
```

--------------------------------

### discord.utils.utcnow

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an aware UTC datetime representing the current time.

```APIDOC
## discord.utils.utcnow()

### Description
A helper function to return an aware UTC datetime representing the current time.

### Returns
- **datetime.datetime** - The current aware datetime in UTC.
```

--------------------------------

### Flatten channel history into a list

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Convert an asynchronous history iterator into a standard list of messages.

```python
messages = await channel.history().flatten()
for message in messages:
    print(message)
```

--------------------------------

### @discord.app_commands.dm_only

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Indicates that a command can only be used within bot DM contexts.

```APIDOC
## @discord.app_commands.dm_only(func=None)

### Description
A decorator that indicates this command can only be used in the context of bot DMs. This is verified by Discord server side.
```

--------------------------------

### Implement a static command cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Uses the cooldown decorator to limit command usage to once every 5 seconds per member, with error handling for cooldown triggers.

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

### AutoShardedClient.send_audio_packet

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

### Inspecting Cog Listeners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Retrieve all listeners registered within a Cog, returning a list of name and function tuples.

```python
>>> for name, func in cog.get_listeners():
...     print(name, '->', func)
```

--------------------------------

### Messageable.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination. Supports text content, embeds, files, and various message formatting options.

```APIDOC
## async Messageable.send(content=None, *, tts=False, embed=None, embeds=None, file=None, files=None, stickers=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None, view=None, suppress_embeds=False, silent=False, poll=None)

### Description
Sends a message to the destination. The content must be convertible to a string. If content is None, an embed must be provided.

### Parameters
- **content** (str) - Optional - The message content.
- **tts** (bool) - Optional - Whether the message should be sent using text-to-speech. Defaults to False.
- **embed** (Embed) - Optional - A single embed to send.
- **embeds** (List[Embed]) - Optional - A list of embeds to send.
- **file** (File) - Optional - A single file to upload.
- **files** (List[File]) - Optional - A list of files to upload.
- **stickers** (List[Sticker]) - Optional - A list of stickers to send.
- **delete_after** (float) - Optional - Seconds to wait before deleting the message.
- **silent** (bool) - Optional - Whether the message should be sent without a notification sound.
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

### Errors
- **HTTPException**: Retrieving the scheduled events failed.

### Response
- **Returns**: List[ScheduledEvent]
```

--------------------------------

### discord.ui.UserSelect

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a UI select menu with a list of predefined options with the current members of the guild. If sent in a private message, it allows selecting the client or the user themselves.

```APIDOC
## class discord.ui.UserSelect(custom_id=..., placeholder=None, min_values=1, max_values=1, disabled=False, required=True, row=None, default_values=..., id=None)

### Description
Represents a UI select menu with a list of predefined options with the current members of the guild. If this is sent a private message, it will only allow the user to select the client or themselves.

### Parameters
- **custom_id** (str) - Optional - The ID of the select menu that gets received during an interaction. Max 100 characters.
- **placeholder** (Optional[str]) - Optional - The placeholder text shown if nothing is selected. Max 150 characters.
- **min_values** (int) - Optional - The minimum number of items that must be chosen. Defaults to 1, range 0-25.
- **max_values** (int) - Optional - The maximum number of items that must be chosen. Defaults to 1, range 1-25.
- **disabled** (bool) - Optional - Whether the select is disabled.
- **required** (bool) - Optional - Whether the select is required. Only applicable within modals.
- **default_values** (Sequence[Snowflake]) - Optional - A list of objects representing the users that should be selected by default.
- **row** (Optional[int]) - Optional - The relative row this select menu belongs to (0-4).
- **id** (Optional[int]) - Optional - The ID of the component, must be unique across the view.
```

--------------------------------

### Implementing Cog-based invocation hooks

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use cog-specific methods to manage state or cleanup within a Cog class.

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

### @discord.app_commands.guild_only

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Indicates that a command can only be used within a guild context. Verification is handled server-side by Discord.

```APIDOC
## @discord.app_commands.guild_only(func=None)

### Description
A decorator that indicates this command can only be used in a guild context. This is verified by Discord server side and does not trigger a local check error handler.
```

--------------------------------

### history

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator for message history.

```APIDOC
## history(*, limit=100, before=None, after=None, around=None, oldest_first=None)

### Description
Returns an asynchronous iterator that enables receiving the destination’s message history. Requires read_message_history permission.
```

--------------------------------

### discord.ui.FileUpload

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a file upload component within a modal. Allows users to upload files as part of an interaction.

```APIDOC
## class discord.ui.FileUpload(custom_id=..., required=True, min_values=None, max_values=None, id=None)

### Description
Represents a file upload component within a modal. New in version 2.7.

### Parameters
- **id** (Optional[int]) - Optional - The ID of the component. Must be unique across the view.
- **custom_id** (Optional[str]) - Optional - The custom ID of the file upload component.
- **max_values** (Optional[int]) - Optional - The maximum number of files that can be uploaded (1-10). Defaults to 1.
- **min_values** (Optional[int]) - Optional - The minimum number of files that must be uploaded (0-10). Defaults to 0.
- **required** (bool) - Required - Whether this component is required to be filled before submitting. Defaults to True.
```

--------------------------------

### Customizing FlagConverter with flag()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the flag() function to customize flag names and default values.

```python
from typing import List


class BanFlags(commands.FlagConverter):
    members: List[discord.Member] = commands.flag(name="member", default=lambda ctx: [])
```

--------------------------------

### await edit(**fields, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the properties of the scheduled event.

```APIDOC
## await edit(**fields, reason=None)

### Description
Edits the scheduled event. Requires manage_events permission. This is a coroutine.

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

### await edit(content=..., embed=..., embeds=..., attachments=..., delete_after=None, allowed_mentions=..., view=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the message content, embeds, attachments, or view.

```APIDOC
## await edit(...)

### Description
Edits the message. Returns the newly edited message object.

### Parameters
- **content** (str) - Optional - New content.
- **embed** (Embed) - Optional - New embed.
- **embeds** (List[Embed]) - Optional - New list of embeds (max 10).
- **attachments** (List[Union[Attachment, File]]) - Optional - List of attachments.
- **delete_after** (float) - Optional - Seconds to wait before deleting the edited message.
- **allowed_mentions** (AllowedMentions) - Optional - Mentions processing configuration.
- **view** (Union[View, LayoutView]) - Optional - Updated view.

### Returns
- **Message** - The newly edited message.
```

--------------------------------

### pins()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the pinned messages from a channel.

```APIDOC
## pins(limit=50, before=None, oldest_first=False)

### Description
Retrieves a list of pinned messages from the channel.

### Parameters
#### Query Parameters
- **limit** (int) - Optional - The number of pinned messages to retrieve. Defaults to 50.
- **before** (datetime.datetime or abc.Snowflake) - Optional - Retrieve pinned messages before this time or snowflake.
- **oldest_first** (bool) - Optional - If True, return messages in oldest to newest order. Defaults to False.

### Returns
- **Message** - Yields the pinned message with Message.pinned_at set.

### Raises
- **Forbidden** - You do not have the permission to retrieve pinned messages.
- **HTTPException** - Retrieving the pinned messages failed.
```

--------------------------------

### Implement a logical OR check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses the check decorator to create a predicate that validates if the user is the guild owner.

```python
def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)
```

--------------------------------

### VoiceChannel.move

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine to move a voice channel relative to other channels. Requires manage_channels permission.

```APIDOC
## await move(**kwargs)

### Description
A rich interface to help move a channel relative to other channels. Voice channels will always be sorted below text channels.

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

### Greedy Attachment Command

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses Greedy to capture all remaining attachments provided by the user.

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

### discord.on_error

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an event raises an uncaught exception.

```APIDOC
## discord.on_error(event, *args, **kwargs)

### Description
Allows overriding the default behavior of logging tracebacks for uncaught exceptions in events.

### Parameters
- **event** (str) - Required - The name of the event that raised the exception.
- **args** (tuple) - Optional - The positional arguments for the event.
- **kwargs** (dict) - Optional - The keyword arguments for the event.
```

--------------------------------

### discord.on_reaction_add(reaction, user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message has a reaction added to it. Requires Intents.reactions to be enabled.

```APIDOC
## discord.on_reaction_add(reaction, user)

### Description
Called when a message has a reaction added to it. If the message is not in the internal cache, this event will not be called; consider using on_raw_reaction_add instead.

### Parameters
- **reaction** (Reaction) - The current state of the reaction.
- **user** (Union[Member, User]) - The user who added the reaction.
```

--------------------------------

### Implement a separate converter class

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses a dedicated converter class inheriting from MemberConverter to transform arguments.

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

### discord.utils.as_chunks

Source: https://discordpy.readthedocs.io/en/latest/api.html

Collects an iterator into chunks of a given size.

```APIDOC
## discord.utils.as_chunks(iterator, max_size)

### Description
A helper function that collects an iterator into chunks of a given size.

### Parameters
- **iterator** (Union[collections.abc.Iterable, collections.abc.AsyncIterable]) - Required - The iterator to chunk, can be sync or async.
- **max_size** (int) - Required - The maximum chunk size.
```

--------------------------------

### Using Built-in Owner Check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Uses the library-provided is_owner check decorator.

```python
@bot.command(name="eval")
@commands.is_owner()
async def _eval(ctx, *, code):
    """A bad example of an eval command"""
    await ctx.send(eval(code))
```

--------------------------------

### Bot.unload_extension

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Unloads an extension, removing all commands, listeners, and cogs.

```APIDOC
## Bot.unload_extension(name, *, package=None)

### Description
Unloads an extension. When the extension is unloaded, all commands, listeners, and cogs are removed from the bot and the module is un-imported.

### Parameters
- **name** (str) - Required - The extension name to unload.
- **package** (Optional[str]) - Optional - The package name to resolve relative imports with.
```

--------------------------------

### discord.ui.button

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that attaches a button to a component. The decorated function should accept self, interaction, and the button instance.

```APIDOC
## @discord.ui.button(label=None, custom_id=None, disabled=False, style=ButtonStyle.secondary, emoji=None, row=None, id=None)

### Description
A decorator that attaches a button to a component. The function being decorated should have three parameters: `self` (the `discord.ui.View`), `interaction` (the `discord.Interaction`), and the `button` (the `discord.ui.Button` being pressed).

### Parameters
- **label** (Optional[str]) - Optional - The label of the button.
- **custom_id** (Optional[str]) - Optional - The ID of the button received during an interaction.
- **disabled** (bool) - Optional - Whether the button is disabled.
- **style** (discord.ButtonStyle) - Optional - The style of the button.
- **emoji** (Optional[Union[PartialEmoji, Emoji, str]]) - Optional - The emoji of the button.
- **row** (Optional[int]) - Optional - The relative row this button belongs to (0-4).
- **id** (Optional[int]) - Optional - The unique ID of this component.
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

### defer(*, ephemeral=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that defers interaction-based contexts, typically used when a secondary action will be performed later.

```APIDOC
## await defer(*, ephemeral=False)

### Description
Defers the interaction based contexts. This is typically used when the interaction is acknowledged and a secondary action will be done later. If this isn’t an interaction based context then it does nothing.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral.

### Raises
- **HTTPException** - Deferring the interaction failed.
- **InteractionResponded** - This interaction has already been responded to before.
```

--------------------------------

### ActionRow.add_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds an item to the action row. Returns the instance for chaining.

```APIDOC
## add_item(item)

### Description
Adds an item to this action row. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to add to the action row.

### Raises
- **TypeError** - An Item was not passed.
- **ValueError** - Maximum number of children has been exceeded (5) or (40) for the entire view.
```

--------------------------------

### User.fetch_message(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single message from the destination by its ID.

```APIDOC
## await User.fetch_message(id)

### Description
Retrieves a single Message from the destination.

### Parameters
- **id** (int) - Required - The message ID to look for.

### Returns
- **Message** - The message asked for.

### Raises
- **NotFound** - The specified message was not found.
- **Forbidden** - You do not have the permissions required to get a message.
- **HTTPException** - Retrieving the message failed.
```

--------------------------------

### @discord.app_commands.rename

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Renames the given parameters by their name using the key of the keyword argument as the name within the Discord UI.

```APIDOC
## @discord.app_commands.rename(**parameters)

### Description
Renames the given parameters by their name using the key of the keyword argument as the name. This renames the parameter within the Discord UI.

### Parameters
- **parameters** (Union[str, locale_str]) - Required - The name of the parameters.
```

--------------------------------

### original_response()

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

### fetch_sticker(sticker_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a sticker object by its ID.

```APIDOC
## fetch_sticker(sticker_id)

### Description
Retrieves a `Sticker` with the specified ID.

### Parameters
- **sticker_id** (int) - Required - The sticker's ID to fetch from.

### Returns
- **Union[StandardSticker, GuildSticker]** - The sticker you requested.

### Raises
- **HTTPException** - Retrieving the sticker failed.
- **NotFound** - Invalid sticker ID.
```

--------------------------------

### AllowedMentions

Source: https://discordpy.readthedocs.io/en/latest/api.html

A class representing what mentions are allowed in a message, configurable globally or per-message.

```APIDOC
## AllowedMentions(everyone=True, users=True, roles=True, replied_user=True)

### Description
A class that represents what mentions are allowed in a message. This class can be set during Client initialisation or applied on a per message basis.

### Attributes
- **everyone** (bool) - Whether to allow everyone and here mentions.
- **users** (Union[bool, Sequence[abc.Snowflake]]) - Controls the users being mentioned.
- **roles** (Union[bool, Sequence[abc.Snowflake]]) - Controls the roles being mentioned.
- **replied_user** (bool) - Whether to mention the author of the message being replied to.
```

--------------------------------

### clear_fields()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes all fields from the embed object. Returns the class instance for fluent-style chaining.

```APIDOC
## clear_fields()

### Description
Removes all fields from this embed. This function returns the class instance to allow for fluent-style chaining.
```

--------------------------------

### get_stage_instance(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a stage instance with the given stage channel ID.

```APIDOC
## get_stage_instance(id)

### Description
Returns a stage instance with the given stage channel ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[StageInstance]** - The stage instance or None if not found.
```

--------------------------------

### fetch_application_emoji

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a specific emoji for the current application.

```APIDOC
## fetch_application_emoji(emoji_id)

### Description
Retrieves an emoji for the current application.

### Parameters
- **emoji_id** (int) - Required - The emoji ID to retrieve.

### Returns
- **Emoji** - The emoji requested.
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

### discord.on_interaction(interaction)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an interaction happened. Used for slash command invocations or components.

```APIDOC
## discord.on_interaction(interaction)

### Description
Called when an interaction happened. This currently happens due to slash command invocations or components being used.

### Parameters
- **interaction** (Interaction) - The interaction data.
```

--------------------------------

### Attachment.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts the attachment into a File object suitable for sending.

```APIDOC
## await Attachment.to_file(*, filename=..., description=..., use_cached=False, spoiler=False)

### Description
Converts the attachment into a File suitable for sending via abc.Messageable.send().

### Parameters
- **filename** (str) - Optional - The filename to use for the file.
- **description** (str) - Optional - The description for the file.
- **use_cached** (bool) - Optional - Whether to use proxy_url rather than url.
- **spoiler** (bool) - Optional - Whether the file should be marked as a spoiler.
```

--------------------------------

### Creating a Custom Check Decorator

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Wraps a check predicate in a factory function to create a reusable decorator.

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

--------------------------------

### fetch_webhook(webhook_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a webhook object by its ID.

```APIDOC
## fetch_webhook(webhook_id)

### Description
Retrieves a `Webhook` with the specified ID.

### Parameters
- **webhook_id** (int) - Required - The webhook's ID to fetch from.

### Returns
- **Webhook** - The webhook you requested.

### Raises
- **HTTPException** - Retrieving the webhook failed.
- **NotFound** - Invalid webhook ID.
- **Forbidden** - You do not have permission to fetch this webhook.
```

--------------------------------

### Webhook.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the webhook. This method supports various parameters for content, files, embeds, and UI components.

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
- **Optional[WebhookMessage]** - The message that was sent if `wait` is `True`, otherwise `None`.
```

--------------------------------

### discord.on_guild_emojis_update(guild, before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Guild adds or removes Emoji. Requires Intents.emojis_and_stickers to be enabled.

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

### Bulk update permissions

Source: https://discordpy.readthedocs.io/en/latest/whats_new.html

Use the update method to modify multiple permission attributes in a single call.

```python
p.update(read_messages=True, send_messages=False)
```

--------------------------------

### discord.on_invite_delete(invite)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when an Invite is deleted. Requires Intents.invites to be enabled.

```APIDOC
## discord.on_invite_delete(invite)

### Description
Called when an Invite is deleted. You must have manage_channels to receive this. This requires Intents.invites to be enabled.

### Parameters
- **invite** (Invite) - The invite that was deleted.
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

### discord.on_guild_role_update(before, after)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a role is changed guild-wide. Requires Intents.guilds to be enabled.

```APIDOC
## discord.on_guild_role_update(before, after)

### Description
Called when a Role is changed guild-wide.

### Parameters
- **before** (Role) - The updated role’s old info.
- **after** (Role) - The updated role’s updated info.
```

--------------------------------

### get_guild(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a guild with the given ID.

```APIDOC
## get_guild(id)

### Description
Returns a guild with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[Guild]** - The guild or None if not found.
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

### await fetch_automod_rule(automod_rule_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Fetches a specific automod rule by ID. Requires manage_guild permission.

```APIDOC
## await fetch_automod_rule(automod_rule_id)

### Description
Fetches an active automod rule from the guild. Requires Permissions.manage_guild.

### Parameters
- **automod_rule_id** (int) - The ID of the automod rule to fetch.

### Returns
- **AutoModRule** - The fetched automod rule.

### Raises
- **Forbidden** - You do not have permission to view the automod rule.
- **NotFound** - The automod rule does not exist.
```

--------------------------------

### Iterate over channel message history

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use an asynchronous loop to process messages in a channel's history.

```python
counter = 0
async for message in channel.history(limit=200):
    if message.author == client.user:
        counter += 1
```

```python
messages = [message async for message in channel.history(limit=123)]
# messages is now a list of Message...
```

--------------------------------

### @discord.ext.commands.guild_only()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Restricts a command to be used only within a guild context.

```APIDOC
## @discord.ext.commands.guild_only()

### Description
A check that ensures the command is only executed in a guild. Raises NoPrivateMessage if used in a DM.
```

--------------------------------

### Attachment.save

Source: https://discordpy.readthedocs.io/en/latest/api.html

Saves the attachment content into a file-like object or a file on disk.

```APIDOC
## await Attachment.save(fp, *, seek_begin=True, use_cached=False)

### Description
Saves this attachment into a file-like object or creates a file with the provided filename.

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

### Webhook.fetch_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single WebhookMessage owned by the webhook.

```APIDOC
## Webhook.fetch_message

### Description
Retrieves a single `WebhookMessage` owned by this webhook using its ID.

### Parameters
- **id** (int) - Required - The message ID to look for.
- **thread** (Snowflake) - Optional - The thread to look in.

### Returns
- **WebhookMessage** - The message requested.
```

--------------------------------

### Invite.set_scheduled_event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Associates a scheduled event with the invite.

```APIDOC
## set_scheduled_event(scheduled_event)

### Description
Sets the scheduled event for this invite.

### Parameters
- **scheduled_event** (Snowflake) - Required - The ID of the scheduled event.

### Returns
- **Invite** - The invite object with the updated scheduled event.
```

--------------------------------

### Refactoring message history collection

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Use list comprehensions with asynchronous iterators to replace manual loops for collecting message content.

```python
# before
content_of_messages = []
async for content in channel.history().map(lambda m: m.content):
    content_of_messages.append(content)

# after
content_of_messages = [message.content async for message in channel.history()]
```

--------------------------------

### VoiceChannel.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the voice channel with the provided options. Requires manage_channels permission.

```APIDOC
## await edit(*, name=None, bitrate=None, nsfw=None, user_limit=None, position=None, sync_permissions=False, category=None, slowmode_delay=None, reason=None, overwrites=None, rtc_region=None, video_quality_mode=None, status=None)

### Description
Edits the channel properties. This is a coroutine.

### Parameters
- **name** (str) - Optional - The new channel's name.
- **bitrate** (int) - Optional - The new channel's bitrate.
- **nsfw** (bool) - Optional - To mark the channel as NSFW or not.
- **user_limit** (int) - Optional - The new channel's user limit.
- **position** (int) - Optional - The new channel's position.
- **sync_permissions** (bool) - Optional - Whether to sync permissions with the channel's new or pre-existing category.
- **category** (Optional[CategoryChannel]) - Optional - The new category for this channel.
- **slowmode_delay** (int) - Optional - Specifies the slowmode rate limit for user in this channel, in seconds.
- **reason** (Optional[str]) - Optional - The reason for editing this channel.
- **overwrites** (Mapping) - Optional - A Mapping of target to PermissionOverwrite to apply.
- **rtc_region** (Optional[str]) - Optional - The new region for the voice channel's voice communication.
- **video_quality_mode** (VideoQualityMode) - Optional - The camera video quality for the voice channel's participants.
- **status** (Optional[str]) - Optional - The new voice channel status.

### Returns
- **VoiceChannel** (Optional) - The newly edited voice channel.
```

--------------------------------

### Cog.listener

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Decorator to mark a function as an event listener within the cog.

```APIDOC
## listener(name=...)

### Description
A decorator that marks a function as a listener. This is the cog equivalent of Bot.listen().

### Parameters
- **name** (str) - Optional - The name of the event being listened to. Defaults to the function's name.
```

--------------------------------

### SoundboardSound.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the soundboard sound. Requires manage_expressions permission or specific ownership permissions.

```APIDOC
## await SoundboardSound.delete(reason=None)

### Description
Deletes the soundboard sound. You must have `manage_expressions` to delete the sound. If the sound was created by the client, you must have either `manage_expressions` or `create_expressions`.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this sound. Shows up on the audit log.
```

--------------------------------

### pins(limit=50, before=None, oldest_first=False)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of the pinned messages in the channel.

```APIDOC
## pins

### Description
Retrieves an asynchronous iterator of the pinned messages in the channel. Requires view_channel and read_message_history permissions.

### Parameters
- **limit** (int) - Optional - The number of messages to retrieve (default 50).
- **before** (Any) - Optional - Retrieve messages before this point.
- **oldest_first** (bool) - Optional - Whether to return messages oldest first.

### Returns
- **AsyncIterator[Message]** - An asynchronous iterator of pinned messages.
```

--------------------------------

### channel.history

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns an asynchronous iterator that enables receiving the destination’s message history.

```APIDOC
## async channel.history(limit=100, before=None, after=None, around=None, oldest_first=None)

### Description
Returns an asynchronous iterator that enables receiving the destination’s message history. You must have `read_message_history` permission to perform this action.

### Parameters
- **limit** (Optional[int]) - Optional - The number of messages to retrieve. If None, retrieves every message in the channel.
- **before** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages before this date or message.
- **after** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages after this date or message.
- **around** (Optional[Union[Snowflake, datetime.datetime]]) - Optional - Retrieve messages around this date or message. Maximum limit is 101.
- **oldest_first** (Optional[bool]) - Optional - If set to True, return messages in oldest->newest order.

### Yields
- **Message** - The message with the message data parsed.

### Raises
- **Forbidden** - You do not have permissions to get channel message history.
- **HTTPException** - The request to get message history failed.
```

--------------------------------

### fetch_message(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single Message from the destination. This is a coroutine.

```APIDOC
## fetch_message

### Description
Retrieves a single Message from the destination by its ID.

### Parameters
- **id** (int) - Required - The message ID to look for.

### Returns
- **Message** - The message asked for.
```

--------------------------------

### fetch_thread

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Retrieves the public thread attached to the message.

```APIDOC
## fetch_thread()

### Description
Retrieves the public thread attached to this message via an API call.

### Returns
- **Thread** - The public thread attached to this message.
```

--------------------------------

### Use discord.Attachment converter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Retrieves files uploaded with the message. Does not inspect message content.

```python
import discord


@bot.command()
async def upload(ctx, attachment: discord.Attachment):
    await ctx.send(f"You have uploaded <{attachment.url}>")
```

--------------------------------

### purge(limit, check, before, after, around, oldest_first, bulk, reason)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Purges messages from the channel based on provided criteria.

```APIDOC
## purge(limit, check, before, after, around, oldest_first, bulk, reason)

### Description
Deletes messages from the channel that match the provided criteria.

### Parameters
- **limit** (int) - Optional - The number of messages to search through.
- **check** (Callable[[Message], bool]) - Required - The function used to check if a message should be deleted.
- **before** (Union[abc.Snowflake, datetime.datetime]) - Optional - Search messages before this ID or time.
- **after** (Union[abc.Snowflake, datetime.datetime]) - Optional - Search messages after this ID or time.
- **around** (Union[abc.Snowflake, datetime.datetime]) - Optional - Search messages around this ID or time.
- **oldest_first** (bool) - Optional - Whether to search oldest messages first.
- **bulk** (bool) - Required - If True, use bulk delete.
- **reason** (str) - Optional - The reason for purging the messages.

### Returns
- List[Message] - The list of messages that were deleted.
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

### Attachment.read

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves the content of the attachment as a bytes object.

```APIDOC
## await Attachment.read(*, use_cached=False)

### Description
Retrieves the content of this attachment as a bytes object.

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

### Flatten message history into a list

Source: https://discordpy.readthedocs.io/en/latest/api.html

Shows how to collect messages from the history iterator into a standard Python list using a list comprehension.

```python
messages = [message async for message in channel.history(limit=123)]
```

--------------------------------

### discord.ext.commands.check

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A decorator that adds a check to a Command or its subclasses.

```APIDOC
## @discord.ext.commands.check(predicate)

### Description
A decorator that adds a check to the Command or its subclasses. The predicate must take a single parameter of type Context and return a boolean-like value.

### Parameters
- **predicate** (Callable[[Context], bool]) - Required - The predicate to check if the command should be invoked.
```

--------------------------------

### VoiceChannel.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the destination with the content given. This is a coroutine.

```APIDOC
## VoiceChannel.send

### Description
Sends a message to the destination with the content given. The content must be a type that can convert to a string through str(content).

### Parameters
- **content** (Optional[str]) - Optional - The content of the message to send.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **embed** (Embed) - Optional - The rich embed for the content.
- **embeds** (List[Embed]) - Optional - A list of embeds to upload. Must be a maximum of 10.
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload. Must be a maximum of 10.
- **nonce** (int) - Optional - The nonce to use for sending this message.
- **delete_after** (float) - Optional - The number of seconds to wait before deleting the message.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed in this message.
- **reference** (Union[Message, MessageReference, PartialMessage]) - Optional - A reference to the Message to which you are referencing.
- **mention_author** (Optional[bool]) - Optional - If set, overrides the replied_user attribute of allowed_mentions.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - A Discord UI View to add to the message.
- **stickers** (Sequence[Union[GuildSticker, StickerItem]]) - Optional - A list of stickers to upload. Must be a maximum of 3.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications for the message.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **Message** - The message that was sent.
```

--------------------------------

### discord.on_raw_reaction_add(payload)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message has a reaction added, regardless of the internal message cache state.

```APIDOC
## discord.on_raw_reaction_add(payload)

### Description
Called when a message has a reaction added. This is called regardless of the state of the internal message cache.

### Parameters
- **payload** (RawReactionActionEvent) - The raw event payload data.
```

--------------------------------

### fetch_members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all ThreadMember objects in the thread.

```APIDOC
## fetch_members()

### Description
Retrieves all ThreadMember objects that are in this thread. Requires Intents.members.
```

--------------------------------

### await cancel(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Cancels the scheduled event by setting its status to cancelled.

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

### permissions_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Resolves permissions for a member or role within the thread context.

```APIDOC
## permissions_for(obj)

### Description
Handles permission resolution for the Member or Role. Since threads do not have their own permissions, they mostly inherit them from the parent channel with some implicit permissions changed.

### Parameters
- **obj** (Union[Member, Role]) - Required - The object to resolve permissions for. If it’s a role then member overwrites are not computed.

### Returns
- **Permissions** - The resolved permissions for the member or role.
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

### discord.on_member_remove(member)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a Member leaves a Guild. Requires Intents.members to be enabled.

```APIDOC
## discord.on_member_remove(member)

### Description
Called when a Member leaves a Guild. This requires Intents.members to be enabled.

### Parameters
- **member** (Member) - The member who left.
```

--------------------------------

### remove_footer()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears the embed's footer information. Returns the class instance for chaining.

```APIDOC
### remove_footer()

Clears embed footer information.
```

--------------------------------

### add_check(func)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds a check to the command to determine if it can be executed.

```APIDOC
## add_check(func)

### Description
Adds a check function to the command. This is the non-decorator interface for adding command execution requirements.

### Parameters
- **func** (function) - Required - The function to be used as a check.
```

--------------------------------

### GroupChannel.send

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to the group channel.

```APIDOC
## async GroupChannel.send(content=None, ...)

### Description
Sends a message to the group channel. Returns the message that was sent.

### Raises
- **HTTPException** - Sending the message failed.
- **Forbidden** - You do not have the proper permissions to send the message.
- **NotFound** - You sent a message with the same nonce as one that has been explicitly deleted shortly earlier.
- **ValueError** - The `files` or `embeds` list is not of the appropriate size.
- **TypeError** - You specified both `file` and `files`, or you specified both `embed` and `embeds`, or the `reference` object is not a `Message`, `MessageReference` or `PartialMessage`.
```

--------------------------------

### on_error

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Coroutine callback triggered when a command raises an AppCommandError.

```APIDOC
## on_error(interaction, error)

### Description
This function is a coroutine. A callback that is called when any command raises an AppCommandError. The default implementation logs the exception using the library logger if the command does not have any error handlers attached to it.

### Parameters
- **interaction** (Interaction) - Required - The interaction that caused the error.
- **error** (AppCommandError) - Required - The error that was raised.
```

--------------------------------

### Restrict commands via add_command

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Specify a guild when adding a command to the tree manually. Avoid using this with the command decorator to prevent duplicates.

```python
@app_commands.command()
async def ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")


tree.add_command(ping, guild=discord.Object(123456789012345678))
```

--------------------------------

### PartialEmoji.from_str

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts a Discord string representation of an emoji to a PartialEmoji object.

```APIDOC
## PartialEmoji.from_str(value, *, client=None)

### Description
Converts a Discord string representation of an emoji (e.g., 'a:name:id' or '<a:name:id>') to a PartialEmoji object. If the format does not match, it is treated as a unicode emoji.

### Parameters
- **value** (str) - Required - The string representation of an emoji.
- **client** (Client) - Optional - The client to initialise this emoji with.

### Returns
- **PartialEmoji** - The partial emoji from this string.
```

--------------------------------

### Register Event Listeners

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Registers functions as event listeners using the add_listener method as an alternative to the @listen decorator.

```python
async def on_ready():
    pass


async def my_message(message):
    pass


bot.add_listener(on_ready)
bot.add_listener(my_message, "on_message")
```

--------------------------------

### Restrict command context with allowed_contexts

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Use this decorator to specify whether a command is available in guilds, DMs, or private channels. It is verified server-side and does not work on subcommands.

```python
@app_commands.command()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def my_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am only available in guilds and private channels!")
```

--------------------------------

### Template.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the template.

```APIDOC
## Template.delete()

### Description
Delete the template. Requires `manage_guild` permission in the source guild.
```

--------------------------------

### fetch_user(user_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a User object based on their ID.

```APIDOC
## fetch_user(user_id)

### Description
Retrieves a `User` based on their ID. This is an API call that does not require shared guilds.

### Parameters
- **user_id** (int) - Required - The user’s ID to fetch from.

### Returns
- **User** - The user you requested.

### Raises
- **NotFound** - A user with this ID does not exist.
- **HTTPException** - Fetching the user failed.
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

### Translator.translate()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Translates the given string to the specified locale. If the string cannot be translated, None should be returned.

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

### fetch_role(role_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a Role object with the specified ID from the API.

```APIDOC
## fetch_role(role_id)

### Description
Retrieves a Role with the specified ID. This is an API call.

### Parameters
- **role_id** (int) - Required - The role’s ID.

### Returns
- **Role** - The retrieved role.

### Raises
- **NotFound** - The role requested could not be found.
- **HTTPException** - An error occurred fetching the role.
```

--------------------------------

### CategoryChannel.create_stage_channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a new stage channel within this category.

```APIDOC
## await create_stage_channel(name, **options)

### Description
Shortcut method to create a StageChannel in the category.

### Returns
- **StageChannel** - The created channel.
```

--------------------------------

### @discord.app_commands.checks.has_permissions(**perms)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member has all of the specified permissions.

```APIDOC
## @discord.app_commands.checks.has_permissions(**perms)

### Description
A check that verifies if the member has all of the permissions necessary, based on discord.Interaction.permissions. Raises MissingPermissions on failure.

### Parameters
- **perms** (bool) - Required - Keyword arguments denoting the permissions to check for.
```

--------------------------------

### @discord.app_commands.private_channel_only

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Indicates that a command can only be used in DMs and group DMs.

```APIDOC
## @discord.app_commands.private_channel_only(func=None)

### Description
A decorator that indicates this command can only be used in the context of DMs and group DMs. This is verified by Discord server side.
```

--------------------------------

### Update on_guild_emojis_update signature

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The event now includes the guild object as the first argument.

```python
async def on_guild_emojis_update(before, after)
```

```python
async def on_guild_emojis_update(guild, before, after)
```

--------------------------------

### Avoid blocking the event loop

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Use asyncio.sleep instead of time.sleep to prevent blocking the event loop.

```python
# bad
time.sleep(10)

# good
await asyncio.sleep(10)
```

--------------------------------

### Loop.add_exception_type

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Adds exception types to be handled during the reconnect logic.

```APIDOC
## Loop.add_exception_type(*exceptions)

### Description
Adds exception types to be handled during the reconnect logic.
```

--------------------------------

### InteractionResponse.send_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by sending a message.

```APIDOC
## await InteractionResponse.send_message(content=None, *, embed=..., embeds=..., file=..., files=..., view=..., tts=False, ephemeral=False, allowed_mentions=..., suppress_embeds=False, silent=False, delete_after=None, poll=...)

### Description
Responds to this interaction by sending a message.

### Parameters
- **content** (Optional[str]) - Optional - The content of the message to send.
- **embeds** (List[Embed]) - Optional - A list of embeds to send.
- **embed** (Embed) - Optional - The rich embed for the content.
- **file** (File) - Optional - The file to upload.
- **files** (List[File]) - Optional - A list of files to upload.
- **tts** (bool) - Optional - Indicates if the message should be sent using text-to-speech.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - The view to send with the message.
- **ephemeral** (bool) - Optional - Indicates if the message should only be visible to the user who started the interaction.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **suppress_embeds** (bool) - Optional - Whether to suppress embeds for the message.
- **silent** (bool) - Optional - Whether to suppress push and desktop notifications.
- **delete_after** (float) - Optional - Number of seconds to wait before deleting the message.
- **poll** (Poll) - Optional - The poll to send with this message.

### Returns
- **InteractionCallbackResponse** - The interaction callback data.
```

--------------------------------

### View.interaction_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Callback to check if the view should process item callbacks.

```APIDOC
## await interaction_check(interaction, /)

### Description
A coroutine called when an interaction happens within the view that checks whether the view should process item callbacks for the interaction.

### Parameters
- **interaction** (Interaction) - Required - The interaction that occurred.
```

--------------------------------

### discord.SelectDefaultValue

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a default value for a select menu, which can be constructed for channels, roles, or users.

```APIDOC
## class discord.SelectDefaultValue(id, type)

### Description
Represents a select menu's default value. These can be created by users.

### Methods
- **from_channel(channel)**: Creates a SelectDefaultValue with the type set to channel.
- **from_role(role)**: Creates a SelectDefaultValue with the type set to role.
- **from_user(user)**: Creates a SelectDefaultValue with the type set to user.
```

--------------------------------

### SyncWebhook.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the webhook from Discord.

```APIDOC
## SyncWebhook.delete

### Description
Deletes the current webhook from the Discord server.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deletion, which appears in the audit log.
- **prefer_auth** (bool) - Optional - Whether to use the bot token over the webhook token. Defaults to True.

### Errors
- **HTTPException** - Deleting the webhook failed.
- **NotFound** - The webhook does not exist.
- **Forbidden** - Insufficient permissions to delete the webhook.
- **ValueError** - The webhook does not have a token associated with it.
```

--------------------------------

### Attachment.to_file

Source: https://discordpy.readthedocs.io/en/latest/api.html

Converts an attachment into a File object suitable for sending in a message.

```APIDOC
## Attachment.to_file

### Description
Converts the attachment into a file object that can be sent in a message. This method handles downloading the attachment data.

### Parameters
- **filename** (Optional[str]) - Optional - The filename to use for the file. If not specified, the original filename is used.
- **description** (Optional[str]) - Optional - The description to use for the file. If not specified, the original description is used.
- **use_cached** (bool) - Optional - Whether to use proxy_url rather than url when downloading. Useful for accessing attachments after they have been deleted.
- **spoiler** (bool) - Optional - Whether the file should be marked as a spoiler.

### Returns
- **File** - The attachment as a file object.

### Raises
- **HTTPException** - Downloading the attachment failed.
- **Forbidden** - You do not have permissions to access this attachment.
- **NotFound** - The attachment was deleted.
```

--------------------------------

### Advanced Converter Interface

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Implements the Converter interface to perform asynchronous operations and access the invocation context.

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

### add_reaction(emoji)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a reaction to the message.

```APIDOC
## add_reaction(emoji)

### Description
Adds a reaction to the message. The emoji may be a unicode emoji or a custom guild Emoji.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to react with.
```

--------------------------------

### Handle wait_for timeout

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

The timeout parameter now raises an asyncio.TimeoutError instead of returning None.

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

### set_author(name, url=None, icon_url=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the author for the embed content. Returns the class instance for chaining.

```APIDOC
### set_author(name, url=None, icon_url=None)

#### Parameters
- **name** (str) - Required - The name of the author (max 256 characters).
- **url** (str) - Optional - The URL for the author.
- **icon_url** (str) - Optional - The URL of the author icon.
```

--------------------------------

### Use Greedy converter for multiple arguments

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Consumes as many arguments as possible until conversion fails. Useful for processing lists of members or items.

```python
@bot.command()
async def slap(ctx, members: commands.Greedy[discord.Member], *, reason="no reason"):
    slapped = ", ".join(x.name for x in members)
    await ctx.send(f"{slapped} just got slapped for {reason}")
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

### Delete channel permission overwrites

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes existing permission overwrites for a target by setting the overwrite parameter to None.

```python
await channel.set_permissions(member, overwrite=None)
```

--------------------------------

### Handling Iterable Data Structures

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_async.html

Shows invalid indexing on iterables and the recommended approach of casting to a list to restore sequence behavior.

```python
if client.servers[0].name == "test":
    # do something
```

```python
servers = list(client.servers)
# work with servers
```

--------------------------------

### Perform cleanup during task cancellation

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Check is_being_cancelled within an after_loop hook to perform final operations, such as flushing remaining data, when a task is stopped.

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

### TextChannel.fetch_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single message from the channel by its ID.

```APIDOC
## await TextChannel.fetch_message(id)

### Description
Retrieves a single `Message` from the destination.

### Parameters
- **id** (int) - Required - The message ID to look for.

### Returns
- **Message** - The message requested.

### Raises
- **NotFound** - The specified message was not found.
- **Forbidden** - You do not have the permissions required to get a message.
- **HTTPException** - Retrieving the message failed.
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

### CategoryChannel.move

Source: https://discordpy.readthedocs.io/en/latest/api.html

Moves a channel relative to other channels within the category.

```APIDOC
## await move(**kwargs)

### Description
A rich interface to move a channel relative to others. Requires manage_channels permission.

### Parameters
- **beginning** (bool) - Optional - Move to the beginning.
- **end** (bool) - Optional - Move to the end.
- **before** (Snowflake) - Optional - Move before the given channel.
- **after** (Snowflake) - Optional - Move after the given channel.
- **offset** (int) - Optional - Number of channels to offset the move.
- **category** (Optional[Snowflake]) - Optional - Category to move the channel under.
- **sync_permissions** (bool) - Optional - Sync permissions with the category.
- **reason** (str) - Optional - Reason for the move.
```

--------------------------------

### Update Embed title handling

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Embed title comparison behavior has changed; use None instead of discord.Embed.Empty to represent an unset title.

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

### Group.add_command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds a command or group to the group's internal list of commands.

```APIDOC
## add_command(command, override=False)

### Description
Adds a command or group to this group's internal list of commands.

### Parameters
- **command** (Union[Command, Group]) - Required - The command or group to add.
- **override** (bool) - Optional - Whether to override a pre-existing command or group with the same name.
```

--------------------------------

### Template.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the template metadata.

```APIDOC
## Template.edit(*, name=..., description=...)

### Description
Edit the template metadata. Requires `manage_guild` permission in the source guild.

### Parameters
- **name** (str) - Optional - The template’s new name.
- **description** (Optional[str]) - Optional - The template’s new description.

### Returns
- **Template** - The newly edited template.
```

--------------------------------

### is_nsfw()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the channel is marked as NSFW.

```APIDOC
### is_nsfw()

Returns `bool`: True if the channel is NSFW, False otherwise.
```

--------------------------------

### ban(user, *, reason=None, delete_message_days=..., delete_message_seconds=...)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bans a user from the guild. Requires the 'ban_members' permission.

```APIDOC
## ban(user, *, reason=None, delete_message_days=..., delete_message_seconds=...)

### Description
Bans a user from the guild. The user must meet the abc.Snowflake abc. You must have 'ban_members' to do this.

### Parameters
- **user** (abc.Snowflake) - Required - The user to ban from the guild.
- **delete_message_days** (int) - Optional - The number of days worth of messages to delete (0-7). Deprecated since 2.1.
- **delete_message_seconds** (int) - Optional - The number of seconds worth of messages to delete (0-604800). New in 2.1.
- **reason** (Optional[str]) - Optional - The reason the user got banned.

### Raises
- **NotFound** - The requested user was not found.
- **Forbidden** - You do not have the proper permissions to ban.
- **HTTPException** - Banning failed.
- **TypeError** - You specified both delete_message_days and delete_message_seconds.
```

--------------------------------

### bulk_ban(users, *, reason=None, delete_message_seconds=86400)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bans multiple users from the guild. Requires 'ban_members' and 'manage_guild' permissions. New in version 2.4.

```APIDOC
## bulk_ban(users, *, reason=None, delete_message_seconds=86400)

### Description
Bans multiple users from the guild. The users must meet the abc.Snowflake abc. You must have 'ban_members' and 'manage_guild' to do this.

### Parameters
- **users** (Iterable[abc.Snowflake]) - Required - The users to ban from the guild, up to 200 users.
- **delete_message_seconds** (int) - Optional - The number of seconds worth of messages to delete (0-604800).
- **reason** (Optional[str]) - Optional - The reason the users got banned.

### Raises
- **Forbidden** - You do not have the proper permissions to ban.
- **HTTPException** - Banning failed.

### Returns
- **BulkBanResult** - The result of the bulk ban operation.
```

--------------------------------

### fetch_message(id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a single message from the destination.

```APIDOC
## fetch_message(id)

### Description
Retrieves a single Message from the destination.

### Parameters
- **id** (int) - Required - The message ID to look for.

### Returns
- **Message** - The message asked for.
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

### await delete(delay=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the message. Requires manage_messages permission if deleting another user's message.

```APIDOC
## await delete(delay=None)

### Description
Deletes the message. Your own messages can be deleted without specific permissions, but deleting others' messages requires the `manage_messages` permission.

### Parameters
- **delay** (float) - Optional - The number of seconds to wait before deleting the message.

### Raises
- **Forbidden** - Insufficient permissions.
- **NotFound** - Message already deleted.
- **HTTPException** - Deletion failed.
```

--------------------------------

### @after_loop

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Decorator that registers a coroutine to be called after the loop finishes running.

```APIDOC
## @after_loop

### Description
A decorator that registers a coroutine to be called after the loop finishes running. The coroutine must take no arguments (except self in a class context).

### Parameters
- **coro** (coroutine) - Required - The coroutine to register after the loop finishes.

### Raises
- **TypeError** - The function was not a coroutine.
```

--------------------------------

### discord.utils.sleep_until

Source: https://discordpy.readthedocs.io/en/latest/api.html

Coroutine that sleeps until a specified datetime.

```APIDOC
## discord.utils.sleep_until(when, result=None)

### Description
This function is a coroutine. Sleep until a specified time. If the time supplied is in the past this function will yield instantly.

### Parameters
- **when** (datetime.datetime) - Required - The timestamp in which to sleep until.
- **result** (Any) - Optional - If provided is returned to the caller when the coroutine completes.
```

--------------------------------

### discord.on_raw_bulk_message_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a bulk delete is triggered, regardless of cache state.

```APIDOC
## discord.on_raw_bulk_message_delete(payload)

### Description
Called when a bulk delete is triggered. This is called regardless of the messages being in the internal message cache.

### Parameters
- **payload** (RawBulkMessageDeleteEvent) - Required - The raw event payload data.
```

--------------------------------

### @discord.app_commands.check(predicate)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a custom check to an application command. The predicate must accept an Interaction object and return a boolean.

```APIDOC
## @discord.app_commands.check(predicate)

### Description
A decorator that adds a check to an application command. If the predicate returns a False-like value, a CheckFailure exception is raised.

### Parameters
- **predicate** (Callable[[Interaction], bool]) - Required - The predicate to check if the command should be invoked.
```

--------------------------------

### remove_command

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes an application command from the tree locally. Note that sync() must be called to update the client.

```APIDOC
## remove_command(command, *, guild=None, type=AppCommandType.chat_input)

### Description
Removes an application command from the tree. This only removes the command locally – in order to sync the commands and remove them in the client, sync() must be called.

### Parameters
- **command** (str) - Required - The name of the root command to remove.
- **guild** (Optional[Snowflake]) - Optional - The guild to remove the command from. If not given or None then it removes a global command instead.
- **type** (AppCommandType) - Optional - The type of command to remove. Defaults to chat_input.

### Returns
- **Optional[Union[Command, ContextMenu, Group]]** - The application command that got removed. If nothing was removed then None is returned.
```

--------------------------------

### await _fetch_emoji(emoji_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific custom emoji from the guild by its ID.

```APIDOC
## await _fetch_emoji(emoji_id)

### Description
Retrieves a custom `Emoji` from the guild. For general usage, consider iterating over `emojis` instead.

### Parameters
- **emoji_id** (int) - Required - The emoji’s ID (positional-only).

### Returns
- **Emoji** - The retrieved emoji.

### Raises
- **NotFound** - The emoji requested could not be found.
- **HTTPException** - An error occurred fetching the emoji.
```

--------------------------------

### wait_for(event, *, check=None, timeout=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

A coroutine that waits for a specific WebSocket event to be dispatched. It returns the first event that satisfies the provided check predicate.

```APIDOC
## wait_for(event, *, check=None, timeout=None)

### Description
Waits for a WebSocket event to be dispatched. This is useful for handling sequential interactions like waiting for a specific user reply or reaction.

### Parameters
- **event** (str) - Required - The event name to wait for (without the 'on_' prefix).
- **check** (Optional[Callable[..., bool]]) - Optional - A predicate function to filter events. Must accept the same arguments as the event.
- **timeout** (Optional[float]) - Optional - Seconds to wait before raising asyncio.TimeoutError.

### Returns
- **Any** - Returns the event arguments, or a tuple if multiple arguments are provided.

### Raises
- **asyncio.TimeoutError** - If the timeout is reached.
```

--------------------------------

### discord.on_webhooks_update(channel)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever a webhook is created, modified, or removed from a guild channel. Requires Intents.webhooks to be enabled.

```APIDOC
## discord.on_webhooks_update(channel)

### Description
Called whenever a webhook is created, modified, or removed from a guild channel. This requires Intents.webhooks to be enabled.

### Parameters
- **channel** (abc.GuildChannel) - The channel that had its webhooks updated.
```

--------------------------------

### Wait for message event

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Use a predicate function to filter messages when waiting for a specific event.

```python
def pred(m):
    return m.author == message.author and m.channel == message.channel


msg = await client.wait_for("message", check=pred)
```

--------------------------------

### get_emoji(id)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns an emoji with the given ID.

```APIDOC
## get_emoji(id)

### Description
Returns an emoji with the given ID.

### Parameters
- **id** (int) - Required - The ID to search for.

### Returns
- **Optional[Emoji]** - The custom emoji or None if not found.
```

--------------------------------

### fetch_entitlement

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Retrieves a specific entitlement by its ID.

```APIDOC
## fetch_entitlement(entitlement_id)

### Description
Retrieves a `Entitlement` with the specified ID.

### Parameters
- **entitlement_id** (int) - Required - The entitlement’s ID to fetch from.

### Returns
- **Entitlement** - The entitlement you requested.
```

--------------------------------

### edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the message content, embeds, attachments, or view. This is a coroutine.

```APIDOC
## await edit(content=..., embed=..., embeds=..., attachments=..., suppress=..., delete_after=None, allowed_mentions=..., view=...)

### Description
Edits the message. The content must be able to be transformed into a string via str(content).

### Parameters
- **content** (Optional[str]) - Optional - The new content to replace the message with.
- **embed** (Optional[Embed]) - Optional - The new embed to replace the original with.
- **embeds** (List[Embed]) - Optional - The new embeds to replace the original with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep in the message as well as new files to upload.
- **suppress** (bool) - Optional - Whether to suppress embeds for the message.
- **delete_after** (Optional[float]) - Optional - Number of seconds to wait before deleting the message.
- **allowed_mentions** (Optional[AllowedMentions]) - Optional - Controls the mentions being processed.
- **view** (Optional[Union[View, LayoutView]]) - Optional - The updated view to update this message with.

### Returns
- **Message** - The newly edited message.
```

--------------------------------

### await delete()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the guild. You must be the guild owner to delete the guild. Note: This method is deprecated.

```APIDOC
## await delete()

### Description
Deletes the guild. You must be the guild owner to delete the guild.

### Raises
- **HTTPException** - Deleting the guild failed.
- **Forbidden** - You do not have permissions to delete the guild.
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
```

--------------------------------

### ShardInfo.disconnect

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects a shard.

```APIDOC
## await ShardInfo.disconnect()

### Description
Disconnects a shard. When this is called, the shard connection will no longer be open. If the shard is already disconnected this does nothing.
```

--------------------------------

### cancel()

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Cancels the internal task if it is currently running.

```APIDOC
## cancel()

### Description
Cancels the internal task, if it is running.
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
- **default** (bool) - Required - Whether this checkbox is selected by default.
```

--------------------------------

### Purge messages using a predicate

Source: https://discordpy.readthedocs.io/en/latest/api.html

Use a check function to filter messages for deletion. Requires manage_messages and read_message_history permissions.

```python
def is_me(m):
    return m.author == client.user


deleted = await thread.purge(limit=100, check=is_me)
await thread.send(f"Deleted {len(deleted)} message(s)")
```

--------------------------------

### Apply Command Attributes to a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Use command_attrs to set default attributes for all commands within a cog, which can be overridden by individual command decorators.

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

### get_member_named(name)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Searches for a member in the guild by their name, nickname, or global name.

```APIDOC
## get_member_named(name)

### Description
Returns the first member found that matches the name provided. The lookup order includes username, nickname, and global name.

### Parameters
- **name** (str) - Required - The name of the member to lookup.

### Returns
- **Optional[Member]** - The member in this guild with the associated name, or None if not found.
```

--------------------------------

### @discord.ext.commands.dynamic_cooldown(cooldown, type)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Adds a dynamic cooldown to a command. Unlike standard cooldowns, this takes a function that accepts a Context and returns a Cooldown object or None to bypass.

```APIDOC
## @discord.ext.commands.dynamic_cooldown(cooldown, type)

### Description
A decorator that adds a dynamic cooldown to a Command. If a cooldown is triggered, CommandOnCooldown is raised.

### Parameters
- **cooldown** (Callable[[Context], Optional[Cooldown]]) - Required - A function that takes a context and returns a cooldown or None.
- **type** (BucketType) - Required - The type of cooldown (e.g., per-guild, per-user).
```

--------------------------------

### get_channel(id, /)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a channel or thread from the internal cache by its ID.

```APIDOC
## get_channel(id, /)

### Description
Returns a channel or thread with the given ID from the internal cache.

### Parameters
- **id** (int) - Required - The ID to search for.

### Response
- **Returns** (Optional[Union[abc.GuildChannel, Thread, abc.PrivateChannel]]) - The channel or None if not found.
```

--------------------------------

### callback(interaction)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

The coroutine callback associated with the UI item, triggered when the button is pressed.

```APIDOC
## await callback(interaction)

### Description
The callback associated with this UI item. This can be overridden by subclasses.

### Parameters
- **interaction** (Interaction) - Required - The interaction that triggered this UI item.
```

--------------------------------

### Use typing.Literal for restricted parameter values

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Restricts command arguments to a specific set of allowed values. Raises BadLiteralArgument if the input does not match.

```python
from typing import Literal


@bot.command()
async def shop(ctx, buy_sell: Literal["buy", "sell"], amount: Literal[1, 2], *, item: str):
    await ctx.send(f"{buy_sell.capitalize()}ing {amount} {item}(s)!")
```

--------------------------------

### Refactoring message filtering

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Replace manual filtering loops with list comprehensions using conditional logic.

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

### Retrieve a Cog for Inter-command Communication

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Use bot.get_cog to access another cog instance, enabling data sharing or method invocation between different cogs.

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

### Send channel message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sends a message to a channel. Note that this requires an asynchronous context.

```python
# Do some computational magic for about 10 seconds
await channel.send("Done!")
```

--------------------------------

### Iterate over pinned messages

Source: https://discordpy.readthedocs.io/en/latest/api.html

Uses an asynchronous loop to process pinned messages from a channel.

```python
counter = 0
async for message in channel.pins(limit=250):
    counter += 1
```

--------------------------------

### is_closed()

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Indicates if the websocket connection is closed.

```APIDOC
## is_closed()

### Description
Indicates if the websocket connection is closed.

### Returns
- **bool** - True if closed, False otherwise.
```

--------------------------------

### remove_cog(name, *, guild=..., guilds=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a cog from the bot and returns it.

```APIDOC
## remove_cog(name, *, guild=..., guilds=...)

### Description
Removes a cog from the bot and returns it. All registered commands and event listeners associated with the cog are removed.

### Parameters
- **name** (str) - Required - The name of the cog to remove.
- **guild** (Optional[Snowflake]) - Optional - The guild where the cog group would be removed from.
- **guilds** (List[Snowflake]) - Optional - The guilds where the cog group would be removed from.
```

--------------------------------

### InteractionResponse.defer

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Defers the interaction response, typically used when the interaction is acknowledged and a secondary action will be performed later.

```APIDOC
## await InteractionResponse.defer(ephemeral=False, thinking=False)

### Description
Defers the interaction response. This is only supported for application_command, component, and modal_submit interaction types.

### Parameters
- **ephemeral** (bool) - Optional - Indicates whether the deferred message will eventually be ephemeral.
- **thinking** (bool) - Optional - Indicates whether the deferred type should be deferred_channel_message instead of deferred_message_update.

### Returns
- **InteractionCallbackResponse** - The interaction callback resource.
```

--------------------------------

### MemberCacheFlags.none()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A factory method that creates a MemberCacheFlags instance with all flags disabled.

```APIDOC
## MemberCacheFlags.none()

### Description
A factory method that creates a MemberCacheFlags with everything disabled.

### Returns
- **MemberCacheFlags** - The resulting member cache flags.
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

### Restrict application commands to a guild

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Register commands or cogs to specific guilds using the guilds decorator to limit their availability.

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

### @discord.app_commands.checks.has_any_role(*items)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member has at least one of the specified roles.

```APIDOC
## @discord.app_commands.checks.has_any_role(*items)

### Description
A check that verifies if the member has any of the roles specified. Raises MissingAnyRole or NoPrivateMessage on failure.

### Parameters
- **items** (List[Union[str, int]]) - Required - An argument list of names or IDs to check.
```

--------------------------------

### discord.utils.snowflake_time

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the creation time of the given snowflake ID.

```APIDOC
## discord.utils.snowflake_time(id)

### Description
Returns the creation time of the given snowflake.

### Parameters
- **id** (int) - Required - The snowflake ID.

### Response
- **datetime** (datetime.datetime) - An aware datetime in UTC representing the creation time of the snowflake.
```

--------------------------------

### Handle exceptions during task reconnection

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Use add_exception_type to specify which exceptions should be ignored or handled during the task's reconnection process.

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

### get_tag(tag_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a specific tag associated with the forum by its ID.

```APIDOC
### Method
get_tag(tag_id)

### Description
Returns the tag with the given ID.

### Parameters
- **tag_id** (int) - Required - The ID to search for.

### Returns
- Optional[ForumTag] - The tag with the given ID, or None if not found.
```

--------------------------------

### fetch_scheduled_event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a scheduled event from the guild by ID.

```APIDOC
## await fetch_scheduled_event(scheduled_event_id, with_counts)

### Description
Retrieves a scheduled event from the guild.

### Parameters
- **scheduled_event_id** (int) - Required - The scheduled event ID.
- **with_counts** (bool) - Optional - Whether to include the number of users that are subscribed to the event.

### Errors
- **NotFound**: The scheduled event was not found.
- **HTTPException**: Retrieving the scheduled event failed.

### Response
- **Returns**: ScheduledEvent
```

--------------------------------

### LayoutView.interaction_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine called when an interaction occurs to check if the view should process it.

```APIDOC
## LayoutView.interaction_check(interaction, /)

### Description
A callback that checks whether the view should process item callbacks for the interaction. Override this to implement custom logic like user verification.

### Parameters
- **interaction** (Interaction) - Required - The interaction that occurred.

### Returns
- **bool** - Whether the view children's callbacks should be called.
```

--------------------------------

### edit_role_positions(positions, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Bulk edits the positions of roles in the guild.

```APIDOC
## edit_role_positions(positions, *, reason=None)

### Description
Bulk edits a list of Role in the guild. Requires manage_roles permission.

### Parameters
- **positions** (dict) - Required - A dict of Role to int to change positions.
- **reason** (Optional[str]) - Optional - The reason for editing the role positions.

### Returns
- **List[Role]** - A list of all the roles in the guild.
```

--------------------------------

### discord.app_commands.checks.bot_has_permissions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that checks if the bot has the specified permissions. It relies on discord.Interaction.app_permissions and raises BotMissingPermissions if the check fails.

```APIDOC
## discord.app_commands.checks.bot_has_permissions(perms)

### Description
Checks if the bot itself has the permissions listed. This relies on discord.Interaction.app_permissions and raises a BotMissingPermissions exception if the check fails.

### Parameters
- **perms** (discord.Permissions) - Required - The permissions to check for.
```

--------------------------------

### get_partial_messageable(id, *, guild_id=None, type=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Returns a partial messageable with the given channel ID.

```APIDOC
## get_partial_messageable(id, *, guild_id=None, type=None)

### Description
Returns a partial messageable with the given channel ID. Useful if you have a channel_id but do not want to perform an API call.

### Parameters
- **id** (int) - Required - The channel ID.
- **guild_id** (Optional[int]) - Optional - The optional guild ID.
- **type** (Optional[ChannelType]) - Optional - The underlying channel type.

### Returns
- **PartialMessageable** - The partial messageable.
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the channel.

```APIDOC
## await delete(reason=None)

### Description
Deletes the channel. You must have manage_channels permissions.

### Parameters
- **reason** (str) - Optional - The reason for deleting this channel.
```

--------------------------------

### Restrict cogs to a guild

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Add a cog to the bot while specifying a guild to restrict all commands within that cog.

```python
class MyCog(commands.Cog):
    @app_commands.command()
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message("Pong!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(...), guild=discord.Object(123456789012345678))
```

--------------------------------

### Loop a specific number of times

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Set the count parameter in the loop decorator to limit the number of iterations, and use the after_loop decorator to perform cleanup.

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

### Restrict commands via decorator argument

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Pass a guild object directly to the command decorator to restrict it to a specific guild.

```python
@tree.command(guild=discord.Object(123456789012345678))
async def ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")
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

### Update snowflake ID usage from string to integer

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Snowflake IDs (the id attribute) must now be passed as integers instead of strings.

```python
# before
ch = client.get_channel("84319995256905728")
if message.author.id == "80528701850124288":
    ...

# after
ch = client.get_channel(84319995256905728)
if message.author.id == 80528701850124288:
    ...
```

--------------------------------

### discord.app_commands.ContextMenu.error

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that registers a coroutine as a local error handler for the context menu command. The handler must accept two parameters: the interaction and the error.

```APIDOC
## @error(coro)

### Description
A decorator that registers a coroutine as a local error handler. The local error handler is called whenever an exception is raised in the body of the command or during handling of the command.

### Parameters
- **coro** (coroutine) - Required - The coroutine to register as the local error handler. It must take 2 parameters: the interaction and the error.

### Raises
- **TypeError** - Raised if the provided object is not a coroutine.
```

--------------------------------

### discord.ChannelType

Source: https://discordpy.readthedocs.io/en/latest/api.html

An enumeration representing the various types of channels available in Discord, such as text, voice, and forum channels.

```APIDOC
## discord.ChannelType

### Description
Specifies the type of channel. Available types include text, voice, private, group, category, news, stage_voice, news_thread, public_thread, private_thread, forum, and media.
```

--------------------------------

### Retrieve pinned messages

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Iterate over or collect pinned messages from a channel.

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

### Filter and map channel history

Source: https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html

Chain filter and map operations on an AsyncIterator to process specific message data.

```python
async for m_id in channel.history().filter(lambda m: m.author == client.user).map(lambda m: m.id):
    print(m_id)
```

--------------------------------

### Find element in iterable with discord.utils.find

Source: https://discordpy.readthedocs.io/en/latest/api.html

Searches an iterable for the first element matching a predicate function. Returns None if no match is found.

```python
member = discord.utils.find(lambda m: m.name == "Mighty", channel.guild.members)
```

--------------------------------

### Update Guild.bans usage

Source: https://discordpy.readthedocs.io/en/latest/migrating.html

Guild.bans() now returns an asynchronous iterator instead of a list due to API pagination changes.

```python
# before

bans = await guild.bans()

# after
async for ban in guild.bans(limit=1000):
    ...
```

--------------------------------

### discord.on_guild_channel_pins_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever a message is pinned or unpinned from a guild channel.

```APIDOC
## discord.on_guild_channel_pins_update(channel, last_pin)

### Description
Called whenever a message is pinned or unpinned from a guild channel. This requires Intents.guilds to be enabled.

### Parameters
- **channel** (Union[abc.GuildChannel, Thread]) - Required - The guild channel that had its pins updated.
- **last_pin** (Optional[datetime.datetime]) - Required - The latest message that was pinned as an aware datetime in UTC.
```

--------------------------------

### Role.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the role with the provided parameters. Requires the manage_roles permission.

```APIDOC
## await Role.edit(**fields)

### Description
Edits the role. You must have `manage_roles` permission to perform this action. All fields are optional.

### Parameters
- **name** (str) - Optional - The new name of the role.
- **permissions** (Permissions) - Optional - The new permissions for the role.
- **colour** (Union[Colour, int]) - Optional - The new primary colour of the role.
- **color** (Union[Colour, int]) - Optional - Alias for colour.
- **hoist** (bool) - Optional - Whether the role should be displayed separately.
- **display_icon** (Union[Asset, str]) - Optional - The new display icon for the role.
- **mentionable** (bool) - Optional - Whether the role can be mentioned.
- **position** (int) - Optional - The new position of the role.
- **reason** (str) - Optional - The reason for this action to be shown in the audit log.
- **secondary_color** (Colour) - Optional - The new secondary colour.
- **tertiary_color** (Colour) - Optional - The new tertiary colour.

### Response
- **Role** - Returns the newly edited role object.
```

--------------------------------

### End a scheduled event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends the scheduled event by setting its status to completed.

```python
await event.edit(status=EventStatus.completed)
```

--------------------------------

### get_partial_message(message_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Creates a PartialMessage from the message ID. This is useful if you want to work with a message and only have its ID without doing an unnecessary API call.

```APIDOC
## get_partial_message(message_id)

### Description
Creates a `PartialMessage` from the message ID.

### Parameters
- **message_id** (`int`) - Required - The message ID to create a partial message for.

### Returns
- `PartialMessage` - The partial message.
```

--------------------------------

### Use Tuple in FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Using typing.Tuple allows for greedy-like parsing or parsing of pairs.

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

### Reaction.clear()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears all instances of this specific reaction from the message. Requires manage_messages permission.

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

### discord.app_commands.checks.dynamic_cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a dynamic cooldown to a command based on a factory function.

```APIDOC
## discord.app_commands.checks.dynamic_cooldown(factory, *, key=...)

### Description
Adds a dynamic cooldown to a command. The factory function determines the cooldown instance per interaction.

### Parameters
- **factory** (Optional[Callable[[discord.Interaction], Optional[Cooldown]]]) - Required - A function that takes an interaction and returns a cooldown or None.
- **key** (Optional[Callable[[discord.Interaction], collections.abc.Hashable]]) - Optional - A function that returns a key to the mapping denoting the type of cooldown.
```

--------------------------------

### delete(delay=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the message.

```APIDOC
## delete(delay=None)

### Description
Deletes the message.

### Parameters
- **delay** (float) - Optional - Number of seconds to wait before deleting the message.
```

--------------------------------

### @error

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Decorator that registers a coroutine to be called if the task encounters an unhandled exception.

```APIDOC
## @error

### Description
A decorator that registers a coroutine to be called if the task encounters an unhandled exception. The coroutine must take only one argument, the exception raised (except self in a class context).

### Parameters
- **coro** (coroutine) - Required - The coroutine to register in the event of an unhandled exception.

### Raises
- **TypeError** - The function was not a coroutine.
```

--------------------------------

### get_thread(thread_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a thread with the given ID.

```APIDOC
## get_thread(thread_id)

### Description
Returns a thread with the given ID from the internal cache.

### Parameters
- **thread_id** (int) - Required - The ID to search for.

### Returns
- Optional[Thread] - The returned thread or None if not found.
```

--------------------------------

### add_field(name, value, inline=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Adds a field to the embed object. Returns the class instance for chaining.

```APIDOC
### add_field(name, value, inline=True)

#### Parameters
- **name** (str) - Required - The name of the field (max 256 characters).
- **value** (str) - Required - The value of the field (max 1024 characters).
- **inline** (bool) - Optional - Whether the field should be displayed inline.
```

--------------------------------

### @discord.app_commands.guilds

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Restricts a command to specific guilds, preventing it from being registered as a global command.

```APIDOC
## @discord.app_commands.guilds(*guild_ids)

### Description
Associates the given guilds with the command. When added to a CommandTree, these become the default guilds for the command.

### Parameters
- **guild_ids** (Union[int, Snowflake]) - The guilds to associate this command with.
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

### Search for items in an iterable

Source: https://discordpy.readthedocs.io/en/latest/api.html

Searches through an iterable for an item matching the provided keyword arguments.

```python
msg = await discord.utils.get(channel.history(), author__name="Dave")
```

--------------------------------

### VoiceClient.disconnect(*, force=False)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Disconnects the voice client from the voice channel.

```APIDOC
## await VoiceClient.disconnect(*, force=False)

### Description
Disconnects this voice client from voice. This is a coroutine.

### Parameters
- **force** (bool) - Optional - Whether to force the disconnection.
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the message. This is a coroutine.

```APIDOC
## await delete(delay=None)

### Description
Deletes the message.

### Parameters
- **delay** (Optional[float]) - Optional - If provided, the number of seconds to wait before deleting the message.

### Raises
- **Forbidden** - You do not have proper permissions to delete the message.
- **NotFound** - The message was deleted already.
- **HTTPException** - Deleting the message failed.
```

--------------------------------

### LayoutView.find_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Finds an item within the view by its ID.

```APIDOC
## LayoutView.find_item(id, /)

### Description
Gets an item with Item.id set as id, or None if not found.

### Parameters
- **id** (int) - Required - The ID of the component.

### Returns
- **Optional[Item]** - The item found, or None.
```

--------------------------------

### discord.on_thread_delete(thread)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever a thread is deleted. Requires Intents.guilds to be enabled.

```APIDOC
## discord.on_thread_delete(thread)

### Description
Called whenever a thread is deleted. If the thread could not be found in the internal cache this event will not be called.

### Parameters
- **thread** (Thread) - Required - The thread that got deleted.
```

--------------------------------

### Emoji.edit(name=..., roles=..., reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the custom emoji. Requires the manage_emojis permission.

```APIDOC
## await Emoji.edit(name=..., roles=..., reason=None)

### Description
Edits the custom emoji. Returns the newly updated emoji.

### Parameters
- **name** (str) - Optional - The new emoji name.
- **roles** (List[Snowflake]) - Optional - A list of roles that can use this emoji. An empty list can be passed to make it available to everyone.
- **reason** (Optional[str]) - Optional - The reason for editing this emoji. Shows up on the audit log.

### Returns
- **Emoji** - The newly updated emoji.

### Raises
- **Forbidden** - You are not allowed to edit emojis.
- **HTTPException** - An error occurred editing the emoji.
- **MissingApplicationID** - The emoji is owned by an application but the application ID is missing.
```

--------------------------------

### Rename Command Parameters

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Changes the display name of a parameter in the Discord UI while keeping the original name for internal logic.

```python
@app_commands.command()
@app_commands.rename(the_member_to_ban="member")
async def ban(interaction: discord.Interaction, the_member_to_ban: discord.Member):
    await interaction.response.send_message(f"Banned {the_member_to_ban}")
```

--------------------------------

### Translator.unload()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

An asynchronous teardown function for unloading the translation system. This is invoked when a translator is replaced or the client closes.

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

### discord.on_bulk_message_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when multiple messages are bulk deleted.

```APIDOC
## discord.on_bulk_message_delete(messages)

### Description
Called when messages are bulk deleted. Only messages found in the internal message cache are included in the list.

### Parameters
- **messages** (List[Message]) - Required - The messages that have been deleted.
```

--------------------------------

### prune_members

Source: https://discordpy.readthedocs.io/en/latest/api.html

Prunes the guild from its inactive members based on the number of days since their last login.

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

### Guild-Only Command Restriction

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Ensures a command is only usable within a guild context. This is verified server-side and does not trigger local error handlers.

```python
@app_commands.command()
@app_commands.guild_only()
async def my_guild_only_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am only available in guilds!")
```

--------------------------------

### overwrites_for(obj)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns the channel-specific permission overwrites for a given member or role.

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

### discord.on_raw_message_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is deleted, regardless of cache state.

```APIDOC
## discord.on_raw_message_delete(payload)

### Description
Called when a message is deleted. Unlike on_message_delete, this is called regardless of the message being in the internal message cache.

### Parameters
- **payload** (RawMessageDeleteEvent) - Required - The raw event payload data.
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
- **options** (List[discord.CheckboxGroupOption]) - Required - A list of options that can be selected in this checkbox group.
- **max_values** (Optional[int]) - Optional - The maximum number of options that can be selected.
- **min_values** (Optional[int]) - Optional - The minimum number of options that must be selected.
- **required** (bool) - Required - Whether this component is required to be filled before submitting the modal.

### Methods
- **add_option(label, value=..., description=None, default=False)**: Adds an option to the checkbox group.
- **append_option(option)**: Appends an option to the checkbox group.
```

--------------------------------

### InteractionMessage.add_reaction

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Adds a reaction to the interaction response message.

```APIDOC
## InteractionMessage.add_reaction(emoji)

### Description
Adds a reaction to the message. Requires read_message_history permission.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to react with.

### Raises
- **HTTPException** - Adding the reaction failed.
- **Forbidden** - Missing permissions.
- **NotFound** - Emoji not found.
- **TypeError** - Invalid emoji parameter.
```

--------------------------------

### SyncWebhookMessage.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a message object directly.

```APIDOC
## edit(content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, view=...)

### Description
Edits the message and returns the newly edited message.

### Parameters
- **content** (Optional[str]) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Union[discord.ui.View, discord.ui.LayoutView]) - Optional - The updated view to update this message with.
```

--------------------------------

### Wait for a message event

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Uses wait_for to pause execution until a specific message is received that satisfies the check function.

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

### MessageReference

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents a reference to a message, used for replies or linking to specific messages.

```APIDOC
## class discord.MessageReference

### Description
Represents a reference to a `Message`. This class can be constructed by users to reference messages for replies or other operations.

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
Creates a `MessageReference` from an existing `Message` object.
```

--------------------------------

### Private Channel Only Command Restriction

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Restricts a command to DMs and group DMs. This is verified server-side and does not trigger local error handlers.

```python
@app_commands.command()
@app_commands.private_channel_only()
async def my_private_channel_only_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am only available in DMs and GDMs!")
```

--------------------------------

### PartialMessage

Source: https://discordpy.readthedocs.io/en/latest/api.html

Represents a partial message, used when only the message ID and channel are known, allowing for limited interactions.

```APIDOC
## class discord.PartialMessage

### Description
Represents a partial message to aid with working with messages when only a message and channel ID are present. This class is trimmed down and has no rich attributes.

### Constructor
`discord.PartialMessage(channel, id)`

### Attributes
- **channel** (Union[PartialMessageable, TextChannel, StageChannel, VoiceChannel, Thread, DMChannel]) - The channel associated with this partial message.
- **id** (int) - The message ID.
- **guild** (Optional[Guild]) - The guild that the partial message belongs to.
- **jump_url** (str) - A URL that allows the client to jump to this message.

### Methods
#### fetch()
This function is a coroutine. Fetches the partial message to a full `Message` object.

- **Raises**:
  - `NotFound`: The message was not found.
  - `Forbidden`: You do not have the permissions required to get a message.
  - `HTTPException`: Retrieving the message failed.
- **Returns**: `Message`
```

--------------------------------

### discord.on_raw_message_edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is edited, regardless of cache state.

```APIDOC
## discord.on_raw_message_edit(payload)

### Description
Called when a message is edited. This event is triggered regardless of whether the message is in the internal message cache.

### Parameters
- **payload** (RawMessageUpdateEvent) - Required - The raw event payload data.
```

--------------------------------

### ScheduledEvent.users

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves all users subscribed to a scheduled event.

```APIDOC
## async for ... in ScheduledEvent.users(limit=None, before=None, after=None, oldest_first=...)

### Description
Retrieves all `User` that are subscribed to this event. This requires `Intents.members` to get information about members other than yourself.

### Returns
- **List[User]** - All subscribed users of this event.

### Raises
- **HTTPException** - Retrieving the members failed.
```

--------------------------------

### discord.utils.escape_markdown

Source: https://discordpy.readthedocs.io/en/latest/api.html

Escapes Discord's markdown characters in a given string.

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

### delete_invite(invite, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Revokes an Invite, URL, or ID to an invite.

```APIDOC
## await delete_invite(invite, reason=None)

### Description
Revokes an Invite, URL, or ID to an invite. You must have manage_channels in the associated guild to do this.

### Parameters
- **invite** (Union[Invite, str]) - Required - The invite to revoke.
- **reason** (Optional[str]) - Optional - The reason for deleting the invite.
```

--------------------------------

### CommandTree.set_translator

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Sets the translator to use for translating commands. If a translator was previously set, it will be unloaded.

```APIDOC
## await CommandTree.set_translator(translator)

### Description
Sets the translator to use for translating commands. If a translator was previously set, it will be unloaded using its Translator.unload() method.

### Parameters
- **translator** (Optional[Translator]) - Optional - The translator to use. If None then the translator is removed and unloaded.
```

--------------------------------

### InteractionCallbackResponse.is_thinking

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Checks if the interaction response was a thinking defer.

```APIDOC
## InteractionCallbackResponse.is_thinking()

### Description
Returns a boolean indicating whether the response was a thinking defer.

### Returns
- **bool** - True if the response is a thinking defer, False otherwise.
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

### edit(content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the content, embeds, attachments, or view of a webhook message.

```APIDOC
## edit(content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None)

### Description
Edits the message with new content, embeds, attachments, or a view. Note that `embed` and `embeds` should not be mixed.

### Parameters
- **content** (str) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Embed) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (View) - Optional - The updated view to update this message with.

### Returns
- **WebhookMessage** - The newly edited message.
```

--------------------------------

### interaction_check(interaction)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A coroutine callback that checks whether the button's callback should be processed.

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

### VoiceChannel.set_permissions

Source: https://discordpy.readthedocs.io/en/latest/api.html

Sets the channel specific permission overwrites for a target (Member or Role) in the channel. This method replaces existing overwrites.

```APIDOC
## set_permissions(target, overwrite=None, reason=None, **permissions)

### Description
Sets the channel specific permission overwrites for a target in the channel. Requires `manage_roles` permission.

### Parameters
- **target** (Union[Member, Role]) - Required - The member or role to overwrite permissions for.
- **overwrite** (Optional[PermissionOverwrite]) - Optional - The permissions to allow and deny, or None to delete.
- **permissions** (dict) - Optional - Keyword arguments for specific permissions. Cannot be mixed with overwrite.
- **reason** (Optional[str]) - Optional - The reason for the audit log.

### Raises
- **Forbidden** - Missing permissions.
- **HTTPException** - Request failed.
- **NotFound** - Target not in guild.
- **TypeError** - Invalid parameters.
- **ValueError** - Both overwrite and permissions unset.
```

--------------------------------

### Change Bot Presence

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Updates the bot's status and activity using the change_presence coroutine.

```python
game = discord.Game("with the API")
await client.change_presence(status=discord.Status.idle, activity=game)
```

--------------------------------

### @error(coro)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that registers a coroutine as a local error handler for a command.

```APIDOC
## @error(coro)

### Description
Registers a local error handler that is invoked when an exception occurs during command execution. The handler must accept the `interaction` and the `error` (derived from `AppCommandError`).

### Parameters
- **coro** (coroutine) - Required - The coroutine to register as the local error handler.
```

--------------------------------

### set_field_at(index, name, value, inline=True)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Modifies an existing field in the embed object.

```APIDOC
## set_field_at(index, name, value, inline=True)

### Description
Modifies a field to the embed object. The index must point to a valid pre-existing field.

### Parameters
- **index** (int) - Required - The index of the field to modify.
- **name** (str) - Required - The name of the field (up to 256 characters).
- **value** (str) - Required - The value of the field (up to 1024 characters).
- **inline** (bool) - Optional - Whether the field should be displayed inline.
```

--------------------------------

### get_role(role_id)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Returns a role with the given ID from the member's roles.

```APIDOC
## get_role(role_id)

### Description
Returns a role with the given ID from roles which the member has.

### Parameters
- **role_id** (int) - Required - The ID to search for.

### Returns
- **Optional[Role]** - The role or None if not found.
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

### Member.is_on_mobile()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Determines if a member is active on a mobile device.

```APIDOC
## Member.is_on_mobile()

### Description
A helper function that determines if a member is active on a mobile device.

### Returns
- **bool** - True if the member is active on mobile, False otherwise.
```

--------------------------------

### delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the thread.

```APIDOC
## delete(*, reason=None)

### Description
Deletes this thread. Requires manage_threads permission.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this thread.
```

--------------------------------

### Add reaction to message

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Add a reaction to a message using unicode or custom emoji.

```python
emoji = "\N{THUMBS UP SIGN}"
# or '\U0001f44d' or '👍'
await message.add_reaction(emoji)
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
- **limit** (Optional[bool]) - Optional - Number of threads to retrieve.
- **before** (Optional[Union[abc.Snowflake, datetime.datetime]]) - Optional - Retrieve threads before the given date or ID.
- **private** (bool) - Optional - Whether to retrieve private archived threads.
- **joined** (bool) - Optional - Whether to retrieve private archived threads that you have joined.

### Yields
- **Thread** - The archived threads.
```

--------------------------------

### DM-Only Command Restriction

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Restricts a command to bot DMs. This is verified server-side and does not trigger local error handlers.

```python
@app_commands.command()
@app_commands.dm_only()
async def my_dm_only_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("I am only available in DMs!")
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

### AutoShardedClient.is_ws_ratelimited()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the websocket is currently rate limited. This is useful for determining whether to query members via HTTP or the gateway.

```APIDOC
## is_ws_ratelimited()

### Description
Returns a boolean indicating whether the websocket is currently rate limited. This checks if any of the shards are rate limited.

### Returns
- **bool** - True if the websocket is rate limited, False otherwise.
```

--------------------------------

### Loop.change_interval

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Changes the interval for the sleep time of the loop.

```APIDOC
## Loop.change_interval(*, seconds=0, minutes=0, hours=0, time=...)

### Description
Changes the interval for the sleep time.
```

--------------------------------

### discord.on_private_channel_update

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called whenever a private group DM is updated.

```APIDOC
## discord.on_private_channel_update(before, after)

### Description
Called whenever a private group DM is updated, such as a change in name or topic. This requires Intents.messages to be enabled.

### Parameters
- **before** (GroupChannel) - Required - The updated group channel’s old info.
- **after** (GroupChannel) - Required - The updated group channel’s new info.
```

--------------------------------

### discord.ui.RadioGroup

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Represents a radio group component within a modal, allowing users to select one option from a list.

```APIDOC
## class discord.ui.RadioGroup(custom_id=..., required=True, options=..., id=None)

### Description
Represents a radio group component within a modal. New in version 2.7.

### Methods

#### add_option(label, value=..., description=None, default=False)
Adds an option to the group.
- **label** (str) - Required - The label displayed to users (max 100 chars).
- **value** (str) - Optional - The value of the option (max 100 chars).
- **description** (Optional[str]) - Optional - Additional description (max 100 chars).
- **default** (bool) - Optional - Whether this option is selected by default.

#### append_option(option)
Appends a pre-existing discord.RadioGroupOption to the group.
- **option** (discord.RadioGroupOption) - Required - The option to append.
```

--------------------------------

### clear_reaction(emoji)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears a specific reaction from the message.

```APIDOC
## clear_reaction(emoji)

### Description
Clears a specific reaction from the message.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to clear.
```

--------------------------------

### WebhookMessage.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a specific WebhookMessage instance.

```APIDOC
## WebhookMessage.edit(content=..., embeds=..., embed=..., attachments=..., view=..., allowed_mentions=None)

### Description
Edits the message and returns the newly edited message object.

### Parameters
- **content** (str) - Optional - The new content for the message.
- **embeds** (List[Embed]) - Optional - The new list of embeds.
- **embed** (Embed) - Optional - The new single embed.
- **attachments** (List[Union[Attachment, File]]) - Optional - The new list of attachments.
- **view** (Union[View, LayoutView]) - Optional - The new view to attach.
- **allowed_mentions** (AllowedMentions) - Optional - Mentions configuration.
```

--------------------------------

### Member.edit

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits the member's data, such as nickname, roles, voice channel, or timeout status. Requires specific permissions depending on the fields being modified.

```APIDOC
## Member.edit(nick=..., mute=..., deafen=..., suppress=..., roles=..., voice_channel=..., timed_out_until=..., bypass_verification=..., avatar=..., banner=..., bio=..., reason=None)

### Description
Edits the member's data. Note that uploading an avatar or banner requires a bytes-like object.

### Parameters
- **nick** (Optional[str]) - Optional - The member's new nickname.
- **mute** (bool) - Optional - Indicates if the member should be guild muted.
- **deafen** (bool) - Optional - Indicates if the member should be guild deafened.
- **suppress** (bool) - Optional - Indicates if the member should be suppressed in stage channels.
- **roles** (List[Role]) - Optional - The member's new list of roles.
- **voice_channel** (Optional[Union[VoiceChannel, StageChannel]]) - Optional - The voice channel to move the member to.
- **timed_out_until** (Optional[datetime.datetime]) - Optional - The date the member's timeout should expire.
- **bypass_verification** (bool) - Optional - Indicates if the member should bypass guild verification.
- **avatar** (Optional[bytes]) - Optional - Bytes-like object for the new avatar.
- **banner** (Optional[bytes]) - Optional - Bytes-like object for the new banner.
- **bio** (Optional[str]) - Optional - The new bio for the member.
- **reason** (Optional[str]) - Optional - The reason for the audit log.

### Returns
- **Member** (Optional[Member]) - The newly updated member object.
```

--------------------------------

### await _delete_emoji(emoji, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a custom emoji from the guild.

```APIDOC
## await _delete_emoji(emoji, reason=None)

### Description
Deletes the custom `Emoji` from the guild. Requires `manage_emojis` permission.

### Parameters
- **emoji** (abc.Snowflake) - Required - The emoji to delete (positional-only).
- **reason** (Optional[str]) - Optional - The reason for deleting this emoji for the audit log.

### Raises
- **Forbidden** - You are not allowed to delete emojis.
- **HTTPException** - An error occurred deleting the emoji.
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

### edit

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the content, embeds, or other attributes of the interaction message.

```APIDOC
## edit(content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, delete_after=None, poll=...)

### Description
Edits the message with new content, embeds, or attachments.

### Parameters
- **content** (Optional[str]) - Optional - New message content.
- **embeds** (List[Embed]) - Optional - List of embeds.
- **embed** (Optional[Embed]) - Optional - Single embed.
- **attachments** (List[Union[Attachment, File]]) - Optional - List of attachments.
- **allowed_mentions** (AllowedMentions) - Optional - Mentions processing configuration.
- **view** (Optional[Union[View, LayoutView]]) - Optional - Updated view.
- **delete_after** (Optional[float]) - Optional - Seconds to wait before deleting.
- **poll** (Poll) - Optional - Poll to create.
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

### Errors
- **Forbidden**: You are not allowed to delete stickers.
- **HTTPException**: An error occurred deleting the sticker.
```

--------------------------------

### discord.on_raw_poll_vote_add / discord.on_raw_poll_vote_remove

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a poll gains or loses a vote, regardless of cache state.

```APIDOC
## discord.on_raw_poll_vote_add(payload)
## discord.on_raw_poll_vote_remove(payload)

### Description
Called when a Poll gains or loses a vote. This is called regardless of the state of the internal user and message cache.

### Parameters
- **payload** (RawPollVoteActionEvent) - Required - The raw event payload data.
```

--------------------------------

### role_member_counts()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves a mapping of roles to the number of members that have it.

```APIDOC
## role_member_counts()

### Description
Retrieves a mapping of roles to the number of members that have it.

### Returns
- **Dict[Union[Object, Role], int]** - A mapping of roles to the number of members that have it.
```

--------------------------------

### mentioned_in(message)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the user is mentioned in the specified message.

```APIDOC
## mentioned_in(message)

### Description
Checks if the user is mentioned in the specified message.

### Parameters
- **message** (Message) - Required - The message to check if you’re mentioned in.

### Returns
- **bool** - Indicates if the user is mentioned in the message.
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

### WidgetMember.mentioned_in

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if the user is mentioned in the specified message.

```APIDOC
## WidgetMember.mentioned_in(message)

### Description
Checks if the user is mentioned in the specified message.

### Parameters
- **message** (Message) - Required - The message to check if you're mentioned in.

### Returns
- **bool** - Indicates if the user is mentioned in the message.
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

### discord.app_commands.checks.cooldown

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A decorator that adds a static cooldown to a command, limiting usage frequency.

```APIDOC
## discord.app_commands.checks.cooldown(rate, per, *, key=...)

### Description
Adds a cooldown to a command, allowing it to be used a specific amount of times in a specific time frame. If triggered, CommandOnCooldown is raised.

### Parameters
- **rate** (int) - Required - The number of times a command can be used before triggering a cooldown.
- **per** (float) - Required - The amount of seconds to wait for a cooldown when it’s been triggered.
- **key** (Optional[Callable[[discord.Interaction], collections.abc.Hashable]]) - Optional - A function that returns a key to the mapping denoting the type of cooldown.
```

--------------------------------

### discord.MessageType

Source: https://discordpy.readthedocs.io/en/latest/api.html

An enumeration representing the type of a message, used to distinguish between regular messages and various system messages.

```APIDOC
## discord.MessageType

### Description
Specifies the type of `Message`. This is used to denote if a message is to be interpreted as a system message or a regular message.

### Methods
- **is_deletable()** (bool) - Checks if the message type is deletable, as some system messages cannot be deleted.
```

--------------------------------

### discord.on_reaction_remove(reaction, user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message has a reaction removed from it. Requires Intents.reactions and Intents.members to be enabled.

```APIDOC
## discord.on_reaction_remove(reaction, user)

### Description
Called when a message has a reaction removed from it. If the message is not in the internal cache, this event will not be called.

### Parameters
- **reaction** (Reaction) - The current state of the reaction.
- **user** (Union[Member, User]) - The user whose reaction was removed.
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
- **roles** (abc.Snowflake) - Required - An argument list of abc.Snowflake representing a Role to remove from the member.
- **reason** (str) - Optional - The reason for removing these roles. Shows up on the audit log.
- **atomic** (bool) - Optional - Whether to atomically remove roles.
```

--------------------------------

### discord.on_poll_vote_add / discord.on_poll_vote_remove

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a poll gains or loses a vote.

```APIDOC
## discord.on_poll_vote_add(user, answer)
## discord.on_poll_vote_remove(user, answer)

### Description
Called when a Poll gains or loses a vote. Requires the user and answer's poll parent message to be cached.

### Parameters
- **user** (Union[User, Member]) - Required - The user that performed the action.
- **answer** (PollAnswer) - Required - The answer the user voted or removed their vote from.
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
```

--------------------------------

### Reaction.remove(user)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a specific user's reaction from the message. Requires manage_messages permission if removing a reaction that is not your own.

```APIDOC
## await Reaction.remove(user)

### Description
Removes the reaction by the provided user from the message.

### Parameters
- **user** (abc.Snowflake) - Required - The user or member from which to remove the reaction.

### Raises
- **HTTPException** - Removing the reaction failed.
- **Forbidden** - You do not have the proper permissions to remove the reaction.
- **NotFound** - The user you specified, or the reaction’s message was not found.
```

--------------------------------

### @discord.app_commands.checks.has_role(item)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

A check that verifies if the member invoking the command has the specified role by name or ID.

```APIDOC
## @discord.app_commands.checks.has_role(item)

### Description
A check that verifies if the member invoking the command has the role specified via name or ID. Raises MissingRole or NoPrivateMessage on failure.

### Parameters
- **item** (Union[int, str]) - Required - The name or ID of the role to check.
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

### Cancel a scheduled event

Source: https://discordpy.readthedocs.io/en/latest/api.html

Cancels the scheduled event by setting its status to cancelled.

```python
await event.edit(status=EventStatus.cancelled)
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

### Positional FlagConverter

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html

Defines a positional flag within a FlagConverter class.

```python
class BanFlags(commands.FlagConverter):
    members: List[discord.Member] = commands.flag(name="member", positional=True, default=lambda ctx: [])
    reason: Optional[str] = None
```

--------------------------------

### Disable view items on timeout

Source: https://discordpy.readthedocs.io/en/latest/faq.html

Update the view's message after disabling all children in the on_timeout method.

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

### discord.on_message_delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Called when a message is deleted. Requires the message to be in the internal message cache.

```APIDOC
## discord.on_message_delete(message)

### Description
Called when a message is deleted. If the message is not found in the internal message cache, this event will not be called.

### Parameters
- **message** (Message) - Required - The deleted message.
```

--------------------------------

### remove_user

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a user from the thread.

```APIDOC
## remove_user(user)

### Description
Removes a user from the thread. Requires manage_threads permission or being the thread creator.

### Parameters
- **user** (abc.Snowflake) - Required - The user to remove from the thread.
```

--------------------------------

### Purge messages from a channel

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes messages that match a specific check function. Requires manage_messages and read_message_history permissions.

```python
def is_me(m):
    return m.author == client.user


deleted = await channel.purge(limit=100, check=is_me)
await channel.send(f"Deleted {len(deleted)} message(s)")
```

--------------------------------

### discord.app_commands.ContextMenu.remove_check

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes a check from the command.

```APIDOC
## remove_check(func)

### Description
Removes a check from the command. This function is idempotent and will not raise an exception if the function is not in the command's checks.

### Parameters
- **func** (callable) - Required - The function to remove from the checks.
```

--------------------------------

### delete_messages(messages, *, reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a list of messages in the thread. This method supports bulk deletion for multiple messages.

```APIDOC
## delete_messages(messages, *, reason=None)

### Description
Deletes a list of messages. This is similar to Message.delete() except it bulk deletes multiple messages. You cannot bulk delete more than 100 messages or messages that are older than 14 days old. Requires manage_messages permission.

### Parameters
- **messages** (Iterable[abc.Snowflake]) - Required - An iterable of messages denoting which ones to bulk delete.
- **reason** (Optional[str]) - Optional - The reason for deleting the messages. Shows up on the audit log.
```

--------------------------------

### remove_command(name)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a command from the internal list of commands.

```APIDOC
## remove_command(name)

### Description
Removes a Command from the internal list of commands. Can also be used to remove aliases.

### Parameters
- **name** (str) - Required - The name of the command to remove.
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

### remove_listener(func, *, name=...)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a listener from the pool of listeners.

```APIDOC
## remove_listener(func, *, name=...)

### Description
Removes a listener from the pool of listeners.

### Parameters
- **func** (function) - Required - The function that was used as a listener to remove.
- **name** (str) - Optional - The name of the event to remove.
```

--------------------------------

### edit_message

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Responds to an interaction by editing the original message of a component or modal interaction.

```APIDOC
## await edit_message(content=..., embed=..., embeds=..., attachments=..., view=..., allowed_mentions=..., delete_after=None, suppress_embeds=...)

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

### edit_original_response()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Edits the original interaction response message.

```APIDOC
## await edit_original_response(*, content=..., embeds=..., embed=..., attachments=..., allowed_mentions=None, view=..., poll=...)

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

### Remove a Cog

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html

Remove a registered cog from the bot by its name.

```python
await bot.remove_cog("Greetings")
```

--------------------------------

### discord.utils.maybe_coroutine

Source: https://discordpy.readthedocs.io/en/latest/api.html

A helper function that awaits the result of a function if it is a coroutine, or returns the result if it is not.

```APIDOC
## discord.utils.maybe_coroutine(f, *args, **kwargs)

### Description
A helper function that will await the result of a function if it’s a coroutine or return the result if it’s not. This is useful for functions that may or may not be coroutines.

### Parameters
- **f** (Callable) - Required - The function or coroutine to call.
- ***args** - Optional - The arguments to pass to the function.
- ***kwargs** - Optional - The keyword arguments to pass to the function.

### Response
- **result** (Any) - The result of the function or coroutine.
```

--------------------------------

### remove_check(func, *, call_once=False)

Source: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html

Removes a global check from the bot.

```APIDOC
## remove_check(func, *, call_once=False)

### Description
Removes a global check from the bot. This function is idempotent.

### Parameters
- **func** (function) - Required - The function to remove from the global checks.
- **call_once** (bool) - Optional - Whether the function was added with call_once=True.
```

--------------------------------

### remove_attachments

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes attachments from the message. This is a coroutine.

```APIDOC
## await remove_attachments(*attachments)

### Description
Removes attachments from the message.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove from the message.

### Returns
- **InteractionMessage** - The newly edited message.

### Raises
- **HTTPException** - Editing the message failed.
- **Forbidden** - Tried to edit a message that isn’t yours.
```

--------------------------------

### ActionRow.remove_item

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes an item from the action row.

```APIDOC
## remove_item(item)

### Description
Removes an item from the action row. This function returns the class instance to allow for fluent-style chaining.

### Parameters
- **item** (Item) - Required - The item to remove from the action row.
```

--------------------------------

### PollAnswer.voters()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Retrieves an asynchronous iterator of users who have voted on a specific poll answer. This method is available on PollAnswer objects.

```APIDOC
## PollAnswer.voters(limit=None, after=None)

### Description
Returns an asynchronous iterator representing the users that have voted on this answer. This can only be called when the parent poll was sent to a message.

### Parameters
- **limit** (Optional[int]) - Optional - The maximum number of results to return. If not provided, returns all the users who voted on this poll answer.
- **after** (Optional[abc.Snowflake]) - Optional - For pagination, voters are sorted by member.

### Yields
- **Union[User, Member]** - The member (if retrievable) or the user that has voted on this poll answer.

### Raises
- **HTTPException** - Retrieving the users failed.
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

### Emoji.delete(reason=None)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes the custom emoji. Requires the manage_emojis permission if the emoji is not application-owned.

```APIDOC
## await Emoji.delete(reason=None)

### Description
Deletes the custom emoji. You must have `manage_emojis` to do this if `is_application_owned()` is `False`.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting this emoji. Shows up on the audit log.

### Raises
- **Forbidden** - You are not allowed to delete emojis.
- **HTTPException** - An error occurred deleting the emoji.
- **MissingApplicationID** - The emoji is owned by an application but the application ID is missing.
```

--------------------------------

### await end_poll()

Source: https://discordpy.readthedocs.io/en/latest/api.html

A coroutine that ends the poll attached to the message. Only the message author can perform this action.

```APIDOC
## await end_poll()

### Description
Ends the Poll attached to this message. This can only be done if you are the message author.

### Returns
- **Message** - The updated message.
```

--------------------------------

### Loop.remove_exception_type

Source: https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html

Removes exception types from being handled during the reconnect logic.

```APIDOC
## Loop.remove_exception_type(*exceptions)

### Description
Removes exception types from being handled during the reconnect logic.

### Returns
- **bool** - Whether all exceptions were successfully removed.
```

--------------------------------

### ScheduledEvent.delete

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a scheduled event. Requires manage_events permissions.

```APIDOC
## await ScheduledEvent.delete(reason=None)

### Description
Deletes the scheduled event. You must have `manage_events` to do this.

### Parameters
- **reason** (Optional[str]) - Optional - The reason for deleting the scheduled event. Shows up on the audit log.

### Raises
- **Forbidden** - You do not have permissions to delete the scheduled event.
- **HTTPException** - Deleting the scheduled event failed.
```

--------------------------------

### InteractionMessage.clear_reaction

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Clears a specific reaction from the interaction response message.

```APIDOC
## InteractionMessage.clear_reaction(emoji)

### Description
Clears a specific reaction from the message. Requires manage_messages permission.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to clear.

### Raises
- **HTTPException** - Clearing the reaction failed.
- **Forbidden** - Missing permissions.
- **NotFound** - Emoji not found.
- **TypeError** - Invalid emoji parameter.
```

--------------------------------

### AutoModRule.is_exempt

Source: https://discordpy.readthedocs.io/en/latest/api.html

Checks if a specific object (role, channel, or thread) is exempt from the auto moderation rule.

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

### remove_reaction(emoji, member)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes a reaction from the message by a specific member.

```APIDOC
## await remove_reaction(emoji, member)

### Description
Remove a reaction by the member from the message. This is a coroutine.

### Parameters
- **emoji** (Union[Emoji, Reaction, PartialEmoji, str]) - Required - The emoji to remove.
- **member** (abc.Snowflake) - Required - The member for which to remove the reaction.
```

--------------------------------

### InteractionCallbackResponse.is_ephemeral

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Checks if the interaction response was ephemeral.

```APIDOC
## InteractionCallbackResponse.is_ephemeral()

### Description
Returns a boolean indicating whether the response was ephemeral.

### Returns
- **bool** - True if the response is ephemeral, False otherwise.
```

--------------------------------

### Webhook.edit_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a message owned by the webhook.

```APIDOC
## Webhook.edit_message

### Description
Edits a message owned by this webhook. This is a lower-level interface to `WebhookMessage.edit()`.

### Parameters
- **message_id** (int) - Required - The ID of the message to edit.
- **content** (str) - Optional - The new content.
- **embeds** (List[Embed]) - Optional - The new list of embeds.
- **embed** (Embed) - Optional - The new embed.
- **attachments** (List[Attachment]) - Optional - The new attachments.
- **view** (View) - Optional - The new view.
- **allowed_mentions** (AllowedMentions) - Optional - The new allowed mentions.
- **thread** (Snowflake) - Optional - The thread the message is in.
```

--------------------------------

### remove_author()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Clears the embed's author information. Returns the class instance for chaining.

```APIDOC
### remove_author()

Clears embed author information.
```

--------------------------------

### InteractionMessage.clear_reactions

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes all reactions from the interaction response message.

```APIDOC
## InteractionMessage.clear_reactions()

### Description
Removes all reactions from the message. Requires manage_messages permission.

### Raises
- **HTTPException** - Removing the reactions failed.
- **Forbidden** - Missing permissions.
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
```

--------------------------------

### delete_original_response()

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Deletes the original interaction response message.

```APIDOC
## await delete_original_response()

### Description
Deletes the original interaction response message. This is a lower-level interface to InteractionMessage.delete() to save an HTTP request.
```

--------------------------------

### remove_field(index)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes a field at a specified index. If the index is invalid, the error is silently swallowed.

```APIDOC
## remove_field(index)

### Description
Removes a field at a specified index. If the index is invalid or out of bounds then the error is silently swallowed.

### Parameters
- **index** (int) - Required - The index of the field to remove.
```

--------------------------------

### edit_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Edits a message sent by a webhook using the message ID and optional content, embeds, attachments, or views.

```APIDOC
## edit(message_id, content=None, embeds=None, embed=None, attachments=None, allowed_mentions=None, view=None, thread=None)

### Description
Edits a message owned by the webhook. Returns the newly edited webhook message.

### Parameters
- **message_id** (int) - Required - The message ID to edit.
- **content** (Optional[str]) - Optional - The content to edit the message with.
- **embeds** (List[Embed]) - Optional - A list of embeds to edit the message with.
- **embed** (Optional[Embed]) - Optional - The embed to edit the message with.
- **attachments** (List[Union[Attachment, File]]) - Optional - A list of attachments to keep or new files to upload.
- **allowed_mentions** (AllowedMentions) - Optional - Controls the mentions being processed.
- **view** (Optional[Union[View, LayoutView]]) - Optional - The updated view to update this message with.
- **thread** (Snowflake) - Optional - The thread the webhook message belongs to.
```

--------------------------------

### remove_attachments(*attachments)

Source: https://discordpy.readthedocs.io/en/latest/api.html

Removes specific attachments from the message.

```APIDOC
## remove_attachments(*attachments)

### Description
Removes attachments from the message.

### Parameters
- **attachments** (Attachment) - Required - Attachments to remove from the message.

### Returns
- **WebhookMessage** - The newly edited message.
```

--------------------------------

### end_poll

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Ends the poll attached to the message.

```APIDOC
## end_poll()

### Description
Ends the `Poll` attached to this message. Can only be performed by the message author.

### Returns
- **Message** - The updated message.
```

--------------------------------

### remove_check(func)

Source: https://discordpy.readthedocs.io/en/latest/interactions/api.html

Removes a previously added check from the command.

```APIDOC
## remove_check(func)

### Description
Removes a check from the command. This operation is idempotent.

### Parameters
- **func** (function) - Required - The function to remove from the checks.
```

--------------------------------

### end_poll()

Source: https://discordpy.readthedocs.io/en/latest/api.html

Ends the poll attached to the message. Only the message author can perform this action.

```APIDOC
## await end_poll()

### Description
Ends the Poll attached to this message. Returns the updated Message object upon success.
```

--------------------------------

### delete_message

Source: https://discordpy.readthedocs.io/en/latest/api.html

Deletes a message owned by the webhook using its ID.

```APIDOC
## delete_message(message_id, thread=None)

### Description
Deletes a message owned by this webhook. This is a lower-level interface to WebhookMessage.delete().

### Parameters
- **message_id** (int) - Required - The message ID to delete.
- **thread** (Snowflake) - Optional - The thread the webhook message belongs to.
```
