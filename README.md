# Parrot Discord Bot

Imagine a Discord bot with Mini Ticket System, Moderation tools for admins and lots of fun commands for the users. And International Global Chat.

[![Discord Bots](https://top.gg/api/widget/800780974274248764.svg)](https://top.gg/bot/800780974274248764)


Invite bot with:-
 - [No permission](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=0&scope=bot%20applications.commands)
 - [Minimal permission](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=385088&scope=bot%20applications.commands)
 - [Recommended permission](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=2013651062&scope=bot%20applications.commands)
 - [Admin permission](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=8&scope=bot%20applications.commands)
 - [All permission (Not Admin)](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=545460846583&scope=bot%20applications.commands)

## Self Host?

You need to set the environment variables for the bot to work. You can find the tokens and links for the token in `.example-env` file. After that, you need to change the `author_name`, `discriminator` and other credentials in the `config.yml` file.

You also need to have `pm2` installed. To install it, run the following command:

```bash
npm install pm2@latest -g
```

After all that you can run the bot with the following command:

```bash
pm2 start pm2.json
```
