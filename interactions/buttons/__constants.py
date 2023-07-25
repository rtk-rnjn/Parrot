from __future__ import annotations

from string import ascii_uppercase
from typing import Optional, Union

from PIL import Image

import discord

REGIONAL_INDICATOR_EMOJI = (
    "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Z}",
)

AN_EMOJI = "<:regional_indicator_an:929993092390596609>"
ER_EMOJI = "<:regional_indicator_er:929994016471261224>"
HE_EMOJI = "<:regional_indicator_he:929994202572554240>"
IN_EMOJI = "<:regional_indicator_in:929994734372536361>"
QU_EMOJI = "<:regional_indicator_qu:929994922923274260>"
TH_EMOJI = "<:regional_indicator_th:929995052153970789>"


LETTERS_EMOJI = {
    **{
        "#": "\N{BLACK SQUARE FOR STOP}\ufe0f",
        "1": AN_EMOJI,
        "2": ER_EMOJI,
        "3": HE_EMOJI,
        "4": IN_EMOJI,
        "5": QU_EMOJI,
        "6": TH_EMOJI,
    },
    **dict(zip(ascii_uppercase, REGIONAL_INDICATOR_EMOJI, strict=True)),
}

SMALL = 3
ORIGINAL = 4
BIG = 5
SUPER_BIG = 6

DIE = {
    SMALL: [
        "ATSWKA",
        "ZHIWIR",
        "WYASAY",
        "NELTDL",
        "UJNIIQ",
        "ORQPII",
        "PCOAUB",
        "TKRTAU",
        "ZAQLPG",
    ],
    ORIGINAL: [
        "RIFOBX",
        "IFEHEY",
        "DENOWS",
        "UTOKND",
        "HMSRAO",
        "LUPETS",
        "ACITOA",
        "YLGKUE",
        "5BMJOA",
        "EHISPN",
        "VETIGN",
        "BALIYT",
        "EZAVND",
        "RALESC",
        "UWILRG",
        "PACEMD",
    ],
    BIG: [
        "5BZJXK",
        "TOUOTO",
        "OVWGR",
        "AAAFSR",
        "AUMEEG",
        "HHLRDO",
        "MJDTHO",
        "LHNROD",
        "AFAISR",
        "YIFASR",
        "TELPCI",
        "SSNSEU",
        "RIYPRH",
        "DORDLN",
        "CCWNST",
        "TTOTEM",
        "SCTIEP",
        "EANDNN",
        "MNNEAG",
        "UOTOWN",
        "AEAEEE",
        "YIFPSR",
        "EEEEMA",
        "ITITIE",
        "ETILIC",
    ],
    SUPER_BIG: [
        "AAAFRS",
        "AAEEEE",
        "AAEEOO",
        "AAFIRS",
        "ABDEIO",
        "ADENNN",
        "AEEEEM",
        "AEEGMU",
        "AEGMNN",
        "AEILMN",
        "AEINOU",
        "AFIRSY",
        "123456",
        "BBJKXZ",
        "CCENST",
        "CDDLNN",
        "CEIITT",
        "CEIPST",
        "CFGNUY",
        "DDHNOT",
        "DHHLOR",
        "DHHNOW",
        "DHLNOR",
        "EHILRS",
        "EIILST",
        "EILPST",
        "EIO###",
        "EMTTTO",
        "ENSSSU",
        "GORRVW",
        "HIRSTV",
        "HOPRST",
        "IPRSYY",
        "JK5WXZ",
        "NOOTUW",
        "OOOTTU",
    ],
}

__1 = {3: 1, 4: 1, 5: 2, 6: 3, 7: 5}
__2 = {x: 11 for x in range(8, SUPER_BIG**2)}
POINTS = __1 | __2

_2048_GAME = a = {
    "0": "<:YELLO:922889092755259405>",
    "2": "<:2_:922741083983724544>",
    "8": "<:8_:922741084004687913>",
    "2048": "<:2048:922741084612861992>",
    "256": "<:256:922741084671602740>",
    "32": "<:32:922741084700966963>",
    "4": "<:4_:922741084738699314>",
    "1024": "<:1024:922741085007130624>",
    "16": "<:16:922741085464297472>",
    "64": "<:64:922741085539827772>",
    "128": "<:128:922741085866958868>",
    "4096": "<:4096:922741086009565204>",
    "512": "<:512:922741086017978368>",
}


