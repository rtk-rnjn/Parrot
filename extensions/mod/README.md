# Moderation Commands

Everything a mod team needs to keep a server tidy: kick, ban, mute, warn, clean up messages, hand out roles, and look back at what happened. Each action gets a **case number**, so there's always a paper trail.

> Examples on this page use `!` as the prefix. If your server uses a different one, swap it in.

---

## Read this first

A few rules apply to almost every command here, so they're listed once.

**You need the right permission.** Each command lists what it needs. The bot needs the matching permission too, or it'll tell you it can't do it.

**Role order matters.** You can only act on someone whose top role is *below* yours. The bot can only act on someone whose top role is *below the bot's*. If the bot refuses, check that its role sits high enough in your role list. The server owner is the exception to the "below you" rule, and nobody can punish the server owner.

**Some people are off limits.** You can't kick, ban, mute or warn yourself, the bot, or the server owner.

**Reasons are optional but a good idea.** Type the reason right after the target. It goes into the audit log (with your name on it), the mod log, and the DM the person receives. Keep it under a few hundred characters.

**The person usually gets a DM.** For kicks, bans, softbans, timeouts, mutes and warnings, the bot tries to DM them the reason. If their DMs are closed, the action still goes through.

**Everything is logged as a case.** After each action the bot adds a small `Case #12` note to its reply. If your server has a mod-log channel set up, every case is posted there as well.

