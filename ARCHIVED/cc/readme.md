# ARCHIVED - THIS COG IS NO LONGER MAINTAINED

# Custom Commands

Parrot give custom command privileges to members. Instead you think any of the command is missing you can create your own command. Creating command can be complex for those who are new to the bot. It is expected to have some basic knowledge of the python and the bot.

> **Note:** The entire custom command feature is in beta. If you find any bugs or have any suggestions, please let me know.

---

To create custom command you need to have a permission level of `MANAGE_GUILD`.

## Few things to note

- You are given `message` as instance of CustomMessage, in on_message case, or `reaction` in on_reaction_x case and `member` in on_member_x case.
- Your code must have a `return` statement at the end, and try to return `None`.
- Your code must be a valid python code.
- Every custom command must have a unique name.
- The total time taken to execute a custom command must not exceed 10 seconds.
- In case of any error, the bot will send a message to the channel where the command was executed.
- The bot will not execute any custom command if the user tries to execute it in a private message.