class Emojis:
    cross_mark = "\u274C"
    star = "\u2B50"
    christmas_tree = "\U0001F384"
    check = "\u2611"
    envelope = "\U0001F4E8"

    ok_hand = ":ok_hand:"
    hand_raised = "\U0001F64B"

    number_emojis = {
        1: "\u0031\ufe0f\u20e3",
        2: "\u0032\ufe0f\u20e3",
        3: "\u0033\ufe0f\u20e3",
        4: "\u0034\ufe0f\u20e3",
        5: "\u0035\ufe0f\u20e3",
        6: "\u0036\ufe0f\u20e3",
        7: "\u0037\ufe0f\u20e3",
        8: "\u0038\ufe0f\u20e3",
        9: "\u0039\ufe0f\u20e3",
    }

    confirmation = "\u2705"
    decline = "\u274c"
    incident_unactioned = "\N{NEGATIVE SQUARED CROSS MARK}"

    x = "\U0001f1fd"
    o = "\U0001f1f4"


STATES = (
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
)

NUMBERS = list(Emojis.number_emojis.values())
CROSS_EMOJI = Emojis.incident_unactioned

Coordinate = Optional[tuple[int, int]]
EMOJI_CHECK = Union[discord.Emoji, discord.PartialEmoji, str]

CHOICES = ["rock", "paper", "scissors"]
SHORT_CHOICES = ["r", "p", "s"]

# Using a dictionary instead of conditions to check for the winner.
WINNER_DICT = {
    "r": {
        "r": 0,
        "p": -1,
        "s": 1,
    },
    "p": {
        "r": 1,
        "p": 0,
        "s": -1,
    },
    "s": {
        "r": -1,
        "p": 1,
        "s": 0,
    },
}

# This is for the opposing player's board which only shows aimed locations.
HIDDEN_EMOJIS = {
    (True, True): ":red_circle:",
    (True, False): ":black_circle:",
    (False, True): ":white_circle:",
    (False, False): ":black_circle:",
}

# For the top row of the board
LETTERS = (
    ":stop_button::regional_indicator_a::regional_indicator_b::regional_indicator_c::regional_indicator_d:"
    ":regional_indicator_e::regional_indicator_f::regional_indicator_g::regional_indicator_h:"
    ":regional_indicator_i::regional_indicator_j:"
)

# For the first column of the board
NUMBERS = [
    ":one:",
    ":two:",
    ":three:",
    ":four:",
    ":five:",
    ":six:",
    ":seven:",
    ":eight:",
    ":nine:",
    ":keycap_ten:",
]

CROSS_EMOJI = "\u274e"
HAND_RAISED_EMOJI = "\U0001f64b"

BoardState = list[list[bool | None]]

DIAGRAPHS = {"1": "AN", "2": "ER", "3": "HE", "4": "IN", "5": "QU", "6": "TH"}


EmojiSet = dict[tuple[bool, bool], str]

grass = Image.open("extra/minecraft/grass64x.png").convert("RGBA")
water = Image.open("extra/minecraft/water64x.png").convert("RGBA")
sand = Image.open("extra/minecraft/sand64x.png").convert("RGBA")
stone = Image.open("extra/minecraft/stone64x.png").convert("RGBA")
plank = Image.open("extra/minecraft/plank64x.png").convert("RGBA")
glass = Image.open("extra/minecraft/glass64x.png").convert("RGBA")
red = Image.open("extra/minecraft/red64x.png").convert("RGBA")
iron = Image.open("extra/minecraft/iron64x.png").convert("RGBA")
brick = Image.open("extra/minecraft/brick64x.png").convert("RGBA")
gold = Image.open("extra/minecraft/gold64x.png").convert("RGBA")
pur = Image.open("extra/minecraft/pur64x.png").convert("RGBA")
leaf = Image.open("extra/minecraft/leaf64x.png").convert("RGBA")
log = Image.open("extra/minecraft/log64x.png").convert("RGBA")
coal = Image.open("extra/minecraft/coal64x.png").convert("RGBA")
dia = Image.open("extra/minecraft/diamond64x.png").convert("RGBA")
lava = Image.open("extra/minecraft/lava64x.png").convert("RGBA")
hay = Image.open("extra/minecraft/hay64x.png").convert("RGBA")
snowy = Image.open("extra/minecraft/snowy64x.png").convert("RGBA")
layer = Image.open("extra/minecraft/layer64x.png").convert("RGBA")
loff = Image.open("extra/minecraft/lamp_off64x.png").convert("RGBA")
lon = Image.open("extra/minecraft/lamp_on64x.png").convert("RGBA")
fence = Image.open("extra/minecraft/fence64x.png").convert("RGBA")
man = Image.open("extra/minecraft/man.png").convert("RGBA")
cake = Image.open("extra/minecraft/cake64x.png").convert("RGBA")
pop = Image.open("extra/minecraft/poppy64x.png").convert("RGBA")
lapis = Image.open("extra/minecraft/lapis64x.png").convert("RGBA")
wfull = Image.open("extra/minecraft/water_full64x.png").convert("RGBA")
lfull = Image.open("extra/minecraft/lava_full64x.png").convert("RGBA")
wfullmid = Image.open("extra/minecraft/water_full_mid64x.png").convert("RGBA")
lfullmid = Image.open("extra/minecraft/lava_full_mid64x.png").convert("RGBA")
wmid = Image.open("extra/minecraft/water_mid64x.png").convert("RGBA")
lmid = Image.open("extra/minecraft/lava_mid64x.png").convert("RGBA")

