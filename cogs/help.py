import discord
from discord.ext import commands

from utilities.paginator import Paginator
from utilities.config import SUPPORT_SERVER, INVITE, DEV_LOGO

from core.cog import Cog
from core.bot import Parrot


class HelpCommand(commands.HelpCommand):
				def __init__(self):
								super().__init__(
												command_attrs={
																'cooldown': commands.Cooldown(1, 3.0,	commands.BucketType.member),
																'help': 'Shows help about the bot, a command, or a category'
												})

				async def on_help_command_error(self, ctx, error):
								if isinstance(error, commands.CommandInvokeError):
												await ctx.send(str(error.original))

				def get_command_signature(self, command):
								return f'[p]{command.name}{"|" if command.aliases else ""}{"|".join(command.aliases if command.aliases else "")} {command.signature}'

				def common_command_formatting(self, embed_like, command):
								embed_like.title = f"Help with command `{command.name}`"

								embed_like.description = f"```\n{command.help if command.help else 'Help not available... :('}\n```"
								embed_like.add_field(
												name="Usage",
												value=f"```\n{self.get_command_signature(command)}\n```")
								embed_like.add_field(
												name="Aliases",
												value=
												f"```\n{', '.join(command.aliases if command.aliases else '')}\n```"
								)

				async def send_command_help(self, command):
								embed = discord.Embed(colour=discord.Colour(0x55ddff))
								self.common_command_formatting(embed, command)
								await self.context.send(embed=embed)

				async def send_bot_help(self, mapping):
								bot = self.context.bot

								em_list = []

								get_bot = f"[Add me to your server]({INVITE})"
								support_server = f"[Support Server]({SUPPORT_SERVER})"

								embed = discord.Embed(description=f"```\nPrefixes are '{self.context.prefix}' and '@Parrot#9209'\n```", color=discord.Colour(0x55ddff))
								embed.set_author(name=f"Server: {self.context.guild.name or self.context.author.name}", icon_url=self.context.guild.icon_url or self.context.me.icon_url)

								embed.add_field(name="Get Parrot", value=f"• {get_bot}\n• {support_server}", inline=False)
								embed.set_footer(text="Built with ❤️ and `discord.py`", icon_url=f"{DEV_LOGO}")

								em_list.append(embed)

								for cog in bot.cogs:
												if bot.cogs[cog].get_commands():

																em = discord.Embed(
																				description=
																				f"```\n{bot.cogs[cog].description if bot.cogs[cog].description else 'No help available :('}\n```\n"
																				f"**Commands**```\n{', '.join([cmd.name for cmd in bot.cogs[cog].get_commands()])}\n```",
																				color=discord.Colour(0x55ddff))
																em.set_author(name=f"COG: {cog}")
																em.set_footer(text="Built with ❤️ and `discord.py`",
																														icon_url=f"{DEV_LOGO}")
																em_list.append(em)
												else: 
																pass

								paginator = Paginator(pages=em_list)
								await paginator.start(self.context)

				async def send_group_help(self, group):
						
						em_list = []
						cmds = await self.filter_commands(group.commands, sort=True)

						e = discord.Embed(color=discord.Colour(0x55ddff), description=f"Sub commands\n```\n{', '.join([cmd.name for cmd in cmds])}\n```")
						e.title = f"Help with group **{group.name}{'|'.join(group.aliases) if group.aliases else ''}**"
						e.set_footer(text="Built with ❤️ and `discord.py`", icon_url=f"{DEV_LOGO}")
						
						em_list.append(e)
						
						for cmd in cmds:
								e = discord.Embed(title=cmd.name, 
																	description=f"```{cmd.description if cmd.description else 'No description.'}```\n"
																							f"Usage: {self.get_command_signature(cmd)}", 
																	color=discord.Colour(0x55ddff))
								em_list.append(e)

						paginator = Paginator(pages=em_list)
						await paginator.start(self.context)

				async def send_cog_help(self, cog):

								em_list = []

								embed = discord.Embed(
												title=f'{str(cog.qualified_name).capitalize()} Commands',
												description=
												f"```\n{cog.description if cog.description else 'NA'}\n```",
												color=discord.Colour(0x55ddff))
								embed.set_footer(text="Built with ❤️ and `discord.py`", icon_url=f"{DEV_LOGO}")
								em_list.append(embed)

								for cmd in cog.get_commands():
									if cog.get_commands():
										em = discord.Embed(title=f"Help with {cmd.name}",
																			description=f"```\n{cmd.help}\n```",
																			color=discord.Colour(0x55ddff))
										em.add_field(name=f"Usage",
																value=f"```\n{self.get_command_signature(cmd)}\n```")
										em.add_field(
														name="Aliases",
														value=
														f"```\n{', '.join(cmd.aliases if cmd.aliases else 'NA')}\n```")

										em_list.append(em)
									else: pass

								paginator = Paginator(pages=em_list)
								await paginator.start(self.context)


class Meta(Cog):
				def __init__(self, bot: Parrot):
								self.bot = bot
								self.old_help_command = bot.help_command
								bot.help_command = HelpCommand()
								bot.help_command.cog = self

				def cog_unload(self):
								self.bot.help_command = self.old_help_command


def setup(bot):
				bot.add_cog(Meta(bot))
