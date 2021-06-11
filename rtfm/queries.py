from os import system as sys
from datetime import datetime
import json
sys('pip install lxml')

from pygicord import Paginator
from yaml import safe_load as yaml_load
languages = '''
05ab1e
1l-a
1l-aoi
2dfuck
2l
2sable
3var
4
7
99
a-gram
a-pear-tree
abc
abc-assembler
accbb
aceto
actually
ada-gnat
adapt
addpp
adjust
agda
agony
ahead
aheui
alchemist
algol68g
alice
alice-bob
aliceml
alphabeta
alphuck
alumin
amnesiac-from-minsk
ante
anyfix
apl-dyalog
apl-dyalog-classic
apl-dyalog-extended
apl-dzaima
apl-ngn
appleseed
arble
archway
archway2
arcyou
arnoldc
asciidots
asperix
assembly-as
assembly-fasm
assembly-gcc
assembly-jwasm
assembly-nasm
ats2
attache
aubergine
awk
axo
backhand
bash
bc
bctbww
beam
bean
beanshell
beatnik
beeswax
befunge
befunge-93-fbbi
befunge-93-mtfi
befunge-93-pyfunge
befunge-96-mtfi
befunge-97-mtfi
befunge-98
befunge-98-pyfunge
bit
bitbitjump
bitch
bitchanger
bitcycle
bitwise
blak
blc
boo
boolfuck
bosh
brachylog
brachylog2
bracmat
braille
brain-flak
brainbash
brainbool
brainflump
brainfuck
braingolf
brainhack
brat
brian-chuck
broccoli
bubblegum
burlesque
buzzfizz
bwfuckery
c-clang
c-gcc
c-tcc
cakeml
calc2
canvas
cardinal
carol-dave
carrot
catholicon
cauliflower
ceres
ceylon
chain
changeling
chapel
charcoal
charm
check
checkedc
cheddar
chef
chip
cil-mono
cinnamon-gum
cixl
cjam
clam
clean
clips
clisp
clojure
cobol-gnu
cobra
coconut
coffeescript
coffeescript2
commata
commentator
commercial
condit
convex
cood
corea
cow
cpp-clang
cpp-gcc
cpy
cquents
crayon
cryptol
crystal
cs-core
cs-csc
cs-csi
cs-mono
cs-mono-shell
csl
cubically
cubix
curry-pakcs
curry-sloth
cy
d
d2
dafny
dart
dash
dc
deadfish-
decimal
delimit
deorst
detour
dg
dirty
dobela
dodos
dreaderef
dscript
dstack
dyvil
eacal
ec
ecndpcaalrlp
ecpp-c
ecpp-cpp
ed
egel
element
elf
elixir
elvm-ir
emacs-lisp
emmental
emoji
emoji-gramming
emojicode
emojicode6
emojicoder
emotifuck
emotinomicon
empty-nest
enlist
erlang-escript
es
esopunk
eta
euphoria3
euphoria4
evil
explode
extrac
face
factor
false
fantom
farnsworth
felix
fernando
feu
fimpp
fish
fish-shell
fission
fission2
flipbit
flobnar
foam
focal
foo
forked
forte
forth-gforth
fortran-gfortran
fourier
fractran
fs-core
fs-mono
fueue
funciton
functoid
funky
funky2
fynyl
gaia
gaotpp
gap
gema
geo
glypho
glypho-shorthand
gnuplot
go
golfish
golfscript
granule
grass
grime
groovy
gs2
gwion
hades
haskell
haskell-gofer
haskell-hugs
haskell-literate
hasm
haxe
haystack
hbcht
hdbf
hexagony
hobbes
hodor
homespring
hspal
huginn
husk
hy
i
icon
idris
incident
ink
intercal
io
j
j-uby
jael
japt
java-jdk
java-openjdk
javascript-babel-node
javascript-node
javascript-spidermonkey
javascript-v8
jelly
jellyfish
joy
jq
julia
julia1x
julia5
julia6
julia7
jx
k-kona
k-ngn
k-ok
kavod
klein
koberi-c
koka
kotlin
krrp
ksh
l33t
labyrinth
lean
lily
llvm
lmbm
lnusp
locksmith
logicode
lolcode
lost
lower
lua
ly
m
m4
machinecode
make
malbolge
mamba
mariolang
mascarpone
mathematica
mathgolf
mathics
matl
maverick
maxima
maybelater
memory-gap
milambda
milky-way
minimal-2d
miniml
minkolang
mirror
momema
monkeys
moonscript
moorhens
mornington-crescent
mouse
mouse2002
mouse83
mu6
mumps
muriel
my
my-basic
nameless
neim
neutrino
nhohnhehr
nial
nim
no
noether
nqt
ntfjc
numberwang
oasis
obcode
object-pascal-fpc
objective-c-clang
objective-c-gcc
ocaml
occam-pi
octave
ohm
ohm2
oml
ooocode
ork
orst
osabie
osh
pain-flak
paradoc
parenthesis-hell
parenthetic
pari-gp
pascal-fpc
path
pbrain
perl4
perl5
perl5-cperl
perl6
phoenix
phooey
php
physica
picolisp
piet
pike
pilot-pspilot
pilot-rpilot
pingpong
pip
pixiedust
pl
pony
positron
postl
postscript-xpost
powershell
powershell-core
prelude
premier
preproc
prolog-ciao
prolog-swi
proton
proton2
ps-core
pure
purescript
purple
pushy
puzzlang
pyke
pylons
pyn-tree
pyon
pyramid-scheme
pyt
pyth
python1
python2
python2-cython
python2-iron
python2-jython
python2-pypy
python3
python3-cython
python3-pypy
python3-stackless
python38pr
qqq
qs-core
quadr
quadrefunge-97-mtfi
quads
quarterstaff
quintefunge-97-mtfi
r
racket
rad
rail
random-brainfuck
rapira
re-direction
reason
rebol
recursiva
red
reng
reregex
resplicate
reticular
retina
retina1
return
rexx
ring
rk
rockstar
roda
roop
ropy
rotor
rprogn
rprogn-2
ruby
runic
rust
rutger
sad-flak
sakura
sbf
scala
scheme-chez
scheme-chicken
scheme-gambit
scheme-guile
sed
sed-gnu
seed
septefunge-97-mtfi
seriously
sesos
set
sexefunge-97-mtfi
sfk
shapescript
shnap
shortc
shove
shp
shtriped
sidef
silberjoder
silos
simplefunge
simplestack
simula
sisal
sisi
slashes
smbf
sml-mlton
smol
snails
snobol4
snowman
snusp
snusp-bloated
snuspi
somme
spaced
spim
spl
spoon
sqlite
squirrel
stackcats
stacked
starfish
starry
stax
stencil
stones
str
straw
subskin
sumerian
surface
swap
swift4
symbolic-python
syms
taco
tampio
tampioi
tamsin
tapebagel
taxi
tcl
tcsh
templat
templates
thing
threead
thue
thutu
tidy
tincan
tinybf
tinylisp
tir
tis
tmbww
transcript
trefunge-97-mtfi
trefunge-98-pyfunge
triangular
triangularity
trigger
triple-threat
trumpscript
turtled
typescript
ubasic
underload
unefunge-97-mtfi
unefunge-98-pyfunge
unicat
unlambda
uno
unreadable
v
v-fmota
vala
var
vb-core
verbosity
visual-basic-net-mono
visual-basic-net-vbc
vitsy
vsl
wasm
waterfall
whirl
whispers
whispers2
whitespace
width
wierd
wise
woefully
wren
wsf
wumpus
wyalhein
xeec
xeraph
yaball
yabasic
yash
ybc
yup
z80golf
zephyr
zig
zkl
zoidberg
zsh
'''

