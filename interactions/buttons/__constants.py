from string import ascii_uppercase

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
    **dict(zip(ascii_uppercase, REGIONAL_INDICATOR_EMOJI)),
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
