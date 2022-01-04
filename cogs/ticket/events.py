from __future__ import annotations

from core import Parrot, Cog
from utilities.database import parrot_db, ticket_update
import discord
from datetime import datetime

collection = parrot_db["server_config"]

from typing import Optional


class TicketReaction(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def log(
        self, guild, channel: discord.TextChannel, description: str, status: str
    ) -> Optional[discord.Message]:
        await channel.send(
            embed=discord.Embed(
                title="Parrot Ticket Bot",
                timestamp=datetime.utcnow(),
                description=f"{description}",
                color=discord.Color.blue(),
            )
            .add_field(name="Status", value=status)
            .set_footer(text=f"{guild.name}")
        )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        collection = parrot_db["ticket"]
        guild_id = payload.guild_id
        guild = self.bot.get_guild(guild_id)
        data = await collection.find_one({"_id": guild_id})
        if not data:
            return
        user_id = payload.user_id
        member = guild.get_member(user_id)
        if not member:
            return
        if member.bot:
            return

        channel_id = payload.channel_id
        channel = self.bot.get_channel(channel_id)

        message_id = payload.message_id
        emoji = payload.emoji.name

        if message_id == data["message_id"] and channel_id == data["channel_id"]:
            message = await channel.fetch_message(message_id)
        else:
            return
        if (message is not None) and (emoji == "✉️"):
            try:
                await message.remove_reaction("✉️", member)
            except Exception:
                return await channel.send(
                    "Missing Manage Message permisssion to work properly",
                    delete_after=10,
                )

            ticket_number = data["ticket_counter"] + 1
            cat = guild.get_channel(data["category"])

            ticket_channel = await guild.create_text_channel(
                "ticket-{}".format(ticket_number), category=cat
            )
            await ticket_channel.set_permissions(
                guild.get_role(guild.id),
                send_messages=False,
                read_messages=False,
                view_channel=False,
            )

            for role_id in data["valid_roles"]:
                role = guild.get_role(role_id)

                await ticket_channel.set_permissions(
                    role,
                    send_messages=True,
                    read_messages=True,
                    add_reactions=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    external_emojis=True,
                )

            await ticket_channel.set_permissions(
                member,
                send_messages=True,
                read_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                external_emojis=True,
            )

            em = discord.Embed(
                title="New ticket from {}#{}".format(member.name, member.discriminator),
                description="{}".format("Pls wait while you reach you"),
                color=0x00A8FF,
            )

            await ticket_channel.send(embed=em, content=f"{member.mention}")
            await ticket_channel.send(
                "To close the ticket, type `[p]close`\nTo save the ticket transcript, type `[p]save`"
            )
            pinged_msg_content = ""
            non_mentionable_roles = []
            if data["pinged_roles"]:
                for role_id in data["pinged_roles"]:
                    role = guild.get_role(role_id)
                    pinged_msg_content += role.mention
                    pinged_msg_content += " "
                    if role.mentionable:
                        pass
                    else:
                        await role.edit(mentionable=True)
                        non_mentionable_roles.append(role)
                await ticket_channel.send(pinged_msg_content)
                for role in non_mentionable_roles:
                    await role.edit(mentionable=False)

            ticket_channel_ids = data["ticket_channel_ids"]
            ticket_channel_ids.append(ticket_channel.id)
            post = {
                "ticket_counter": ticket_number,
                "ticket_channel_ids": ticket_channel_ids,
            }
            await ticket_update(guild.id, post)

            log_channel = guild.get_channel(data["log"])
            await self.log(
                guild,
                log_channel,
                f"Channel: **#ticket-{ticket_number}**\n**Opened by:** {member} ({member.id})",
                "RUNNING",
            )


def setup(bot):
    bot.add_cog(TicketReaction(bot))
