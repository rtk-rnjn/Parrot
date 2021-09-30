# Parrot Discord Bot

A good moderation and Ticket Service bot; over 100+ commands! Basically made for helping the mods! This bot is even great for having fun and to engage people in your server, as it has a lot of meme generator commands and also have global chat and dialing system. Configuring the bot is relatively easy too. It can be found [here](https://github.com/ritik0ranjan/Parrot#bot-setup)

### Self Host?

No Help will be given if You are self Hosting. Tho' Bot is very easy to understand there is No Thetha Theroy. Yes, if you need any Python Help. You can ask me out at my Discord Server. All you need is few API(s)

If you found any Error. In some of the command then please let me know, or you can ask for Pull Request. It would be helpful. Thanks

Bot Invite Link: [Invite Link](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=0&scope=bot)

---

## Bot Setup

#### - **Bot Prefix**

Default prefix is `$` or `@Parrot#9209` (Mention) but if you found is difficult to type you can change the bot prefix. But you can't change the `@Parrot#9209` as prefix. Also, prefix is case **sensitive** and length of prefix must be less than 6 character
```
[p]serverconfig botprefix YOUR_PREFIX_HERE 
```

<br>

#### - **Moderator Logging**

You must be aware what command is being used on whom by whom, especially Mod commands. Parrot can log every action whenever the mod command like `kick` `ban` is used. Pass `None` if you want to remove

```
[p]serverconfig actionlog [CHANNEL]
```

<br>

#### - **Mute Role**

As every moderation bot there is one thing, setting up `MUTE_ROLE`. Parrot can do it without you setup. As per Parrot Bot defination Mute Role should not have `send_messages` permissions. But you can change that too. Pass `None` if you want to remove

```
[p]serverconfig muterole ROLE
```

<br>

#### - **Moderator Role**

Sometimes giving permissions kick ban can be dangerous. If people are not trust worthy. Mod role are like you can use the mod command even if you aren't having real server permission. Pass `None` if you want to remove

```
[p]serverconfig modrole ROLE
```

<br>

---

## Global-Chat Setup

This thing is insane. Feature inspired from World Chat bot. Configuring the `#global-chat` is kinda easy too. 

#### - **Making the channel**

You yourself don't need to do that to be honest. Once you trigger the command bot will create a channel (and webhook of that channel) on the top of the server. Once the channel is created, you can change it's or and whatever you want to do with that.

```
[p]serverconfig gchat
```

<br>

#### - **Ignore-Role in #global-chat**

Again there are anonying people who just spam. People with ignore role can't chat in `#global-chat`. Pass `None` if you want to remove. [I didn't test this feature yet, if incase the this thing is not working then let me know]

```
[p]serverconfig gsetup ignorerole ROLE
```

<br>

---

## Telephone Setup
Another insane feature, I am still improving this. Inspired by Yggdrasil Bot. You can talk to other server people without joining it.

#### - **Channel Setup**

Like in real life your telephone is fixed at a point. Not like Cell Phone. So similarly all kind of calls are made in that channel.

```
[p]telsetup channel [CHANNEL]
```

<br>

#### - **Member Ping**

This is usual that how we come to know someone is calling. Pass `None` if you want to remove. [I didn't test this feature yet, if incase the this thing is not working then let me know]

```
[p]telsetup memberping MEMBER
```

<br>

#### - **Ping Role**

What if the member is offline? You can ping the Role if you want. Pass `None` if you want to remove. [I guess `@everyone` would work too]

```
[p]telsetup pingrole ROLE
```

<br>

#### - **Block**

Some server are really anonying. Like the continously make phone calls. Just to disturb by pinging. You can block those cringe.

```
[p]telsetup block SERVER
```

<br>

#### - **Unblock**

Suppose the cringe server is now DMing your to forgive them. LOL. And they said not doing those thing again.

```
[p]telsetup unblock SERVER
```

<br>

---

## Ticket Setup

If you are unaware then let me know Parrot Support ticket system very nicely. Setting up is easy too. Uff

#### - **Reaction**

Ticket can be created on reaction basis. This can be setup easily by:

```
[p]ticketconfig auto [CHANNEL] [MESSAGE]
```

#### - **Category**

This is optional. By default all the ticket channel are created on the top of the server. If you setup the category then all new category will be created in that category.

```
[p]ticketconfig setcategory CATEGORY
```

<br>

#### - **Add Admin**

There should be Ticket Moderator. Isn't it? This command gives all users with a specific role access to the `admin-level` commands of *Parrot Ticket Bot ONLY*

```
[p]ticketconfig addadminrole ROLE
```

<br>

#### - **Remove Admin**

When you find that ticket mod you choose don't deserve to be mod. Isn't it? This command removes all users with a specific role access to the `admin-level` commands of *Parrot Ticket Bot ONLY*

```
[p]ticketconfig deladminrole ROLE
```

<br>

#### - **Access to Ticket Channel**

This role is important if you want your mods to get the access to that channel

```
[p]ticketconfig addaccess ROLE
```

<br>

#### - **Remove Access from Ticket Channel**

When you find the mods aren't really use full when channel is created. So you decided to remove them.

```
[p]ticketconfig delaccess ROLE
```

<br>

#### - **Logging Setup**

Logging is somewhere important if you run a dedicated server and want to know every single action.

```
[p]ticketconfig setlog [CHANNEL]
```

<br>

#### - **Ping Role**

Sometimes its needed to be get pinged when the new ticket is created.

```
[p]ticketconfig addpingedrole ROLE
```

<br>

#### - **Remove Ping Role**

Now, if you want to remove the role if you don't want that role to be get pinged.

```
[p]ticketconfig delpingedrole ROLE
```

<br>

---


NOTE: 

1. Member having `admin-level` can not have access to the ticket channel unless they have `access` role. `admin-level` can change the `access` and `pinged-role` setting ONLY.

2. Bot will moderate indiscriminately. Means it hardly care about the role level. So it is adviced to place the bot role below the staff role or moderator role.


TODO:

1. To make tag system
2. To make help commands more good
3. To make AutoModeration
4. To make more Todo list. LOL


<br>

__You can get the more info by doing `[p]help <command_name>`__

