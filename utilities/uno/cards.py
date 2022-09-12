from typing import Optional, TypeVar

from .enums import CardType, Color

E = TypeVar("E", bound="Card")


class Emojis:
    class red:
        numbers = [
            "<:red_0:1004449477068869713>",
            "<:red_1:1004449477999992915>",
            "<:red_2:1004449479430262925>",
            "<:red_3:1004449481997172828>",
            "<:red_4:1004449483104465057>",
            "<:red_5:1004449484639588402>",
            "<:red_6:1004449485642022933>",
            "<:red_7:1004449486501851246>",
            "<:red_8:1004449487776911400>",
            "<:red_9:1004449489580458085>",
        ]

        plus_2 = "<:red_plus_2:1004449490373197855>"
        reverse = "<:red_reverse:1004449491434344528>"
        skip = "<:red_skip:1004449492243853443>"

    class yellow:
        numbers = [
            "<:yellow_0:1004449493170786384>",
            "<:yellow_1:1004449494206779483>",
            "<:yellow_2:1004449495083384863>",
            "<:yellow_3:1004449496320708668>",
            "<:yellow_4:1004449497486741566>",
            "<:yellow_5:1004449498703069184>",
            "<:yellow_6:1004449499558723595>",
            "<:yellow_7:1004449501026713742>",
            "<:yellow_8:1004449502280818758>",
            "<:yellow_9:1004449503765594263>",
        ]

        plus_2 = "<:yellow_plus_2:1004449504919044136>"
        reverse = "<:yellow_reverse:1004449506122793000>"
        skip = "<:yellow_skip:1004449507523690587>"

    class blue:
        numbers = [
            "<:blue_0:1004449508698116157>",
            "<:blue_1:1004449510031892631>",
            "<:blue_2:1004449511034343544>",
            "<:blue_3:1004449512179376209>",
            "<:blue_4:1004449512888225834>",
            "<:blue_5:1004449514167472168>",
            "<:blue_6:1004449515480289410>",
            "<:blue_7:1004449516499501086>",
            "<:blue_8:1004449517338370160>",
            "<:blue_9:1004449518437281822>",
        ]

        plus_2 = "<:blue_plus_2:1004449519385202778>"
        reverse = "<:blue_reverse:1004449520291160135>"
        skip = "<:blue_skip:1004449521234890795>"

    class green:
        numbers = [
            "<:green_0:1004449522136653844>",
            "<:green_1:1004449523046821889>",
            "<:green_2:1004449524502233149>",
            "<:green_3:1004449525483704410>",
            "<:green_4:1004449526523891785>",
            "<:green_5:1004449527576658052>",
            "<:green_6:1004449528507801600>",
            "<:green_7:1004449529438949376>",
            "<:green_8:1004449530386854003>",
            "<:green_9:1004449531565453413>",
        ]

        plus_2 = "<:green_plus_2:1004449532601454653>"
        reverse = "<a:green_reverse:1004619745322094662>"
        skip = "<a:green_skip:1004619620805771294>"

    wild = "<a:wild_wild:1004620353349357597>"
    plus_4 = "<a:wild_plus_4:1004620536346857502>"


class Card:
    def __init__(
        self,
        *,
        color: Color,
        type: CardType = CardType.number,
        value: Optional[int] = None,
    ) -> None:
        self.color: Color = color
        self.type: CardType = type
        self.value: Optional[int] = value

    def __hash__(self) -> int:
        return hash((self.color, self.type, self.value))

    def __repr__(self) -> str:
        return (
            f"<Card color={self.color.name} type={self.type.name} value={self.value}>"
        )

    def __eq__(self: E, other: E) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.color is other.color
            and self.type is other.type
            and self.value == other.value
        )

    @property
    def emoji(self) -> str:
        if self.type is CardType.plus_4:
            return Emojis.plus_4
        elif self.type is CardType.wild:
            return Emojis.wild

        sink = getattr(Emojis, self.color.name)
        if self.type is CardType.number:
            return sink.numbers[self.value]
        elif self.type is CardType.plus_2:
            return sink.plus_2
        elif self.type is CardType.reverse:
            return sink.reverse
        elif self.type is CardType.skip:
            return sink.skip

    @property
    def image_url(self) -> str:
        _id = self.emoji.split(":")[-1].rstrip(">")
        return f"https://cdn.discordapp.com/emojis/{_id}.png?v=1"

    def is_wild(self) -> bool:
        return self.type in (CardType.wild, CardType.plus_4)

    def match(self: E, other: E, /) -> bool:
        return (
            other.color is self.color or other.is_wild() or self.stackable_with(other)
        )

    def stackable_with(self: E, other: E, /) -> bool:
        return (
            other.type is self.type is CardType.number and other.value == self.value
        ) or other.type is self.type is not CardType.number