import asyncio
import os
import re
import sys
import urllib.parse
from io import BytesIO
from hashlib import algorithms_available as algorithms

import aiohttp
import discord, requests 
from discord import Embed
import textwrap
# from pytio import Tio, TioRequest
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from discord.utils import escape_mentions
import hashlib 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import _ref, _doc
from _used import typing, get_raw, paste
#from _tio import Tio, TioRequest
from _tio import Tio

class Coding(commands.Cog, name="RTFM Bot"):
		"""To test code and check docs"""

		def __init__(self, bot):
				self.bot = bot
				self.algos = sorted([h for h in hashlib.algorithms_available if h.islower()])
				
				self.bot.languages = ()
		def get_content(self, tag):
				"""Returns content between two h2 tags"""

				bssiblings = tag.next_siblings
				siblings = []
				for elem in bssiblings:
						# get only tag elements, before the next h2
						# Putting away the comments, we know there's
						# at least one after it.
						if type(elem) == NavigableString:
								continue
						# It's a tag
						if elem.name == 'h2':
								break
						siblings.append(elem.text)
				content = '\n'.join(siblings)
				if len(content) >= 1024:
						content = content[:1021] + '...'

				return content

		wrapping = {
				'c': '#include <stdio.h>\nint main() {code}',
				'cpp': '#include <iostream>\nint main() {code}',
				'cs': 'using System;class Program {static void Main(string[] args) {code}}',
				'java': 'public class Main {public static void main(String[] args) {code}}',
				'rust': 'fn main() {code}',
				'd': 'import std.stdio; void main(){code}',
				'kotlin': 'fun main(args: Array<String>) {code}'
		}

		referred = {
				"csp-directives": _ref.csp_directives,
				"git": _ref.git_ref,
				"git-guides": _ref.git_tutorial_ref,
				"haskell": _ref.haskell_ref,
				"html5": _ref.html_ref,
				"http-headers": _ref.http_headers,
				"http-methods": _ref.http_methods,
				"http-status-codes": _ref.http_status,
				"sql": _ref.sql_ref
		}

		# TODO: lua, java, javascript, asm
		documented = {
				'c': _doc.c_doc,
				'cpp': _doc.cpp_doc,
				'haskell': _doc.haskell_doc,
				'python': _doc.python_doc
		}

		@commands.command(help='''run <language> [--wrapped] [--stats] <code> for command-line-options, compiler-flags and arguments you may add a line starting with this argument, and after a space add your options, flags or args. Stats option displays more informations on execution consumption wrapped allows you to not put main function in some languages, which you can see in `list wrapped argument` <code> may be normal code, but also an attached file, or a link from [hastebin](https://hastebin.com) or [Github gist](https://gist.github.com) If you use a link, your command must end with this syntax: `link=<link>` (no space around `=`)''', brief='Execute code in a given programming language')
		async def run(self, ctx, language, *, code=''):
				"""Execute code in a given programming language"""
				# Powered by tio.run
				with open('default_langs.yml', 'r') as file: default = yaml_load(file)
				options = {
						'--stats': False,
						'--wrapped': False
				}

				lang = language.strip('`').lower()

				optionsAmount = len(options)

				# Setting options and removing them from the beginning of the command
				# options may be separated by any single whitespace, which we keep in the list
				code = re.split(r'(\s)', code, maxsplit=optionsAmount)

				for option in options:
						if option in code[:optionsAmount*2]:
								options[option] = True
								i = code.index(option)
								code.pop(i)
								code.pop(i) # remove following whitespace character

				code = ''.join(code)

				compilerFlags = []
				commandLineOptions = []
				args = []
				inputs = []

				lines = code.split('\n')
				code = []
				for line in lines:
						if line.startswith('input '):
								inputs.append(' '.join(line.split(' ')[1:]).strip('`'))
						elif line.startswith('compiler-flags '):
								compilerFlags.extend(line[15:].strip('`').split(' '))
						elif line.startswith('command-line-options '):
								commandLineOptions.extend(line[21:].strip('`').split(' '))
						elif line.startswith('arguments '):
								args.extend(line[10:].strip('`').split(' '))
						else:
								code.append(line)

				inputs = '\n'.join(inputs)

				code = '\n'.join(code)

				text = None

				async with ctx.typing():
						if ctx.message.attachments:
								# Code in file
								file = ctx.message.attachments[0]
								if file.size > 20000:
										return await ctx.send("File must be smaller than 20 kio.")
								buffer = BytesIO()
								await ctx.message.attachments[0].save(buffer)
								text = buffer.read().decode('utf-8')
						elif code.split(' ')[-1].startswith('link='):
								# Code in a webpage
								base_url = urllib.parse.quote_plus(code.split(' ')[-1][5:].strip('/'), safe=';/?:@&=$,><-[]')

								url = get_raw(base_url)

								async with aiohttp.ClientSession() as client_session:
										async with client_session.get(url) as response:
												if response.status == 404:
														return await ctx.send('Nothing found. Check your link')
												elif response.status != 200:
														return await ctx.send(f'An error occurred (status code: {response.status}). Retry later.')
												text = await response.text()
												if len(text) > 20000:
														return await ctx.send('Code must be shorter than 20,000 characters.')
						elif code.strip('`'):
								# Code in message
								text = code.strip('`')
								firstLine = text.splitlines()[0]
								if re.fullmatch(r'( |[0-9A-z]*)\b', firstLine):
										text = text[len(firstLine)+1:]

						if text is None:
								# Ensures code isn't empty after removing options
								raise commands.MissingRequiredArgument(ctx.command.clean_params['code'])

						# common identifiers, also used in highlight.js and thus discord codeblocks
						quickmap = {
								'asm': 'assembly',
								'c#': 'cs',
								'c++': 'cpp',
								'csharp': 'cs',
								'f#': 'fs',
								'fsharp': 'fs',
								'js': 'javascript',
								'nimrod': 'nim',
								'py': 'python',
								'q#': 'qs',
								'rs': 'rust',
								'sh': 'bash',
						}

						if lang in quickmap:
								lang = quickmap[lang]

						if lang in default:
								lang = default[lang]
						if not lang in languages:#self.bot.languages:
								matches = '\n'.join([language for language in languages if lang in language][:10])
								lang = escape_mentions(lang)
								message = f"`{lang}` not available."
								if matches:
										message = message + f" Did you mean:\n{matches}"

								return await ctx.send(message)

						if options['--wrapped']:
								if not (any(map(lambda x: lang.split('-')[0] == x, self.wrapping))) or lang in ('cs-mono-shell', 'cs-csi'):
										return await ctx.send(f'`{lang}` cannot be wrapped')

								for beginning in self.wrapping:
										if lang.split('-')[0] == beginning:
												text = self.wrapping[beginning].replace('code', text)
												break

						tio = Tio(lang, text, compilerFlags=compilerFlags, inputs=inputs, commandLineOptions=commandLineOptions, args=args)

						result = await tio.send()

						if not options['--stats']:
								try:
										start = result.rindex("Real time: ")
										end = result.rindex("%\nExit code: ")
										result = result[:start] + result[end+2:]
								except ValueError:
										# Too much output removes this markers
										pass

						if len(result) > 1991 or result.count('\n') > 40:
								# If it exceeds 2000 characters (Discord longest message), counting ` and ph\n characters
								# Or if it floods with more than 40 lines
								# Create a hastebin and send it back
								link = await paste(result)

								if link is None:
										return await ctx.send("Your output was too long, but I couldn't make an online bin out of it")
								return await ctx.send(f'Output was too long (more than 2000 characters or 40 lines) so I put it here: {link}')

						zero = '\N{zero width space}'
						result = re.sub('```', f'{zero}`{zero}`{zero}`{zero}', result)

						# ph, as placeholder, prevents Discord from taking the first line
						# as a language identifier for markdown and remove it
						returned = await ctx.send(f'```ph\n{result}```')

				await returned.add_reaction('🗑')
				returnedID = returned.id

				def check(reaction, user):
						return user == ctx.author and str(reaction.emoji) == '🗑' and reaction.message.id == returnedID

				try:
						await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
				except asyncio.TimeoutError:
						pass
				else:
						await returned.delete()

		@commands.bot_has_permissions(embed_links=True)
		@commands.command(aliases=['ref'])
		@typing
		async def reference(self, ctx, language, *, query: str):
				"""Returns element reference from given language"""

				lang = language.strip('`')

				if not lang.lower() in self.referred:
						return await ctx.send(f"{lang} not available. See `[p]list references` for available ones.")
				await self.referred[lang.lower()](ctx, query.strip('`'))

		@commands.command(aliases=['doc'])
		@commands.bot_has_permissions(embed_links=True)
		@typing
		async def documentation(self, ctx, language, *, query: str):
				"""Returns element reference from given language"""

				lang = language.strip('`')

				if not lang.lower() in self.documented:
						return await ctx.send(f"{lang} not available. See `[p]list documentations` for available ones.")
				await self.documented[lang.lower()](ctx, query.strip('`'))
				
		@commands.command()
		@commands.bot_has_permissions(embed_links=True)
		@typing
		async def man(self, ctx, *, page: str):
				"""Returns the manual's page for a (mostly Debian) linux command"""

				base_url = f'https://man.cx/{page}'
				url = urllib.parse.quote_plus(base_url, safe=';/?:@&=$,><-[]')

				async with aiohttp.ClientSession() as client_session:
						async with client_session.get(url) as response:
								if response.status != 200:
										return await ctx.send('An error occurred (status code: {response.status}). Retry later.')

								soup = BeautifulSoup(await response.text(), 'lxml')

								nameTag = soup.find('h2', string='NAME\n')

								if not nameTag:
										# No NAME, no page
										return await ctx.send(f'No manual entry for `{page}`. (Debian)')

								# Get the two (or less) first parts from the nav aside
								# The first one is NAME, we already have it in nameTag
								contents = soup.find_all('nav', limit=2)[1].find_all('li', limit=3)[1:]

								if contents[-1].string == 'COMMENTS':
										contents.remove(-1)

								title = self.get_content(nameTag)

								emb = discord.Embed(title=title, url=f'https://man.cx/{page}')
								emb.set_author(name='Debian Linux man pages')
								emb.set_thumbnail(url='https://www.debian.org/logos/openlogo-nd-100.png')

								for tag in contents:
										h2 = tuple(soup.find(attrs={'name': tuple(tag.children)[0].get('href')[1:]}).parents)[0]
										emb.add_field(name=tag.string, value=self.get_content(h2))

								await ctx.send(embed=emb)


		@commands.command()
		@commands.bot_has_permissions(embed_links=True)
		async def list(self, ctx, *, group=None):
				"""Lists available choices for other commands"""

				choices = {
						"documentations": self.documented,
						"hashing": sorted([h for h in algorithms if h.islower()]),
						"references": self.referred,
						"wrapped argument": self.wrapping,
				}

				if group == 'languages':
						emb = discord.Embed(title=f"Available for {group}:",
								description='View them on [tio.run](https://tio.run/#), or in [JSON format](https://tio.run/languages.json)')
						return await ctx.send(embed=emb)

				if not group in choices:
						emb = discord.Embed(title="Available listed commands", description=f"`languages`, `{'`, `'.join(choices)}`")
						return await ctx.send(embed=emb)

				availables = choices[group]
				description=f"`{'`, `'.join([*availables])}`"
				emb = discord.Embed(title=f"Available for {group}: {len(availables)}", description=description)
				await ctx.send(embed=emb)
		

		@commands.command()
		@commands.bot_has_permissions(embed_links=True)
		async def rtfm(self, ctx):
			url = 'https://github.com/FrenchMasterSword/RTFMbot'
			embed = discord.Embed(title="RTFM Bot", description=f"RTFM is a discord bot created to help you as a programmer directly from Discord. It provides some helpful tools:\n    - Languages documentations and references\n    - Code execution\n\nNote: This is a part of Program fetched from RTFM Bot. All credits goes to rightful developer. Consider giving them a star on their Github repo. {url}", timestamp=datetime.utcnow())
			embed.set_footer(text="RTFM Bot", icon_url="https://github.com/FrenchMasterSword/RTFMbot/blob/master/icon.png?raw=true")
			embed.set_thumbnail(url="https://github.com/FrenchMasterSword/RTFMbot/blob/master/icon.png?raw=true")
			embed.add_field(name="run", value="[p]run <lang> <code>", inline=False)
			embed.add_field(name="doc", value="[p]doc <lang> <query>", inline=False)
			embed.add_field(name="ref", value="[p]ref <lang> <query>", inline=False)
			await ctx.send(embed=embed)


		@commands.command()
		@commands.bot_has_permissions(embed_links=True)
		async def ascii(self, ctx, *, text: str):
				"""Returns number representation of characters in text"""

				emb = discord.Embed(title="Unicode convert", description=' '.join([str(ord(letter)) for letter in text]))
				emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')
				await ctx.send(embed=emb)

		
		@commands.bot_has_permissions(embed_links=True)
		@commands.command()
		async def unascii(self, ctx, *, text: str):
				"""Reforms string from char codes"""

				try:
						codes = [chr(int(i)) for i in text.split(' ')]
						emb = discord.Embed(title="Unicode convert",
								description=''.join(codes))
						emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')
						await ctx.send(embed=emb)
				except ValueError as e:
						await ctx.send("Invalid sequence. Example usage : `[p]unascii 104 101 121`")
		

		@commands.bot_has_permissions(embed_links=True)
		@commands.command()
		async def byteconvert(self, ctx, value: int, unit='Mio'):
				"""Shows byte conversions of given value"""

				units = ('o', 'Kio', 'Mio', 'Gio', 'Tio', 'Pio', 'Eio', 'Zio', 'Yio')
				unit = unit.capitalize()

				if not unit in units and unit != 'O':
						return await ctx.send(f"Available units are `{'`, `'.join(units)}`.")

				emb = discord.Embed(title="Binary conversions")
				index = units.index(unit)

				for i,u in enumerate(units):
						result = round(value / 2**((i-index)*10), 14)
						emb.add_field(name=u, value=result)

				await ctx.send(embed=emb)
		

		@commands.bot_has_permissions(embed_links=True)
		@commands.command(name='hash')
		async def _hash(self, ctx, algorithm, *, text: str):
				"""
				Hashes text with a given algorithm
				UTF-8, returns under hexadecimal form
				"""

				algo = algorithm.lower()

				if not algo in self.algos:
						matches = '\n'.join([supported for supported in self.algos if algo in supported][:10])
						message = f"`{algorithm}` not available."
						if matches:
								message += f" Did you mean:\n{matches}"
						return await ctx.send(message)

				try:
						# Guaranteed one
						hash_object = getattr(hashlib, algo)(text.encode('utf-8'))
				except AttributeError:
						# Available
						hash_object = hashlib.new(algo, text.encode('utf-8'))

				emb = discord.Embed(title=f"{algorithm} hash",
														description=hash_object.hexdigest())
				emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')

				await ctx.send(embed=emb)



		@commands.command(aliases=['requestsget', 'rget', 'requestsg', 'rg'])
		@commands.bot_has_permissions(embed_links=True)
		async def reqget(self, ctx, url:str, extra:int=0):
			"""Get Request Tool for developers. [p]reqget [url] [1/0]"""
			req = requests.get(url, params=None)

			status_code = req.status_code
			content = req.text

			embed_contents_list = textwrap.wrap(content, 1000)

			embeds = []
			if extra == 0:
				for temp in range(1, (len(embed_contents_list)+1)):
					embeds.append(Embed(title=f"Response: {status_code} | URL: {url}", description=f"**Content**```\n{embed_contents_list[temp-1]}```",  timestamp=datetime.utcnow()))
			elif extra == 1:
				for temp in range(1, (len(embed_contents_list)+1)):
					embeds.append(Embed(title=f"Response: {status_code} | URL: {url}", description=f"**Content**```\n{embed_contents_list[temp-1]}```",  timestamp=datetime.utcnow()).add_field(name="Headers", value=f"```\n{req.headers}```", inline=False).add_field(name="Encoding", value=f"```\n{req.encoding}```", inline=False).add_field(name="Cookies", value=f"```\n{req.cookies}```"))
				

			paginator = Paginator(pages=embeds)
			await paginator.run(ctx)
		

		@commands.command(aliases=['requestspost', 'rpost', 'requestsp', 'rp'])
		@commands.bot_has_permissions(embed_links=True)
		async def reqpost(self, ctx, url:str, data:str=None):
			"""Post Request Tool for developers. [p]reqpost [url] [data:json]"""
			if data is not None:
				try: 
					data = json.loads(data)
					req = requests.post(url, json=data)
				except: 
					req = requests.post(url, json=None)

			if not 200 <= req.status_code >= 300: return await ctx.send(f"Failed to post ``{json}`` at ``{url}``. Status code ``{req.status_code}``. Please check the credentials again.")
			
			content = req.text
			status_code = req.status_code 
			embed_contents_list = textwrap.wrap(content, 1000)

			embeds = []

			for temp in range(1, (len(embed_contents_list)+1)):
				embeds.append(Embed(title=f"Response: {status_code} | URL: {url}", description=f"**Content**```\n{embed_contents_list[temp-1]}```",  timestamp=datetime.utcnow()))
			paginator = Paginator(pages=embeds)
			await paginator.run(ctx)
		

def setup(bot):
		bot.add_cog(Coding(bot))