fenu = Image.open("extra/minecraft/fence_u64x.png").convert("RGBA")
fent = Image.open("extra/minecraft/fence_t64x.png").convert("RGBA")
fens = Image.open("extra/minecraft/fence_s64x.png").convert("RGBA")
fenb = Image.open("extra/minecraft/fence_b64x.png").convert("RGBA")
fenbu = Image.open("extra/minecraft/fence_bu64x.png").convert("RGBA")
fensb = Image.open("extra/minecraft/fence_sb64x.png").convert("RGBA")
fentb = Image.open("extra/minecraft/fence_tb64x.png").convert("RGBA")
fents = Image.open("extra/minecraft/fence_ts64x.png").convert("RGBA")
fentsb = Image.open("extra/minecraft/fence_tsb64x.png").convert("RGBA")
fenus = Image.open("extra/minecraft/fence_us64x.png").convert("RGBA")
fenusb = Image.open("extra/minecraft/fence_usb64x.png").convert("RGBA")
fenut = Image.open("extra/minecraft/fence_ut64x.png").convert("RGBA")
fenutb = Image.open("extra/minecraft/fence_utb64x.png").convert("RGBA")
fenuts = Image.open("extra/minecraft/fence_uts64x.png").convert("RGBA")
fenutsb = Image.open("extra/minecraft/fence_utsb64x.png").convert("RGBA")

won = Image.open("extra/minecraft/wire_on64x.png").convert("RGBA")
wonu = Image.open("extra/minecraft/wire_on_u64x.png").convert("RGBA")
wont = Image.open("extra/minecraft/wire_on_t64x.png").convert("RGBA")
wons = Image.open("extra/minecraft/wire_on_s64x.png").convert("RGBA")
wonb = Image.open("extra/minecraft/wire_on_b64x.png").convert("RGBA")
wonbu = Image.open("extra/minecraft/wire_on_bu64x.png").convert("RGBA")
wonsb = Image.open("extra/minecraft/wire_on_sb64x.png").convert("RGBA")
wontb = Image.open("extra/minecraft/wire_on_tb64x.png").convert("RGBA")
wonts = Image.open("extra/minecraft/wire_on_ts64x.png").convert("RGBA")
wontsb = Image.open("extra/minecraft/wire_on_tsb64x.png").convert("RGBA")
wonus = Image.open("extra/minecraft/wire_on_us64x.png").convert("RGBA")
wonusb = Image.open("extra/minecraft/wire_on_usb64x.png").convert("RGBA")
wonut = Image.open("extra/minecraft/wire_on_ut64x.png").convert("RGBA")
wonutb = Image.open("extra/minecraft/wire_on_utb64x.png").convert("RGBA")
wonuts = Image.open("extra/minecraft/wire_on_uts64x.png").convert("RGBA")
wonutsb = Image.open("extra/minecraft/wire_on_utsb64x.png").convert("RGBA")

