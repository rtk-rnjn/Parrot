# Custom Commands

Parrot give custom command privileges to members. Instead you think any of the command is missing you can create your own command. Creating command can be complex for those who are new to the bot. It is expected to have some basic knowledge of the python and the bot.

> **Note:** The entire custom command feature is in beta. If you find any bugs or have any suggestions, please let me know.

---

To create custom command you need to have a permission level of `MANAGE_GUILD`. Syntax as follows:

```
$cc create --name <name> --code <code> --help <command help>
```

---

## Few things to note

- Your code must have an asyncronous function named `function`, which takes `message` as argument, in on_message case, or takes `reaction` and `member` in on_reaction_x case.
- Your code must have a `return` statement at the end, and try to return `None`.
- Your code must be a valid python code.
- Every custom command must have a unique name.
- The total time taken to execute a custom command must not exceed 10 seconds.
- In case of any error, the bot will send a message to the channel where the command was executed.
- The bot will not execute any custom command if the user tries to execute it in a private message.

---

## Variables

    - `message`    : `CustomMessage` Object
    - `Re`         : `re` module
    - `Time`       : `time.time` function
    - `Sleep`      : `asyncio.sleep` function
    - `Datetime`   : `datetime.datetime` class
    - `Random`     : `random` module
    - `Object`     : `discord.Object` class
    - `File`       : `discord.File` class
    - `Embed`      : `discord.Embed` class
    - `Colour`     : `discord.Colour` class
    - `Permissions`: `discord.Permissions` class
    - `PermissionOverwrite`: `discord.PermissionOverwrite` class

---

## Examples

---

#### On Message

```python
async def function(message):
    if message.author.id == 123 and message.channel.id == 456:
        await message_send(f"<@{message.author.id}> Hi there")
    return
```
```python
MOD_ROLE = 123456789
async def function(message):
    if MOD_ROLE in message.author.roles and message.content.lower() == "!publish":
        await message_publish()
    return
```

---

#### On Reaction

```python
MOD_ROLES = 123456789
async def function(reaction, member):
    if reaction_type != 'add':
        return
    if MOD_ROLES in member.author.roles and reaction.emoji == "\N{HAMMER}":
        await ban_member(reaction.message.author.id, "for no reason")
    return
```
```python
async def function(reaction, member):
    if reaction.emoji == "\N{REGIONAL INDICATOR SYMBOL LETTER F}":
        await message_send(f"<@{member.id}> paid respect! `F`")
    return
```
