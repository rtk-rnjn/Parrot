# WIP

# Parrot Discord Bot

*Imagine a Discord bot with Mini Ticket System, Moderation tools for admins and lots of fun commands for the users. And International Global Chat.*

---

<p align="center"><img src="https://top.gg/api/widget/servers/800780974274248764.svg"> <img src="https://top.gg/api/widget/upvotes/800780974274248764.svg"> <img src="https://top.gg/api/widget/owner/800780974274248764.svg"></p>

---

#### Invite bot with:-

- [`No permission`](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=0&scope=bot%20applications.commands)
- [`Minimal permission`](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=385088&scope=bot%20applications.commands)
- [`Recommended permission`](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=2013651062&scope=bot%20applications.commands)
- [`Admin permission`](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=8&scope=bot%20applications.commands)
- [`All permission (Not Admin)`](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=545460846583&scope=bot%20applications.commands)

---

## Self Host?

You need to set the environment variables for the bot to work. You can find the tokens and links for the token in `.example-env` file, and do change the name of file to `.env`.

---

You also need to have [`pm2`](https://pm2.keymetrics.io/docs/usage/quick-start/) installed. To install it, run the following command:

```bash
npm install pm2@latest -g
```

---

In case you don't have [`npm`](https://docs.npmjs.com/) installed run the following command to install it:

```bash
sudo apt update
```

```bash
sudo apt install nodejs npm
```

---

Now you need to install dependencies, to do that run the following command, make sure you have [`python`](https://www.python.org/) version `3.11+` installed:

```bash
pip install -r requirements.txt
```

---

After all that you can run the bot with the following command:

```bash
pm2 start pm2.json
```

---

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/b9a3a8eb17a3421bb96a5ea3648f4767)](https://app.codacy.com/gh/rtk-rnjn/Parrot/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