woff = Image.open("extra/minecraft/wire_off64x.png").convert("RGBA")
woffu = Image.open("extra/minecraft/wire_off_u64x.png").convert("RGBA")
wofft = Image.open("extra/minecraft/wire_off_t64x.png").convert("RGBA")
woffs = Image.open("extra/minecraft/wire_off_s64x.png").convert("RGBA")
woffb = Image.open("extra/minecraft/wire_off_b64x.png").convert("RGBA")
woffbu = Image.open("extra/minecraft/wire_off_bu64x.png").convert("RGBA")
woffsb = Image.open("extra/minecraft/wire_off_sb64x.png").convert("RGBA")
wofftb = Image.open("extra/minecraft/wire_off_tb64x.png").convert("RGBA")
woffts = Image.open("extra/minecraft/wire_off_ts64x.png").convert("RGBA")
wofftsb = Image.open("extra/minecraft/wire_off_tsb64x.png").convert("RGBA")
woffus = Image.open("extra/minecraft/wire_off_us64x.png").convert("RGBA")
woffusb = Image.open("extra/minecraft/wire_off_usb64x.png").convert("RGBA")
woffut = Image.open("extra/minecraft/wire_off_ut64x.png").convert("RGBA")
woffutb = Image.open("extra/minecraft/wire_off_utb64x.png").convert("RGBA")
woffuts = Image.open("extra/minecraft/wire_off_uts64x.png").convert("RGBA")
woffutsb = Image.open("extra/minecraft/wire_off_utsb64x.png").convert("RGBA")

leoff = Image.open("extra/minecraft/lever_off64x.png").convert("RGBA")
leon = Image.open("extra/minecraft/lever_on64x.png").convert("RGBA")

selector_back = Image.open("extra/minecraft/selector_back.png").convert("RGBA")
selector_front = Image.open("extra/minecraft/selector_front.png").convert("RGBA")

code_dict = {
    "1": grass,
    "2": water,
    "3": sand,
    "4": stone,
    "5": plank,
    "6": glass,
    "7": red,
    "8": iron,
    "9": brick,
    "g": gold,
    "p": pur,
    "l": leaf,
    "o": log,
    "c": coal,
    "d": dia,
    "v": lava,
    "h": hay,
    "s": layer,
    "k": cake,
    "y": pop,
    "r": loff,
    "b": lapis,
    "%": lon,
    "f": fence,
    "w": woff,
    "$": won,
    "e": leoff,
    "#": leon,
    "┌": woffut,
    "┐": woffts,
    "└": woffbu,
    "┘": woffsb,
    "│": wofftb,
    "─": woffus,
    "┬": woffuts,
    "┤": wofftsb,
    "┴": woffusb,
    "├": woffutb,
    "┼": woffutsb,
    "╌": woffu,
    "╎": wofft,
    "╍": woffs,
    "╏": woffb,
    "┏": wonut,
    "┓": wonts,
    "┗": wonbu,
    "┛": wonsb,
    "┃": wontb,
    "━": wonus,
    "┳": wonuts,
    "┫": wontsb,
    "┻": wonusb,
    "┣": wonutb,
    "╋": wonutsb,
    "┄": wonu,
    "┆": wont,
    "┅": wons,
    "┇": wonb,
    "╔": fenut,
    "╗": fents,
    "╚": fenbu,
    "╝": fensb,
    "║": fentb,
    "═": fenus,
    "╦": fenuts,
    "╣": fentsb,
    "╩": fenusb,
    "╠": fenutb,
    "╬": fenutsb,
    "╶": fenu,
    "╷": fent,
    "╴": fens,
    "╵": fenb,
    "░": wfull,
    "▒": lfull,
    "▓": wfullmid,
    "∙": wmid,
    "█": lfullmid,
    "·": lmid,
}

codes = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "g",
    "p",
    "l",
    "o",
    "c",
    "d",
    "v",
    "h",
    "s",
    "k",
    "y",
    "r",
    "b",
    "%",
    "f",
    "w",
    "$",
    "e",
    "#",
    "┌",
    "┐",
    "└",
    "┘",
    "│",
    "─",
    "┬",
    "┤",
    "┴",
    "├",
    "┼",
    "╌",
    "╎",
    "╍",
    "╏",
    "┏",
    "┓",
    "┗",
    "┛",
    "┃",
    "━",
    "┳",
    "┫",
    "┻",
    "┣",
    "╋",
    "┄",
    "┆",
    "┅",
    "┇",
    "╔",
    "╗",
    "╚",
    "╝",
    "║",
    "═",
    "╩",
    "╠",
    "╦",
    "╣",
    "╬",
    "╴",
    "╶",
    "╵",
    "╷",
    "░",
    "▒",
    "▓",
    "█",
    "∙",
    "·",
]
