# Custom Commands

Parrot give custom command privileges to members. Instead you think any of the command is missing you can create your own command. Creating command can be complex for those who are new to the bot. It is expected to have some basic knowledge of the python and the bot.

> **Note:** The entire custom command feature is in beta. If you find any bugs or have any suggestions, please let me know.

---

To create custom command you need to have a permission level of `MANAGE_GUILD`.

---

## Few things to note

- You are given `message` as instance of CustomMessage, in on_message case, or `reaction` in on_reaction_x case and `member` in on_member_x case.
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
    - `Random`     : `random.randint` function
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
COUNTING_CHANNEL = 999
async def function(message):
    if message.channel.id == COUNTING_CHANNEL:
        data = await get_db()
        if not data.get("count"):
            data["count"] = 0
        data["count"] += 1
        await edit_db(update={"$set": data})
        if message.content != str(data["count"]):
            await message.delete(delay=0)
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

---

## Functions

---

#### `message_send`

To send message in the channel.

```python
await message_send(CHANNEL_ID, content, **kwargs)
```

#### `message_add_reaction`

To add reaction on the message sent.

```python
await message_add_reaction(emoji):
```

#### `message_remove_reaction`

To remove reaction on the message sent of the user.

```python
await message_remove_reaction(emoji, member)
```

#### `message_clear_reactions`

To clear all the reactions from the message sent.

```python
await message_clear_reactions()
```

#### `reactions_users`

To get the list of users who reacted to the message of the specified emoji.

```python
await reactions_users(emoji)
```

#### `channel_create`

To create a channel in the guild.

```python
await channel_create(name, channel_type, **kwargs)
```

#### `channel_edit`

To edit the channel.

```python
await channel_edit(channel_id, **kwargs)
```

#### `channel_delete`

To delete a channel.

```python
await channel_delete(channel_id)
```

#### `role_create`

To create a role in the channel.

```python
await role_create(name, **kwargs)
```

#### `role_edit`

To edit a role 

```python
await role_edit(role_id, **kwargs)
```

#### `role_delete`

To delete a role.

```python
await role_delete(role_id)
```

#### `kick_member`

To kick a member from guild

```python
await kick_member(member_id, reason)
```

#### `ban_member`

To ban member from the guild

```python
await ban_member(member_id, reason)
```

#### `edit_member`

To edit member.

```python
await edit_member(member_id, **kwargs)
```

#### `get_channel`

To get a channel of the guild.

```python
await get_channel(channel_id)
```

#### `get_db`

To get the data of the guild.

```python
await get_db(*, projection, **kwargs)
```

#### `edit_db`

To edit the data of the guild.

```python
await edit_db(**kwargs)
```

#### `del_db`

To delete the data of the guild.

```python
await del_db()
```
