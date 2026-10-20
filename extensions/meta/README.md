# Meta Commands

These are the "what's going on?" commands. Want to know how the bot is doing, who someone is, what a server looks like, or how to send the owner an idea? It's all here.

> Examples on this page use `!` as the prefix. If your server uses a different one, just swap it in.

---

## All commands at a glance

| Command | Other names | What it does |
|---|---|---|
| `about` | `info`, `botinfo`, `hello`, `hi` | Shows info and stats about the bot |
| `feedback` | none | Sends your idea or suggestion to the bot owner |
| `donate` | `support`, `tip` | Shows how to support the bot |
| `invite` | none | Gives you a link to add the bot to your server |
| `ping` | `latency` | Shows how fast the bot is responding |
| `uptime` | `up` | Shows how long the bot has been online |
| `source` | `src` | Shows the code behind the bot or a specific command |
| `member_count` | `member-count`, `mc` | Shows how many people are in the server |
| `userinfo` | `memberinfo`, `ui`, `mi` | Shows info about a member |
| `avatar` | `pfp`, `av` | Shows someone's profile picture |
| `serverinfo` | `guildinfo`, `si`, `gi` | Shows info about the server |
| `roleinfo` | none | Shows info about a role |
| `channelinfo` | none | Shows info about a channel |
| `announcement` | `announcements` | Shows the latest announcement |
| `changelog` | `changelogs`, `updates`, `whatsnew` | Shows what's new in the bot |

**Good to know:**

- Most of these have a short wait (a few seconds) between uses, so if the bot says to slow down, just give it a moment.
- `member_count`, `userinfo`, `avatar`, `serverinfo`, `roleinfo` and `channelinfo` only work inside a server, not in DMs.

---

## About the bot

### `about`

Your quick "who is this bot?" card. Type `!about` and you get one embed with:

- **Stats**: how many servers and members the bot can see, and how many commands it has
- **Channels**: how many text, voice and category channels it's looking after
- **Process / System**: how much memory and CPU it's using, and what it's running on
- **Versions**: what the bot is built with
- **Uptime**: when it last came online
- **Recent commits**: the last 3 updates made to the code, with links
- **Who made it**, and a reminder that you can send ideas with `!feedback`

There are two buttons underneath. **Source** takes you to the bot's code on GitHub. **Donate** shows how to chip in, but only you can see that message. The buttons stop working after about 5 minutes (the Donate one greys out), so just run `!about` again if you need them.

```
!about
```

---

### `feedback`

Got an idea, found something weird, or just want to say something? This sends it straight to the bot owner's DMs.

```
!feedback It would be great if the bot could do X, because Y happens a lot in our server.
```

A few things to know:

- Your message needs to be **at least 50 characters** and **no more than 1500**. That's so suggestions have enough detail to be useful.
- You can attach a screenshot. The first image shows up in the message the owner receives.
- You can send one every **60 seconds**.
- The owner sees your username and which server you sent it from.
- If the bot can't deliver it, it will tell you and you can try again.

---

### `donate`

Shows how to support the bot with a UPI payment: the UPI ID (easy to copy) and a QR code you can scan with any UPI app.

Donating is **never required**. The bot is free either way.

```
!donate
```

---

### `invite`

Gives you the link to add the bot to your own server.

```
!invite
```

---

### `ping`

Checks how quickly the bot is responding. You'll get three numbers:

- **Gateway**: the bot's connection to Discord
- **API**: how long it took to send you a message
- **Database**: how long the bot took to check its storage

Lower is better. If the numbers look high, the bot is probably having a slow moment.

```
!ping
```

---

### `uptime`

Tells you how long the bot has been online and exactly when it started. If the bot has only just restarted, you'll see something like "a few seconds ago".

```
!uptime
```

---

### `source`

Want to see how a command is made? `source` points you to the exact lines of code on GitHub.

```
!source               → link to the whole project
!source ping          → code for the ping command
!source tag create    → code for a subcommand (use a space or a dot: tag.create)
!source help          → code for the help command
```

You can also use the name of a slash command or a whole category of commands. If you mistype something, the bot will suggest names that look close to what you typed.

---

## Server and member info

### `member_count`

Shows how many people are in the server, split into **humans** and **bots**.

```
!member_count
```

---

### `userinfo`

Shows details about a member. Leave the name out and it shows **you**.

```
!userinfo
!userinfo @someone
```

You'll see:

- Their username, display name, and nickname (if they have one)
- When their account was created
- When they joined this server
- How many roles they have
- A short line of their key permissions, like *Administrator*, *Server Moderator* or *Can Timeout Members*
- Their banner, if they have one

The embed also uses the colour of their highest coloured role.

---

### `avatar`

Shows someone's profile picture, big. Leave the name out and it shows **yours**.

```
!avatar
!avatar @someone
```

If you look up someone else, the bot mentions you so everyone knows who asked. There's also a delete button so you can remove the message when you're done.

---

### `serverinfo`

Everything about the server in one embed:

- Owner and when the server was created
- Member counts (total, humans, bots)
- Channel counts (categories, text, voice)
- Number of roles and emojis, and the boost level
- How many members are online, idle, do not disturb or offline
- Special server features, like Community, Verified, Partnered or a vanity invite link
- Boost details, including who boosted most recently
- Emoji usage, so you can see how many slots are left
- The server banner and icon, if the server has them

If the bot has the right permissions, it also shows how many members are banned and how many invites are active.

```
!serverinfo
```

---

### `roleinfo`

Pick a role, get its details. You can mention it or type its name.

```
!roleinfo @Moderator
!roleinfo Moderator
```

You'll see:

- When it was created
- Its position in the role list
- Whether it's shown separately in the member list ("hoisted")
- Whether it's managed by an integration (bot roles, boost roles and so on)
- Whether anyone can mention it
- How many members have it
- Key permissions
- Its icon or emoji, if it has one

---

### `channelinfo`

Shows details about a channel: its name, ID, when it was created, its position in the list, and what type it is. Leave the channel out and it shows the one you're in.

```
!channelinfo
!channelinfo #general
```

Works with text channels, voice channels, stage channels and categories.

---

## News and updates

### `announcement`

Shows the **latest announcement** from the bot owner, in its own embed with a link to the original post.

```
!announcement
```

---

### `changelog`

Shows what's changed in the bot recently, newest first. Use the buttons to flip through older updates.

```
!changelog
```

The buttons stop working after about 5 minutes. Run the command again if that happens.

---

## Quick FAQ

**The bot says I'm using a command too fast.**
Wait a few seconds and try again. Some commands have a short cooldown to keep things smooth.

**A command says it only works in servers.**
Those commands need a server to look at, so they can't be used in DMs.

**I want to suggest a feature.**
Use `!feedback` with a few sentences about what you'd like and why.

**Where do I find the full list of commands?**
Use the bot's help command. This page covers the Meta group only.