**Who can be targeted:** you can mention someone, paste their ID, or type their name. For `kick`, `ban`, `softban` and `massban`, an ID works even for people who have already left (more on that under [Ban](#ban)).

---

## All commands at a glance

| Command | Other names | What it does | You need |
|---|---|---|---|
| `kick` | none | Removes a member (they can rejoin) | Kick Members |
| `ban` | `hackban` | Bans a member, or an ID | Ban Members |
| `massban` | `mass-ban`, `multiban`, `multi-ban` | Bans lots of people at once | Ban Members |
| `softban` | `soft-ban` | Ban + instant unban to wipe their messages | Kick Members |
| `unban` | `pardon` | Lifts a ban | Ban Members |
| `timeout` | `stfu` | Temporarily silences a member | Timeout Members |
| `mute` | none | Same as `timeout`, plus mute role setup | Timeout Members |
| `unmute` | `untimeout` | Un-silences a member | Timeout Members |
| `warn` | `strike` | Gives a member a warning | Timeout Members |
| `warnings` | `strikes`, `infractions` | Lists someone's warnings | Timeout Members |
| `unwarn` | `delwarn`, `removewarn` | Removes one warning | Timeout Members |
| `clearwarns` | `clearwarnings`, `resetwarns` | Removes all of someone's warnings | Timeout Members |
| `case` | none | Shows one moderation case | Timeout Members |
| `cases` | `modlogs` | Browses recent cases | Timeout Members |
| `purge` | `bulkdelete` | Deletes messages that match filters | Manage Messages |
| `clear_reactions` | `clear-reactions` | Strips reactions off recent messages | Manage Messages |
| `cleanup` | none | Tidies up the bot's own messages | Nothing (see below) |
| `role add` | `assign`, `give`, `+`, `+=` | Gives a role to a member | Manage Roles |
| `role remove` | `unassign`, `take`, `-`, `-=` | Takes a role from a member | Manage Roles |
| `role bot` | `bots` | Gives a role to every bot | Manage Roles |
| `role human` | `humans` | Gives a role to every human | Manage Roles |
| `role everyone` | `all` | Gives a role to everyone | Manage Roles |

All of these only work inside a server.

---

## Kick, ban and friends

### Kick

Removes someone from the server. They're free to come back with a new invite.

```
!kick @someone
!kick @someone Spamming invites in general
```

The person has to still be in the server. They get a DM with the reason first.

---

### Ban

Bans someone from the server until they're unbanned.

```
!ban @someone
!ban @someone Repeated harassment
!ban 123456789012345678 Ban evader
```

You can ban by **ID**, even if the person isn't in the server anymore. That's handy for people who leave before you can act, or for banning someone ahead of time. (That's what the `hackban` name means.)

---

### Massban

Ban a whole list of people in one go. Great after a raid.

```
!massban @user1 @user2 123456789012345678 Raid accounts
```

List the people (mentions or IDs, separated by spaces) and then put the reason at the end.

- You can ban up to **200** people at once.
- Anyone who can't be banned (role order, server owner, yourself, the bot) is skipped, and the bot lists who got skipped.
- The bot also needs **Manage Server** for this one, because that's what Discord requires for bulk bans.

---

### Softban

A ban followed immediately by an unban. The person is removed and **their messages from the last 7 days are deleted**, but they can rejoin whenever they like. Good for clearing out a spammer's mess without a permanent punishment.

```
!softban @someone Posted spam links
```

You need Kick Members to use it, and the bot needs Ban Members.

---

### Unban

Lifts a ban. Use the person's **ID** (safest), or their exact username as shown in the ban list.

```
!unban 123456789012345678
!unban 123456789012345678 Appeal accepted
```

If that person isn't banned, the bot tells you.

---

## Timeouts and mutes

There are two ways to silence someone, and the bot picks the right one for you:

- **Timeout**: Discord's built-in feature. It lasts anywhere up to **28 days** and needs no setup.
- **Mute role**: a special role that blocks talking. It's used when you don't give a time, or ask for more than 28 days (a longer or permanent mute).

You don't have to think about it. Just type the command.

### Timeout / mute

`timeout` and `mute` do the same thing when you type them with a person.

```
!timeout @someone 10m
!timeout @someone 2h Arguing in #general
!timeout @someone 7d
!mute @someone
```

- **With a time:** the person is silenced until it runs out. Shows up as a native Discord timeout (when 28 days or less).
- **No time:** the person is muted **indefinitely** with the mute role, until you `unmute` them.
- A timed mute with the role is lifted automatically when the time is up.
- Using the mute role needs one to be set up first (see below). If there isn't one, the bot tells you.

They get a DM saying they were muted or timed out.

---

### Unmute

Lifts a timeout and/or a mute, whichever one they have.

```
!unmute @someone
!unmute @someone Cooled off
```

If they weren't muted, the bot tells you so.

---

### Setting up the mute role

Only needed if you want to use mutes without a time limit (or longer than 28 days). A few commands help you set it up. They all live under `mute`.

| Command | Other names | What it does | You need |
|---|---|---|---|
| `mute create [name]` | `new`, `make`, `setup` | Creates a mute role (called "Muted" unless you pick a name) and sets it up in every channel | Timeout Members, Manage Roles, Manage Channels |
| `mute role <role>` | none | Uses a role you already have as the mute role | Timeout Members, Manage Roles |
| `mute sync` | `synchronize`, `synchronise` | Re-applies the mute role's permissions to every channel (use this after adding new channels) | Timeout Members, Manage Roles, Manage Channels |
| `mute remove` | `delete`, `del`, `rm`, `unbind` | Deletes the mute role and forgets all current mutes | Timeout Members, Manage Roles |
| `mute list` | `show`, `view`, `ls` | Lists everyone currently muted | Timeout Members |

The easiest start is:

```
!mute create
```

That makes the role and locks it out of sending messages, adding reactions, speaking and creating threads in every channel. It shows live progress while it works, and it may take a moment on big servers.

**Good to know about the mute role:**

- **Mutes stick.** If someone removes their own mute role, the bot puts it back. If a muted person leaves and rejoins, they're muted again.
- If you give someone the mute role by hand, the bot notices and remembers them as muted.
- The role must be below the bot's top role, and can't be `@everyone` or a bot/integration role.
- `mute list` shows people muted with the role *and* people on a Discord timeout.

---

## Warnings

Warnings are a gentle way of keeping track of repeated small stuff.

### Warn

```
!warn @someone Please stop spamming emojis
```

The bot:

1. Saves the warning
2. DMs them the reason, how many active warnings they have, and when this one runs out
3. Replies with their new active warning count

Warnings **expire after 60 days**. Only *active* warnings count towards the total. Depending on how your server is set up, collecting enough active warnings can trigger automatic punishments.

---

### Warnings (the list)

See someone's warnings, newest first, including expired ones. Leave the name out to see **your own**.

```
!warnings @someone
!warnings
```

Each warning has a number (like `#2`), a status (Active or Expired), who gave it, when, and the reason. Use that number with `unwarn`.

---

### Unwarn

Removes **one** specific warning.

```
!unwarn @someone 2
!unwarn @someone 2 Issued by mistake
```

Look up the number with `warnings` first.

---

### Clearwarns

Wipes **every** warning (active and expired) from someone.

```
!clearwarns @someone
!clearwarns @someone Fresh start
```

---

## Case history

Every action gets a numbered case, and these two commands let you look back.

### Case

Shows one case in full: what happened, who did it, who it was done to, the reason, and when.

```
!case 12
```

### Cases

Browse recent cases page by page. Add a user to see only the cases about them.

```
!cases
!cases @someone
```

It shows up to the **100 most recent** cases. Older ones are cleared out over time, so if a case isn't found, it's probably been pruned.

---

## Cleaning up messages

### Purge

Bulk delete messages, with optional filters. Think of it like Discord's search bar, but with a delete button.

```
!purge 50
!purge 100 --user @someone
!purge 200 --contains discord.gg --bot yes
```

The number is how many recent messages to look through (default **100**, up to **2000**). Without any filters, it removes everything it finds.

**Filters** you can add:

| Filter | What it removes |
|---|---|
| `--user @someone` | Messages from that person |
| `--contains text` | Messages containing that text (case sensitive) |
| `--prefix text` | Messages that start with that text |
| `--suffix text` | Messages that end with that text |
| `--bot yes` | Messages from bots |
| `--webhooks yes` | Messages from webhooks |
| `--embeds yes` | Messages with embeds |
| `--files yes` | Messages with attachments |
| `--emoji yes` | Messages with custom emoji |
| `--reactions yes` | Messages with reactions |
| `--after <message ID>` | Only look at messages after this one |
| `--before <message ID>` | Only look at messages before this one |
| `--require any` | Remove a message if it matches **any** filter (the default is that it must match **all** of them) |

**Things to know:**

- Discord won't bulk delete messages older than **14 days**, so those are always left alone.
- When it finishes, the bot posts a summary of how many messages it removed and from whom. That summary disappears after about 10 seconds.
- Purges are recorded in the mod log.

---

### Clear reactions

Removes all the reactions from recent messages in the channel.

```
!clear_reactions
!clear_reactions 300
```

The number is how many recent messages to check (default **100**, up to **2000**).

---

### Cleanup

Cleans up after the bot: removes its recent messages from the channel. Anyone can use it.

```
!cleanup
!cleanup 50
```

- **Regular members** can search the last **25** messages and only clear the bot's own replies.
- **People with Manage Messages** can search up to **1000** messages, and the bot will also remove messages that look like commands aimed at it.
- Afterwards you get a quick tally of whose messages were removed, which disappears after 10 seconds.
- There's a short cooldown per channel.

---

## Roles

The `role` command is a toolbox. Type `!role` by itself to see the list.

### Giving and taking roles

```
!role add @someone Member
!role remove @someone Member
```

Shortcuts work too: `!role + @someone Member` and `!role - @someone Member`.

### Giving a role to lots of people at once

```
!role human Member       → every human in the server
!role bot Bots           → every bot in the server
!role everyone Member    → everyone
```

While it runs, the bot shows live progress (the last few people it handled and a counter). When it's done you get a summary: how many succeeded, how many failed, how long it took, and why any failed. Anyone who already has the role is skipped.

Bulk role commands can only run **one at a time per server**, with a short cooldown between uses.

### What roles can you hand out?

- The role must be **below your top role** (unless you're the server owner).
- The role must be **below the bot's top role**.
- You can't hand out `@everyone`, or roles managed by Discord or an integration (like booster or bot roles).

---

## Quick FAQ

**The bot says its role isn't high enough.**
Go to Server Settings, then Roles, and drag the bot's role above the roles it needs to manage.

**What's the difference between a timeout and a mute?**
A timeout is Discord's built-in feature (max 28 days, no setup). A mute uses a role, which can last forever, but needs to be set up with `mute create`.

**Can I ban someone who isn't in the server?**
Yes. Use `!ban <their ID>`.

**I banned the wrong person.**
Use `!unban <ID>`.

**A case number says it wasn't found.**
Old cases are cleared out to keep only the most recent history, so very old ones are gone.

**I want to undo a warning.**
`!warnings @them` to find the number, then `!unwarn @them <number>`.
