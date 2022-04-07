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

- Your code must have an asyncronous function named `function`, which takes `message` as argument.
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


