# Giveaway Guide

Run giveaways in your server with a button or a reaction. Giveaways survive bot restarts, end on time by themselves, and pick winners fairly from the people who are still eligible.

In this guide, \<prefix> stands for your server's command prefix. The command group is giveaway, with the short aliases gw and gaw.

## Before you start

Who can do what

- Starting, ending, cancelling, rerolling and configuring giveaways needs the Manage Server permission.
- Everyone can enter giveaways and use giveaway list and giveaway info.

Permissions the bot needs in the giveaway channel

| Permission | Why |
| --- | --- |
| View Channel | To see the channel |
| Send Messages | To post the giveaway and the winner announcement |
| Embed Links | The giveaway is shown as an embed |
| Add Reactions | Only for reaction giveaways (from-message) |
| Read Message History | To find the giveaway message when it ends |

## Starting a giveaway

### With an Enter button (recommended)

\<prefix>giveaway start \<duration> \<winners> \<prize>

Example: \<prefix>giveaway start 2d 3 Discord Nitro

- duration: how long it runs, for example 30m, 2h or 3d.
- winners: how many winners to draw, from 1 to 20.
- prize: anything you like, spaces included.

The bot posts an embed with an Enter giveaway button. Members click it and get a private confirmation. The embed shows the prize, the number of winners, when it ends, who hosts it and the required role if there is one.

### From your own message (reaction giveaway)

\<prefix>giveaway from-message \<message> \<duration> \<winners>

Example: \<prefix>giveaway from-message https://discord.com/channels/.../... 1d 1

- The message must be your own message in this server. Its text becomes the prize.
- The bot adds a 🎉 reaction, and members enter by reacting with 🎉.
- Removing the reaction withdraws the entry.
- When the giveaway ends, entries are recounted from the reactions that are on the message at that moment, so nothing is lost if the bot was offline for a while.

## Managing giveaways

Commands that take a giveaway accept any of these: the giveaway ID (shown in the embed footer and in list), the message ID, or a message link.

| Command | What it does |
| --- | --- |
| \<prefix>giveaway list | Shows the running giveaways of this server with their end time and ID |
| \<prefix>giveaway info \<giveaway> | Status, host, winners, entry count, end time and a link to the message |
| \<prefix>giveaway end \<giveaway> | Ends it now and draws the winners |
| \<prefix>giveaway cancel \<giveaway> | Stops it without drawing winners. The message is marked as cancelled |
| \<prefix>giveaway reroll \<giveaway> \[count\] | Draws new winners after it ended. count defaults to 1 |

## How winners are chosen

1. The entrants are shuffled, then checked one by one until enough winners are found.
2. Skipped automatically: bots, members who left the server, and members without the required role (if one is set).
3. If fewer eligible people exist than the number of winners, the giveaway ends with fewer winners. If nobody is eligible, the bot says so.
4. The winners are saved, shown in the embed (button giveaways) and announced as a reply to the giveaway message. If that message was deleted, the announcement is posted in the channel instead.
5. Reroll never picks someone who already won. Run it as often as you need, for example \<prefix>giveaway reroll \<giveaway> 2 to replace two winners.

## After a restart

- Enter buttons keep working, including on old giveaways.
- End timers are restored. A giveaway whose time ran out while the bot was offline is ended as soon as the bot comes back.

## Not available yet

Pause and resume, editing a running giveaway, scheduling for later, templates, bonus entries, account or membership age requirements, and statistics are not part of this version.