cards = [
    # Red
    Card(color=Color.red, value=0),
    Card(color=Color.red, value=1),
    Card(color=Color.red, value=1),
    Card(color=Color.red, value=2),
    Card(color=Color.red, value=2),
    Card(color=Color.red, value=3),
    Card(color=Color.red, value=3),
    Card(color=Color.red, value=4),
    Card(color=Color.red, value=4),
    Card(color=Color.red, value=5),
    Card(color=Color.red, value=5),
    Card(color=Color.red, value=6),
    Card(color=Color.red, value=6),
    Card(color=Color.red, value=7),
    Card(color=Color.red, value=7),
    Card(color=Color.red, value=8),
    Card(color=Color.red, value=8),
    Card(color=Color.red, value=9),
    Card(color=Color.red, value=9),
    Card(color=Color.red, type=CardType.plus_2),
    Card(color=Color.red, type=CardType.plus_2),
    Card(color=Color.red, type=CardType.reverse),
    Card(color=Color.red, type=CardType.reverse),
    Card(color=Color.red, type=CardType.skip),
    Card(color=Color.red, type=CardType.skip),
    # Yellow
    Card(color=Color.yellow, value=0),
    Card(color=Color.yellow, value=1),
    Card(color=Color.yellow, value=1),
    Card(color=Color.yellow, value=2),
    Card(color=Color.yellow, value=2),
    Card(color=Color.yellow, value=3),
    Card(color=Color.yellow, value=3),
    Card(color=Color.yellow, value=4),
    Card(color=Color.yellow, value=4),
    Card(color=Color.yellow, value=5),
    Card(color=Color.yellow, value=5),
    Card(color=Color.yellow, value=6),
    Card(color=Color.yellow, value=6),
    Card(color=Color.yellow, value=7),
    Card(color=Color.yellow, value=7),
    Card(color=Color.yellow, value=8),
    Card(color=Color.yellow, value=8),
    Card(color=Color.yellow, value=9),
    Card(color=Color.yellow, value=9),
    Card(color=Color.yellow, type=CardType.plus_2),
    Card(color=Color.yellow, type=CardType.plus_2),
    Card(color=Color.yellow, type=CardType.reverse),
    Card(color=Color.yellow, type=CardType.reverse),
    Card(color=Color.yellow, type=CardType.skip),
    Card(color=Color.yellow, type=CardType.skip),
    # Blue
    Card(color=Color.blue, value=0),
    Card(color=Color.blue, value=1),
    Card(color=Color.blue, value=1),
    Card(color=Color.blue, value=2),
    Card(color=Color.blue, value=2),
    Card(color=Color.blue, value=3),
    Card(color=Color.blue, value=3),
    Card(color=Color.blue, value=4),
    Card(color=Color.blue, value=4),
    Card(color=Color.blue, value=5),
    Card(color=Color.blue, value=5),
    Card(color=Color.blue, value=6),
    Card(color=Color.blue, value=6),
    Card(color=Color.blue, value=7),
    Card(color=Color.blue, value=7),
    Card(color=Color.blue, value=8),
    Card(color=Color.blue, value=8),
    Card(color=Color.blue, value=9),
    Card(color=Color.blue, value=9),
    Card(color=Color.blue, type=CardType.plus_2),
    Card(color=Color.blue, type=CardType.plus_2),
    Card(color=Color.blue, type=CardType.reverse),
    Card(color=Color.blue, type=CardType.reverse),
    Card(color=Color.blue, type=CardType.skip),
    Card(color=Color.blue, type=CardType.skip),
    # Green
    Card(color=Color.green, value=0),
    Card(color=Color.green, value=1),
    Card(color=Color.green, value=1),
    Card(color=Color.green, value=2),
    Card(color=Color.green, value=2),
    Card(color=Color.green, value=3),
    Card(color=Color.green, value=3),
    Card(color=Color.green, value=4),
    Card(color=Color.green, value=4),
    Card(color=Color.green, value=5),
    Card(color=Color.green, value=5),
    Card(color=Color.green, value=6),
    Card(color=Color.green, value=6),
    Card(color=Color.green, value=7),
    Card(color=Color.green, value=7),
    Card(color=Color.green, value=8),
    Card(color=Color.green, value=8),
    Card(color=Color.green, value=9),
    Card(color=Color.green, value=9),
    Card(color=Color.green, type=CardType.plus_2),
    Card(color=Color.green, type=CardType.plus_2),
    Card(color=Color.green, type=CardType.reverse),
    Card(color=Color.green, type=CardType.reverse),
    Card(color=Color.green, type=CardType.skip),
    Card(color=Color.green, type=CardType.skip),
    # Wild cards
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4),
]


def create_deck():
    return cards[:]
